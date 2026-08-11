"""Decode the response shapes used by OpenAI-compatible image relays."""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any
from urllib.parse import urlparse

from .errors import GenerationError


def json_error_message(body: bytes) -> str:
    """Extract a bounded user-facing error from a JSON or text response."""

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


def decode_base64(value: str) -> bytes:
    """Decode plain Base64 or a Base64 data URI."""

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


def extract_image_candidates(value: Any) -> list[tuple[str, str]]:
    """Return ordered ``(kind, value)`` candidates from common response shapes."""

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


def decode_json_or_sse(body: bytes, content_type: str) -> Any:
    """Decode a JSON response or collect JSON values from a simple SSE stream."""

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
