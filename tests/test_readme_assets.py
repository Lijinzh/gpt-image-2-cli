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
    "docs/assets/examples/observatory-photorealistic.png",
    "docs/assets/examples/pixel-snow-observatory.png",
    "docs/assets/examples/star-wars-twin-sunset.png",
    "docs/assets/examples/space-odyssey-monolith.png",
    "docs/assets/examples/troy-gates-duel.png",
    "docs/assets/examples/spider-hero-rooftop.png",
    "docs/assets/examples/iron-hero-workshop.png",
    "docs/assets/examples/avengers-city-battle.png",
    "docs/assets/examples/silence-prison-corridor.png",
    "docs/assets/examples/constantine-cathedral.png",
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
            assert min(image.size) >= 768
            assert max(image.size) >= 1280


def test_movie_gallery_images_have_exact_large_canvas() -> None:
    for relative_path in SITE_ASSETS[-8:]:
        with Image.open(ROOT / relative_path) as image:
            assert image.format == "PNG"
            assert image.size == (1536, 1024)
            assert (ROOT / relative_path).stat().st_size >= 1_000_000


def test_site_brand_icons_are_valid() -> None:
    for relative_path in SITE_ICONS:
        assert (ROOT / relative_path).is_file()

    with Image.open(ROOT / SITE_ICONS[0]) as image:
        assert image.format == "PNG"
        assert image.size == (256, 256)


def test_movie_gallery_assets_are_generated_through_the_cli() -> None:
    generator = ROOT / "scripts" / "generate_gallery_images.py"
    content = generator.read_text(encoding="utf-8")
    for relative_path in SITE_ASSETS[-8:]:
        assert Path(relative_path).name in content
    assert '"-m",\n            "gpt_image_cli"' in content
    assert '"high"' in content
