from __future__ import annotations

import base64
import binascii
import json
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from .config import ApiConfig, redact

SUPPORTED_SIZES = ("auto", "1024x1024", "1536x1024", "1024x1536")
SIZE_ALIASES = {
    "square": "1024x1024",
    "landscape": "1536x1024",
    "portrait": "1024x1536",
}
SUPPORTED_QUALITIES = ("auto", "low", "medium", "high")
SUPPORTED_BACKGROUNDS = ("auto", "opaque")


class GenerationError(RuntimeError):
    """A generation failure with safe, user-facing details."""

    def __init__(self, message: str, *, possibly_billed: bool = False) -> None:
        super().__init__(message)
        self.possibly_billed = possibly_billed


@dataclass(frozen=True, slots=True)
class GenerationOptions:
    model: str
    prompt: str
    n: int = 1
    size: str = "auto"
    quality: str = "auto"
    background: str = "auto"

    def normalized_size(self) -> str:
        return SIZE_ALIASES.get(self.size, self.size)

    def payload(self) -> dict[str, Any]:
        if not self.prompt.strip():
            raise GenerationError("Prompt cannot be empty.")
        if not 1 <= self.n <= 10:
            raise GenerationError("Image count must be between 1 and 10.")
        size = self.normalized_size()
        if size not in SUPPORTED_SIZES:
            raise GenerationError(f"Unsupported size: {self.size}")
        if self.quality not in SUPPORTED_QUALITIES:
            raise GenerationError(f"Unsupported quality: {self.quality}")
        if self.background not in SUPPORTED_BACKGROUNDS:
            raise GenerationError(f"Unsupported background: {self.background}")

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": self.prompt.strip(),
            "n": self.n,
        }
        if size != "auto":
            payload["size"] = size
        if self.quality != "auto":
            payload["quality"] = self.quality
        if self.background != "auto":
            payload["background"] = self.background

        # Deliberately do not send response_format for gpt-image-* models.
        # Current OpenAI-compatible implementations can reject that parameter.
        return payload


@dataclass(frozen=True, slots=True)
class ImagePayload:
    data: bytes
    source: str


@dataclass(frozen=True, slots=True)
class GenerationResult:
    images: tuple[ImagePayload, ...]
    elapsed_seconds: float
    request_id: str | None
    response_bytes: int


def _json_error_message(body: bytes) -> str:
    text = body.decode("utf-8", errors="replace")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text[:2000]
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        message = error.get("message") or error.get("detail")
        if isinstance(message, str):
            return message
    if isinstance(error, str):
        return error
    return text[:2000]


def _decode_base64(value: str) -> bytes:
    encoded = value
    if value.startswith("data:"):
        marker = ";base64,"
        if marker not in value:
            raise GenerationError("The API returned a data URI that is not base64 encoded.")
        encoded = value.split(marker, 1)[1]
    try:
        return base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise GenerationError("The API returned invalid base64 image data.") from exc


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _extract_candidates(value: Any) -> list[tuple[str, str]]:
    """Return ordered (kind, value) image candidates from common compatible shapes."""
    found: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(kind: str, candidate: str) -> None:
        item = (kind, candidate)
        if candidate and item not in seen:
            seen.add(item)
            found.append(item)

    def visit(node: Any) -> None:
        if isinstance(node, list):
            for child in node:
                visit(child)
            return
        if not isinstance(node, dict):
            return

        for key in ("b64_json", "base64", "image_base64"):
            candidate = node.get(key)
            if isinstance(candidate, str):
                add("base64", candidate)
        for key in ("url", "image_url"):
            candidate = node.get(key)
            if isinstance(candidate, str) and _is_http_url(candidate):
                add("url", candidate)
            elif isinstance(candidate, dict):
                nested = candidate.get("url")
                if isinstance(nested, str) and _is_http_url(nested):
                    add("url", nested)

        for key in ("data", "images", "output", "result"):
            child = node.get(key)
            if isinstance(child, (dict, list)):
                visit(child)

    visit(value)
    return found


def _decode_json_or_sse(body: bytes, content_type: str) -> Any:
    text = body.decode("utf-8", errors="replace").lstrip("\ufeff")
    if "text/event-stream" not in content_type and not text.lstrip().startswith("data:"):
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise GenerationError("The image API returned invalid JSON.") from exc

    events: list[Any] = []
    for line in text.splitlines():
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if not data or data == "[DONE]":
            continue
        try:
            events.append(json.loads(data))
        except json.JSONDecodeError:
            continue
    if not events:
        raise GenerationError("The image API returned an empty or invalid event stream.")
    return events


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
    ) -> None:
        self.config = config
        self.read_timeout = read_timeout
        self.connect_timeout = connect_timeout
        self.download_timeout = download_timeout
        self.max_response_bytes = max_response_mb * 1024 * 1024
        self.trust_env = trust_env

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_key}",
            "Accept": "application/json, text/event-stream, image/*",
            "Content-Type": "application/json",
            "User-Agent": "gpt-image-2-cli/0.1.0",
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
                ) as client,
                client.stream(
                    "GET", url, headers={"User-Agent": "gpt-image-2-cli/0.1.0"}
                ) as response,
            ):
                if response.status_code >= 400:
                    body = self._read_limited(response)
                    raise GenerationError(
                        f"Generated image download returned HTTP {response.status_code}: "
                        f"{_json_error_message(body)}",
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
            with httpx.Client(timeout=timeout, trust_env=self.trust_env) as client:
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
        request_reached_server = False
        try:
            with (
                httpx.Client(
                    timeout=timeout,
                    follow_redirects=True,
                    trust_env=self.trust_env,
                ) as client,
                progress_heartbeat(show_progress),
                client.stream(
                    "POST",
                    self.config.images_endpoint,
                    headers=self._headers(),
                    json=payload,
                ) as response,
            ):
                request_reached_server = True
                body = self._read_limited(response)
                request_id = response.headers.get("x-request-id") or response.headers.get(
                    "request-id"
                )
                if response.status_code >= 400:
                    raise GenerationError(
                        f"Image API returned HTTP {response.status_code}: "
                        f"{redact(_json_error_message(body), self.config.api_key)}",
                        possibly_billed=response.status_code >= 500,
                    )
                content_type = response.headers.get("content-type", "").lower()
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
                possibly_billed=request_reached_server,
            ) from exc
        except httpx.HTTPError as exc:
            raise GenerationError(
                f"Image API request failed: {redact(str(exc), self.config.api_key)}",
                possibly_billed=request_reached_server,
            ) from exc

        if content_type.startswith("image/"):
            images = (ImagePayload(body, "inline-image-response"),)
        else:
            decoded = _decode_json_or_sse(body, content_type)
            candidates = _extract_candidates(decoded)
            images_list: list[ImagePayload] = []
            for kind, value in candidates:
                if kind == "base64":
                    images_list.append(ImagePayload(_decode_base64(value), "base64"))
                else:
                    images_list.append(ImagePayload(self._download(value), value))
            images = tuple(images_list)

        if not images:
            raise GenerationError(
                "The API returned success but no supported image data "
                "(base64, data URI, or HTTP URL).",
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
