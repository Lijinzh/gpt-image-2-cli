from __future__ import annotations

import json
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

import httpx

from . import __version__
from .config import ApiConfig, redact
from .errors import GenerationError
from .models import GenerationOptions, GenerationResult, ImagePayload
from .responses import (
    decode_base64,
    decode_json_or_sse,
    extract_image_candidates,
    json_error_message,
    response_shape,
)

USER_AGENT = f"gpt-image-2-cli/{__version__}"


@contextmanager
def progress_heartbeat(enabled: bool, interval: float = 15.0) -> Iterator[None]:
    if not enabled:
        yield
        return
    stop = threading.Event()
    started = time.monotonic()

    def report() -> None:
        while not stop.wait(interval):
            elapsed = int(time.monotonic() - started)
            print(f"Still waiting for the image API... {elapsed}s", file=sys.stderr, flush=True)

    thread = threading.Thread(target=report, name="gpt-image-progress", daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=1)


class ImageClient:
    def __init__(
        self,
        config: ApiConfig,
        *,
        read_timeout: float = 1800,
        connect_timeout: float = 30,
        download_timeout: float = 300,
        max_response_mb: int = 150,
        trust_env: bool = True,
        proxy: str | None = None,
        connect_retries: int = 2,
    ) -> None:
        limits = {
            "read timeout": read_timeout,
            "connect timeout": connect_timeout,
            "download timeout": download_timeout,
            "response size limit": max_response_mb,
        }
        invalid = [name for name, value in limits.items() if value <= 0]
        if invalid:
            raise GenerationError(f"{invalid[0].capitalize()} must be greater than zero.")
        self.config = config
        self.read_timeout = read_timeout
        self.connect_timeout = connect_timeout
        self.download_timeout = download_timeout
        self.max_response_bytes = max_response_mb * 1024 * 1024
        self.trust_env = trust_env
        self.proxy = proxy
        if connect_retries < 0:
            raise GenerationError("Connect retries cannot be negative.")
        self.connect_retries = connect_retries

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Accept": "application/json, text/event-stream, image/*",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }

    def _read_limited(self, response: httpx.Response) -> bytes:
        parts: list[bytes] = []
        total = 0
        for chunk in response.iter_bytes():
            total += len(chunk)
            if total > self.max_response_bytes:
                limit_mb = self.max_response_bytes // 1024 // 1024
                raise GenerationError(
                    f"API response exceeded the {limit_mb} MB safety limit.",
                    possibly_billed=True,
                )
            parts.append(chunk)
        return b"".join(parts)

    def _download(self, url: str) -> bytes:
        timeout = httpx.Timeout(
            connect=self.connect_timeout,
            read=self.download_timeout,
            write=60,
            pool=30,
        )
        try:
            with (
                httpx.Client(
                    timeout=timeout,
                    follow_redirects=True,
                    trust_env=self.trust_env,
                    proxy=self.proxy,
                ) as client,
                client.stream(
                    "GET", url, headers={"User-Agent": USER_AGENT}
                ) as response,
            ):
                if response.status_code >= 400:
                    body = self._read_limited(response)
                    raise GenerationError(
                        f"Generated image download returned HTTP {response.status_code}: "
                        f"{json_error_message(body)}",
                        possibly_billed=True,
                    )
                return self._read_limited(response)
        except httpx.HTTPError as exc:
            raise GenerationError(
                f"Could not download the generated image: {redact(str(exc), self.config.api_key)}",
                possibly_billed=True,
            ) from exc

    def list_models(self) -> list[str]:
        timeout = httpx.Timeout(connect=self.connect_timeout, read=30, write=30, pool=30)
        try:
            with httpx.Client(
                timeout=timeout,
                trust_env=self.trust_env,
                proxy=self.proxy,
            ) as client:
                response = client.get(self.config.models_endpoint, headers=self._headers())
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, json.JSONDecodeError, ValueError) as exc:
            raise GenerationError(
                f"Could not list models: {redact(str(exc), self.config.api_key)}"
            ) from exc
        models: list[str] = []
        if isinstance(payload, dict) and isinstance(payload.get("data"), list):
            for item in payload["data"]:
                if isinstance(item, dict) and isinstance(item.get("id"), str):
                    models.append(item["id"])
        return sorted(set(models))

    def generate(
        self, options: GenerationOptions, *, show_progress: bool = True
    ) -> GenerationResult:
        payload = options.payload()
        timeout = httpx.Timeout(
            connect=self.connect_timeout,
            read=self.read_timeout,
            write=60,
            pool=30,
        )
        started = time.monotonic()
        request_attempted = False
        try:
            for attempt in range(self.connect_retries + 1):
                try:
                    with httpx.Client(
                        timeout=timeout,
                        follow_redirects=True,
                        trust_env=self.trust_env,
                        proxy=self.proxy,
                    ) as client, progress_heartbeat(show_progress), client.stream(
                        "POST",
                        self.config.images_endpoint,
                        headers=self._headers(),
                        json=payload,
                    ) as response:
                        request_attempted = True
                        body = self._read_limited(response)
                        request_id = response.headers.get(
                            "x-request-id"
                        ) or response.headers.get("request-id")
                        if response.status_code >= 400:
                            raise GenerationError(
                                f"Image API returned HTTP {response.status_code}: "
                                f"{redact(json_error_message(body), self.config.api_key)}",
                                possibly_billed=response.status_code >= 500,
                            )
                        content_type = response.headers.get("content-type", "").lower()
                    break
                except (httpx.ConnectError, httpx.ConnectTimeout):
                    if attempt >= self.connect_retries:
                        raise
                    print(
                        "Connection setup failed; retrying "
                        f"({attempt + 1}/{self.connect_retries})...",
                        file=sys.stderr,
                        flush=True,
                    )
        except GenerationError:
            raise
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise GenerationError(
                f"Could not connect to the image API: {redact(str(exc), self.config.api_key)}"
            ) from exc
        except (httpx.ReadTimeout, httpx.ReadError, httpx.RemoteProtocolError) as exc:
            raise GenerationError(
                "The connection ended while waiting for the generated image. "
                "The request may already have been processed, so the CLI will not "
                "retry automatically. "
                f"Details: {redact(str(exc), self.config.api_key)}",
                possibly_billed=request_attempted,
            ) from exc
        except httpx.HTTPError as exc:
            raise GenerationError(
                f"Image API request failed: {redact(str(exc), self.config.api_key)}",
                possibly_billed=request_attempted,
            ) from exc

        if content_type.startswith("image/"):
            images = (ImagePayload(body, "inline-image-response"),)
        else:
            decoded = decode_json_or_sse(body, content_type)
            if isinstance(decoded, dict) and "error" in decoded:
                raise GenerationError(
                    "Image API returned an error inside an HTTP success response: "
                    f"{redact(json_error_message(body), self.config.api_key)}",
                )
            candidates = extract_image_candidates(decoded)
            images_list: list[ImagePayload] = []
            for kind, value in candidates:
                if kind == "base64":
                    images_list.append(ImagePayload(decode_base64(value), "base64"))
                else:
                    images_list.append(ImagePayload(self._download(value), value))
            images = tuple(images_list)

        if not images:
            raise GenerationError(
                "The API returned success but no supported image data "
                "(base64, data URI, or HTTP URL). "
                f"Sanitized response shape: {response_shape(decoded)}",
                possibly_billed=True,
            )
        if len(images) < options.n:
            print(
                f"Warning: requested {options.n} image(s), but the API returned {len(images)}.",
                file=sys.stderr,
            )
        return GenerationResult(
            images=images,
            elapsed_seconds=time.monotonic() - started,
            request_id=request_id,
            response_bytes=len(body),
        )
