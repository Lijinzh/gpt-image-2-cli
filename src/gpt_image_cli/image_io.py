from __future__ import annotations

import io
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from .errors import GenerationError
from .models import ImagePayload

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


def fit_image(data: bytes, expected_size: tuple[int, int]) -> bytes:
    """Center-crop and resize an image to an explicitly requested canvas."""

    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            target_width, target_height = expected_size
            source_width, source_height = image.size
            source_ratio = source_width / source_height
            target_ratio = target_width / target_height
            if source_ratio > target_ratio:
                crop_width = round(source_height * target_ratio)
                left = (source_width - crop_width) // 2
                box = (left, 0, left + crop_width, source_height)
            else:
                crop_height = round(source_width / target_ratio)
                top = (source_height - crop_height) // 2
                box = (0, top, source_width, top + crop_height)
            fitted = image.crop(box).resize(expected_size, Image.Resampling.LANCZOS)
            output = io.BytesIO()
            fitted.save(output, format="PNG", optimize=True)
            return output.getvalue()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise GenerationError(
            "The API response could not be fitted to the requested size.",
            possibly_billed=True,
        ) from exc


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
    output: Path,
    images: tuple[ImagePayload, ...],
    *,
    overwrite: bool,
    expected_size: tuple[int, int] | None = None,
    fit_output_size: bool = False,
) -> list[ImageInfo]:
    if fit_output_size and expected_size is None:
        raise GenerationError("Fitting output size requires an explicit requested size.")
    if fit_output_size and expected_size is not None:
        images = tuple(
            ImagePayload(fit_image(image.data, expected_size), image.source)
            for image in images
        )
    inspected = [inspect_image(image.data) for image in images]
    if expected_size is not None:
        mismatches = [
            (width, height)
            for _image_format, width, height in inspected
            if (width, height) != expected_size
        ]
        if mismatches:
            actual = ", ".join(f"{width}x{height}" for width, height in mismatches)
            expected = f"{expected_size[0]}x{expected_size[1]}"
            raise GenerationError(
                f"The API ignored the requested image size. Expected {expected}; got {actual}. "
                "No output file was written.",
                possibly_billed=True,
            )
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
