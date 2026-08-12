"""Render deterministic pixel-art illustrations used by the README and website."""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "assets" / "examples" / "star-wars-pixel-art.png"
CYBER_OUTPUT = ROOT / "docs" / "assets" / "examples" / "cyberpunk-courier-pixel-art.png"
GREAT_WALL_OUTPUT = ROOT / "docs" / "assets" / "examples" / "great-wall-starfleet-pixel-art.png"
OBSERVATORY_OUTPUT = ROOT / "docs" / "assets" / "examples" / "pixel-snow-observatory.png"
ICON_OUTPUT = ROOT / "docs" / "assets" / "icons" / "pixel-space-operator.png"
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


def _render_cyberpunk_courier() -> Path:
    image = Image.new("RGB", PIXEL_SIZE, "#050717")
    draw = ImageDraw.Draw(image)
    for y, color in ((0, "#06091f"), (24, "#10103b"), (45, "#241047")):
        draw.rectangle((0, y, 159, 95), fill=color)

    rng = random.Random(2049)
    for _ in range(74):
        x = rng.randrange(0, 160)
        y = rng.randrange(2, 59)
        draw.rectangle((x, y, x, y + rng.randrange(1, 4)), fill=rng.choice(("#22d3ee", "#f472b6")))

    buildings = (
        (2, 33, 29),
        (34, 22, 56),
        (61, 37, 80),
        (85, 17, 112),
        (118, 29, 143),
        (147, 12, 159),
    )
    for index, (left, top, right) in enumerate(buildings):
        draw.rectangle((left, top, right, 80), fill="#090f27", outline="#1e3a5f")
        glow = "#22d3ee" if index % 2 == 0 else "#f472b6"
        for wy in range(top + 6, 76, 9):
            for wx in range(left + 4, right - 2, 8):
                if (wx + wy + index) % 3:
                    draw.rectangle((wx, wy, wx + 2, wy + 3), fill=glow)

    draw.polygon(((0, 81), (160, 74), (160, 95), (0, 95)), fill="#07101e")
    draw.line((0, 91, 159, 82), fill="#22d3ee", width=1)
    draw.line((72, 80, 72, 95), fill="#facc15", width=1)
    draw.line((104, 78, 117, 95), fill="#facc15", width=1)

    draw.rectangle((69, 54, 78, 69), fill="#111827")
    draw.rectangle((71, 50, 76, 55), fill="#dbeafe")
    draw.rectangle((72, 51, 76, 53), fill="#22d3ee")
    draw.rectangle((65, 58, 69, 70), fill="#ec4899")
    draw.rectangle((78, 58, 83, 70), fill="#0ea5e9")
    draw.rectangle((69, 69, 72, 82), fill="#111827")
    draw.rectangle((76, 69, 79, 82), fill="#111827")
    draw.rectangle((60, 56, 65, 66), fill="#facc15")
    draw.rectangle((61, 58, 64, 62), fill="#f97316")

    CYBER_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.resize((PIXEL_SIZE[0] * SCALE, PIXEL_SIZE[1] * SCALE), Image.Resampling.NEAREST).save(
        CYBER_OUTPUT,
        format="PNG",
        optimize=True,
    )
    return CYBER_OUTPUT


def _render_great_wall_starfleet() -> Path:
    image = Image.new("RGB", PIXEL_SIZE, "#0b1730")
    draw = ImageDraw.Draw(image)
    bands = ((0, 18, "#101c3c"), (18, 36, "#17476b"), (36, 52, "#e1644d"), (52, 66, "#f7a454"))
    for top, bottom, color in bands:
        draw.rectangle((0, top, 159, bottom), fill=color)

    draw.rectangle((17, 12, 25, 20), fill="#fbbf24")
    draw.rectangle((15, 14, 27, 18), fill="#fde68a")
    draw.rectangle((18, 13, 24, 19), fill="#fff7cc")

    rng = random.Random(2210)
    for _ in range(44):
        x = rng.randrange(2, 158)
        y = rng.randrange(2, 38)
        draw.point((x, y), fill=rng.choice(("#dbeafe", "#fde68a", "#93c5fd")))

    draw.polygon(
        (
            (0, 63),
            (27, 45),
            (52, 62),
            (79, 42),
            (109, 65),
            (136, 46),
            (159, 58),
            (159, 95),
            (0, 95),
        ),
        fill="#1d4d63",
    )
    draw.polygon(
        (
            (0, 74),
            (33, 57),
            (63, 74),
            (91, 54),
            (125, 76),
            (159, 60),
            (159, 95),
            (0, 95),
        ),
        fill="#183c4f",
    )
    draw.rectangle((0, 80, 159, 95), fill="#102c3d")

    wall = ((0, 88), (24, 78), (45, 82), (68, 69), (91, 75), (116, 62), (140, 70), (159, 59))
    draw.line(wall, fill="#d6b27a", width=4)
    draw.line(wall, fill="#7c5037", width=1)
    for x, y in ((22, 78), (66, 68), (115, 61), (143, 67)):
        draw.rectangle((x - 4, y - 6, x + 4, y + 3), fill="#9a6a45", outline="#f4d19b")
        draw.rectangle((x - 2, y - 9, x + 2, y - 6), fill="#9a6a45")

    ships = ((92, 24, 1), (119, 17, 0), (138, 30, 2))
    for x, y, accent in ships:
        draw.polygon(((x, y), (x + 12, y + 3), (x + 3, y + 6)), fill="#dbeafe")
        draw.rectangle((x + 3, y + 2, x + 8, y + 3), fill=("#22d3ee", "#f472b6", "#facc15")[accent])
        draw.line((x - 7, y + 4, x, y + 3), fill="#e0f2fe", width=1)

    GREAT_WALL_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.resize((PIXEL_SIZE[0] * SCALE, PIXEL_SIZE[1] * SCALE), Image.Resampling.NEAREST).save(
        GREAT_WALL_OUTPUT,
        format="PNG",
        optimize=True,
    )
    return GREAT_WALL_OUTPUT


def _render_pixel_observatory() -> Path:
    image = Image.new("RGB", (192, 128), "#050713")
    draw = ImageDraw.Draw(image)

    bands = (
        (0, 24, "#050713"),
        (24, 47, "#0b1535"),
        (47, 66, "#24245b"),
        (66, 79, "#7b326d"),
    )
    for top, bottom, color in bands:
        draw.rectangle((0, top, 191, bottom), fill=color)

    rng = random.Random(2088)
    for _ in range(118):
        x = rng.randrange(2, 190)
        y = rng.randrange(2, 66)
        size = 2 if rng.random() < 0.08 else 1
        star_color = rng.choice(("#13f4ef", "#f7f4ff", "#ff3bd4"))
        draw.rectangle((x, y, x + size - 1, y + size - 1), fill=star_color)

    draw.rectangle((139, 18, 158, 37), fill="#ff3bd4")
    draw.rectangle((135, 22, 162, 33), fill="#ff3bd4")
    draw.rectangle((143, 22, 154, 33), fill="#ff7ce5")
    draw.rectangle((0, 79, 191, 127), fill="#091b35")

    rear_mountains = (
        (0, 95), (38, 52), (66, 89), (101, 46), (130, 92),
        (168, 58), (191, 82), (191, 127), (0, 127),
    )
    front_mountains = (
        (0, 105), (46, 74), (75, 101), (109, 68), (143, 104),
        (176, 76), (191, 91), (191, 127), (0, 127),
    )
    snow_line = ((0, 104), (46, 74), (75, 101), (109, 68), (143, 104), (176, 76), (191, 91))
    draw.polygon(rear_mountains, fill="#102c4c")
    draw.polygon(front_mountains, fill="#174167")
    draw.line(snow_line, fill="#6f8eb3", width=2)

    draw.rectangle((0, 111, 191, 127), fill="#071626")
    draw.rectangle((0, 113, 191, 115), fill="#13f4ef")
    draw.rectangle((0, 117, 191, 127), fill="#081022")
    for x in range(0, 192, 16):
        draw.line((96, 114, x, 127), fill="#263466")
    for y in (119, 123):
        draw.line((0, y, 191, y), fill="#263466")

    # Observatory platform and modules.
    draw.rectangle((47, 86, 148, 103), fill="#0b1028", outline="#13f4ef", width=2)
    draw.rectangle((52, 80, 95, 99), fill="#111a3c", outline="#ff3bd4")
    draw.rectangle((57, 85, 62, 91), fill="#b8ff4a")
    draw.rectangle((68, 85, 74, 91), fill="#13f4ef")
    draw.rectangle((80, 85, 88, 91), fill="#ff3bd4")
    draw.rectangle((100, 77, 139, 100), fill="#101638", outline="#13f4ef")
    draw.rectangle((105, 82, 112, 90), fill="#13f4ef")
    draw.rectangle((119, 82, 126, 90), fill="#ff3bd4")
    draw.rectangle((132, 82, 136, 91), fill="#b8ff4a")

    # Dome and telescope.
    draw.rectangle((65, 69, 91, 84), fill="#18244e", outline="#13f4ef")
    draw.rectangle((69, 64, 87, 69), fill="#283766", outline="#13f4ef")
    draw.rectangle((73, 60, 83, 64), fill="#536b9c")
    draw.rectangle((106, 64, 109, 78), fill="#f7f4ff")
    draw.rectangle((109, 60, 123, 65), fill="#283766", outline="#ff3bd4")
    draw.rectangle((121, 58, 127, 67), fill="#ff3bd4")
    draw.line((124, 61, 145, 47), fill="#13f4ef", width=2)
    draw.rectangle((144, 45, 148, 49), fill="#b8ff4a")

    # Small space operator in the foreground.
    draw.rectangle((28, 88, 38, 100), fill="#f7f4ff", outline="#13f4ef")
    draw.rectangle((30, 84, 36, 89), fill="#f7f4ff")
    draw.rectangle((31, 85, 35, 87), fill="#ff3bd4")
    draw.rectangle((26, 91, 29, 98), fill="#b8ff4a")
    draw.rectangle((37, 91, 40, 98), fill="#13f4ef")
    draw.rectangle((29, 100, 32, 106), fill="#f7f4ff")
    draw.rectangle((35, 100, 38, 106), fill="#f7f4ff")

    OBSERVATORY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.resize((1536, 1024), Image.Resampling.NEAREST).save(
        OBSERVATORY_OUTPUT,
        format="PNG",
        optimize=True,
    )
    return OBSERVATORY_OUTPUT


def _render_space_operator_icon() -> Path:
    image = Image.new("RGBA", (32, 32), (5, 7, 19, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((1, 1, 30, 30), fill="#0a1027", outline="#13f4ef", width=2)
    draw.rectangle((4, 4, 27, 27), outline="#263466")

    # Helmet and face: a friendly space-station operator / alien hybrid.
    draw.rectangle((9, 6, 22, 9), fill="#f7f4ff")
    draw.rectangle((7, 9, 24, 19), fill="#f7f4ff")
    draw.rectangle((9, 19, 22, 23), fill="#f7f4ff")
    draw.rectangle((9, 10, 22, 18), fill="#111a3c")
    draw.rectangle((11, 12, 13, 14), fill="#b8ff4a")
    draw.rectangle((18, 12, 20, 14), fill="#b8ff4a")
    draw.rectangle((14, 16, 17, 17), fill="#13f4ef")
    draw.rectangle((5, 12, 8, 17), fill="#ff3bd4")
    draw.rectangle((23, 12, 26, 17), fill="#13f4ef")
    draw.rectangle((11, 23, 20, 26), fill="#ff3bd4")
    draw.rectangle((13, 24, 18, 27), fill="#b8ff4a")
    draw.rectangle((3, 25, 6, 28), fill="#13f4ef")
    draw.rectangle((25, 4, 28, 7), fill="#ff3bd4")

    ICON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.resize((256, 256), Image.Resampling.NEAREST).save(
        ICON_OUTPUT,
        format="PNG",
        optimize=True,
    )
    return ICON_OUTPUT


if __name__ == "__main__":
    print(render())
    print(_render_cyberpunk_courier())
    print(_render_great_wall_starfleet())
    print(_render_pixel_observatory())
    print(_render_space_operator_icon())
