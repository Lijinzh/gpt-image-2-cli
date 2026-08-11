from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

from gpt_image_cli.image_io import save_images
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
