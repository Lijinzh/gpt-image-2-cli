"""Validated request and response models shared by the CLI and HTTP client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import GenerationError

SUPPORTED_SIZES = ("auto", "1024x1024", "1536x1024", "1024x1536")
SIZE_ALIASES = {
    "square": "1024x1024",
    "landscape": "1536x1024",
    "portrait": "1024x1536",
}
SUPPORTED_QUALITIES = ("auto", "low", "medium", "high")
SUPPORTED_BACKGROUNDS = ("auto", "opaque")


@dataclass(frozen=True, slots=True)
class GenerationOptions:
    """Parameters accepted by the compatible image-generation endpoint."""

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

        # Some OpenAI-compatible gpt-image-* routes reject response_format.
        return payload


@dataclass(frozen=True, slots=True)
class ImagePayload:
    """Raw image bytes and the compatible response field they came from."""

    data: bytes
    source: str


@dataclass(frozen=True, slots=True)
class GenerationResult:
    """Transport metadata and decoded images returned by one request."""

    images: tuple[ImagePayload, ...]
    elapsed_seconds: float
    request_id: str | None
    response_bytes: int
