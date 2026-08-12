from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from gpt_image_cli.errors import GenerationError
from gpt_image_cli.image_io import fit_image, save_images
from gpt_image_cli.models import ImagePayload


def make_png(width: int, height: int) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (width, height), color=(20, 40, 60)).save(output, format="PNG")
    return output.getvalue()


def test_save_images_validates_dimensions_and_expands_multiple_paths(tmp_path: Path) -> None:
    images = (
        ImagePayload(make_png(32, 16), "base64"),
        ImagePayload(make_png(64, 32), "base64"),
    )
    saved = save_images(tmp_path / "result.png", images, overwrite=False)
    assert [item.path.name for item in saved] == ["result-1.png", "result-2.png"]
    assert [(item.width, item.height) for item in saved] == [(32, 16), (64, 32)]
    assert all(item.path.is_file() for item in saved)


def test_save_images_rejects_size_mismatch_before_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "existing.png"
    original = make_png(1536, 1024)
    output.write_bytes(original)

    with pytest.raises(GenerationError, match="Expected 1536x1024; got 1369x1149"):
        save_images(
            output,
            (ImagePayload(make_png(1369, 1149), "base64"),),
            overwrite=True,
            expected_size=(1536, 1024),
        )

    assert output.read_bytes() == original


def test_fit_image_center_crops_to_exact_canvas() -> None:
    fitted = fit_image(make_png(1874, 839), (1536, 1024))
    with Image.open(io.BytesIO(fitted)) as image:
        assert image.format == "PNG"
        assert image.size == (1536, 1024)


def test_save_images_can_explicitly_fit_api_output(tmp_path: Path) -> None:
    saved = save_images(
        tmp_path / "fitted.png",
        (ImagePayload(make_png(1050, 1498), "base64"),),
        overwrite=False,
        expected_size=(1536, 1024),
        fit_output_size=True,
    )
    assert [(item.width, item.height, item.format) for item in saved] == [
        (1536, 1024, "PNG")
    ]
