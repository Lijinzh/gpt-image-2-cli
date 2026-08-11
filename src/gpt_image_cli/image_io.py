from __future__ import annotations

import io
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from .client import GenerationError, ImagePayload

FORMAT_SUFFIXES = {
    "PNG": ".png",
    "JPEG": ".jpg",
    "WEBP": ".webp",
    "GIF": ".gif",
}


@dataclass(frozen=True, slots=True)
class ImageInfo:
    path: Path
    width: int
    height: int
    format: str
    bytes: int
    source: str


def inspect_image(data: bytes) -> tuple[str, int, int]:
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            image_format = image.format or "UNKNOWN"
            width, height = image.size
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise GenerationError(
            "The API response is not a valid supported image.", possibly_billed=True
        ) from exc
    if width <= 0 or height <= 0:
        raise GenerationError("The generated image has invalid dimensions.", possibly_billed=True)
    return image_format.upper(), width, height


def _output_paths(output: Path, formats: list[str]) -> list[Path]:
    output = output.expanduser().resolve()
    count = len(formats)
    suffix = output.suffix
    if count == 1:
        if suffix:
            return [output]
        return [output.with_suffix(FORMAT_SUFFIXES.get(formats[0], ".img"))]

    base_suffix = suffix or FORMAT_SUFFIXES.get(formats[0], ".img")
    stem = output.stem if suffix else output.name
    return [output.with_name(f"{stem}-{index}{base_suffix}") for index in range(1, count + 1)]


def _write_atomic(path: Path, data: bytes, *, overwrite: bool) -> None:
    if path.exists() and not overwrite:
        raise GenerationError(f"Output already exists; use --overwrite intentionally: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.stem}-",
        suffix=path.suffix or ".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as temporary_file:
            temporary_file.write(data)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def save_images(
    output: Path, images: tuple[ImagePayload, ...], *, overwrite: bool
) -> list[ImageInfo]:
    inspected = [inspect_image(image.data) for image in images]
    paths = _output_paths(output, [item[0] for item in inspected])

    if not overwrite:
        existing = [path for path in paths if path.exists()]
        if existing:
            raise GenerationError(
                "Output already exists; use --overwrite intentionally: "
                + ", ".join(str(path) for path in existing)
            )

    result: list[ImageInfo] = []
    for path, image, (image_format, width, height) in zip(paths, images, inspected, strict=True):
        _write_atomic(path, image.data, overwrite=overwrite)
        result.append(
            ImageInfo(
                path=path,
                width=width,
                height=height,
                format=image_format,
                bytes=len(image.data),
                source=image.source,
            )
        )
    return result
