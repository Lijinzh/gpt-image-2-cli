from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
ASSETS = (
    "docs/assets/icons/pixel-terminal.svg",
    "docs/assets/icons/pixel-image.svg",
    "docs/assets/icons/pixel-shield.svg",
    "docs/assets/examples/star-wars-pixel-art.png",
)


def test_readme_visual_assets_exist_and_are_referenced() -> None:
    readme = README.read_text(encoding="utf-8")
    for relative_path in ASSETS:
        assert relative_path in readme
        assert (ROOT / relative_path).is_file()

    with Image.open(ROOT / ASSETS[-1]) as image:
        assert image.format == "PNG"
        assert image.size == (1280, 768)
