"""Render the deterministic pixel-art illustration used by the README."""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "assets" / "examples" / "star-wars-pixel-art.png"
PIXEL_SIZE = (160, 96)
SCALE = 8


def _draw_sky(draw: ImageDraw.ImageDraw) -> None:
    bands = (
        (0, 16, "#070b24"),
        (16, 32, "#11133d"),
        (32, 47, "#292050"),
        (47, 58, "#70345f"),
        (58, 66, "#d46a55"),
    )
    for top, bottom, color in bands:
        draw.rectangle((0, top, 159, bottom), fill=color)

    rng = random.Random(1977)
    colors = ("#f8fafc", "#fde68a", "#93c5fd")
    for _ in range(86):
        x = rng.randrange(2, 158)
        y = rng.randrange(2, 54)
        size = 2 if rng.random() < 0.12 else 1
        draw.rectangle((x, y, x + size - 1, y + size - 1), fill=rng.choice(colors))


def _draw_twin_suns(draw: ImageDraw.ImageDraw) -> None:
    draw.rectangle((116, 22, 130, 36), fill="#f59e0b")
    draw.rectangle((114, 25, 132, 33), fill="#f59e0b")
    draw.rectangle((117, 23, 129, 35), fill="#fde68a")
    draw.rectangle((122, 24, 128, 30), fill="#fff7cc")
    draw.rectangle((139, 33, 147, 41), fill="#fbbf24")
    draw.rectangle((137, 35, 149, 39), fill="#fbbf24")
    draw.rectangle((140, 34, 146, 40), fill="#fef3c7")


def _draw_fighter(draw: ImageDraw.ImageDraw) -> None:
    dark = "#111827"
    light = "#94a3b8"
    draw.polygon(((22, 24), (38, 27), (45, 31), (37, 32), (28, 29)), fill=dark)
    draw.rectangle((27, 25, 39, 28), fill=light)
    draw.rectangle((18, 20, 23, 27), fill=light)
    draw.rectangle((18, 29, 23, 36), fill=light)
    draw.rectangle((39, 25, 43, 29), fill="#22d3ee")
    draw.rectangle((14, 19, 18, 22), fill="#64748b")
    draw.rectangle((14, 34, 18, 37), fill="#64748b")


def _draw_dunes(draw: ImageDraw.ImageDraw) -> None:
    draw.polygon(
        (
            (0, 63),
            (25, 57),
            (51, 62),
            (77, 55),
            (104, 62),
            (131, 54),
            (159, 61),
            (159, 95),
            (0, 95),
        ),
        fill="#b4533c",
    )
    draw.polygon(
        (
            (0, 72),
            (30, 65),
            (57, 71),
            (86, 63),
            (115, 72),
            (143, 64),
            (159, 68),
            (159, 95),
            (0, 95),
        ),
        fill="#d97745",
    )
    draw.polygon(
        ((0, 82), (39, 73), (76, 81), (111, 72), (159, 80), (159, 95), (0, 95)),
        fill="#f59e52",
    )
    draw.rectangle((0, 91, 159, 95), fill="#7c2d32")


def _draw_hero(draw: ImageDraw.ImageDraw) -> None:
    outline = "#111827"
    robe = "#e5d3aa"
    shadow = "#8b5e4b"
    draw.rectangle((55, 55, 61, 61), fill="#d7a06d")
    draw.rectangle((54, 61, 62, 75), fill=outline)
    draw.rectangle((56, 62, 60, 72), fill=robe)
    draw.rectangle((52, 64, 55, 72), fill=shadow)
    draw.rectangle((61, 64, 65, 72), fill=shadow)
    draw.rectangle((54, 75, 57, 87), fill=outline)
    draw.rectangle((60, 75, 63, 87), fill=outline)
    draw.rectangle((63, 62, 66, 65), fill="#cbd5e1")
    draw.rectangle((66, 49, 68, 65), fill="#67e8f9")
    draw.rectangle((67, 43, 69, 57), fill="#22d3ee")
    draw.rectangle((68, 43, 68, 55), fill="#e0f2fe")


def _draw_droid(draw: ImageDraw.ImageDraw) -> None:
    white = "#e2e8f0"
    blue = "#2563eb"
    dark = "#172554"
    draw.rectangle((77, 61, 86, 66), fill=dark)
    draw.rectangle((78, 59, 85, 64), fill=white)
    draw.rectangle((80, 58, 83, 60), fill=blue)
    draw.rectangle((77, 65, 86, 80), fill=white)
    draw.rectangle((79, 66, 84, 71), fill=blue)
    draw.rectangle((81, 67, 82, 69), fill="#22d3ee")
    draw.rectangle((79, 73, 84, 77), fill=dark)
    draw.rectangle((75, 70, 78, 84), fill=white)
    draw.rectangle((85, 70, 88, 84), fill=white)
    draw.rectangle((76, 82, 79, 86), fill=dark)
    draw.rectangle((84, 82, 87, 86), fill=dark)


def render() -> Path:
    image = Image.new("RGB", PIXEL_SIZE, "#070b24")
    draw = ImageDraw.Draw(image)
    _draw_sky(draw)
    _draw_twin_suns(draw)
    _draw_fighter(draw)
    _draw_dunes(draw)
    _draw_hero(draw)
    _draw_droid(draw)
    draw.rectangle((9, 86, 29, 88), fill="#7c2d32")
    draw.rectangle((119, 85, 151, 87), fill="#7c2d32")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.resize((PIXEL_SIZE[0] * SCALE, PIXEL_SIZE[1] * SCALE), Image.Resampling.NEAREST).save(
        OUTPUT,
        format="PNG",
        optimize=True,
    )
    return OUTPUT


if __name__ == "__main__":
    print(render())
