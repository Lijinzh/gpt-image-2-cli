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

SITE_ASSETS = (
    "docs/assets/examples/cyberpunk-courier-pixel-art.png",
    "docs/assets/examples/great-wall-starfleet-pixel-art.png",
    "docs/assets/examples/pixel-snow-observatory.png",
)

SITE_ICONS = (
    "docs/assets/icons/pixel-space-operator.png",
    "docs/assets/icons/pixel-space-operator.svg",
)


def test_readme_visual_assets_exist_and_are_referenced() -> None:
    readme = README.read_text(encoding="utf-8")
    for relative_path in ASSETS:
        assert relative_path in readme
        assert (ROOT / relative_path).is_file()

    with Image.open(ROOT / ASSETS[-1]) as image:
        assert image.format == "PNG"
        assert image.size == (1280, 768)


def test_site_example_images_are_valid() -> None:
    for relative_path in SITE_ASSETS:
        with Image.open(ROOT / relative_path) as image:
            assert image.format == "PNG"
            assert image.width >= 1280
            assert image.height >= 768


def test_site_brand_icons_are_valid() -> None:
    for relative_path in SITE_ICONS:
        assert (ROOT / relative_path).is_file()

    with Image.open(ROOT / SITE_ICONS[0]) as image:
        assert image.format == "PNG"
        assert image.size == (256, 256)
