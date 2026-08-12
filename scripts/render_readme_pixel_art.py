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
    width, height = 384, 256
    image = Image.new("RGB", (width, height), "#050713")
    draw = ImageDraw.Draw(image)

    bands = (
        (0, 38, "#050713"),
        (38, 78, "#091536"),
        (78, 112, "#172452"),
        (112, 139, "#493265"),
        (139, 158, "#9d426f"),
    )
    for top, bottom, color in bands:
        draw.rectangle((0, top, width - 1, bottom), fill=color)

    rng = random.Random(2088)
    for _ in range(310):
        x = rng.randrange(3, width - 3)
        y = rng.randrange(3, 135)
        size = 2 if rng.random() < 0.12 else 1
        star_color = rng.choice(("#13f4ef", "#f7f4ff", "#ff3bd4"))
        draw.rectangle((x, y, x + size - 1, y + size - 1), fill=star_color)

    # Sunset planet and atmospheric glow on the right, matching the photo composition.
    draw.ellipse((303, 48, 361, 106), fill="#ff3bd4")
    draw.ellipse((310, 55, 354, 99), fill="#ff7694")
    draw.rectangle((297, 78, 368, 84), fill="#111638")
    draw.rectangle((316, 61, 349, 65), fill="#ffa26b")

    # Layered mountains with snow shelves, rock seams, and distant atmospheric depth.
    rear_mountains = (
        (0, 167), (52, 103), (82, 139), (128, 68), (190, 150),
        (246, 101), (286, 146), (329, 116), (383, 157), (383, 205), (0, 205),
    )
    front_mountains = (
        (0, 188), (63, 126), (106, 173), (150, 104), (211, 181),
        (271, 132), (318, 178), (356, 145), (383, 174), (383, 218), (0, 218),
    )
    draw.polygon(rear_mountains, fill="#102c4c")
    draw.polygon(front_mountains, fill="#183d61")
    draw.polygon(((65, 126), (107, 173), (150, 104), (133, 147), (112, 158)), fill="#6f8eb3")
    draw.polygon(((151, 104), (211, 181), (184, 160), (174, 139)), fill="#a6b8d4")
    draw.polygon(((271, 132), (318, 178), (296, 161), (286, 145)), fill="#718caf")
    draw.line(((0, 187), (63, 126), (106, 173), (150, 104), (211, 181)), fill="#d6e3f5", width=2)
    draw.line(((211, 181), (271, 132), (318, 178), (356, 145), (383, 174)), fill="#91afd0", width=2)
    for _ in range(75):
        x = rng.randrange(6, 374)
        y = rng.randrange(118, 196)
        draw.line((x, y, x + rng.randrange(3, 11), y + rng.randrange(1, 5)), fill="#0c2747")

    # Lake with broken neon and planet reflections.
    draw.rectangle((0, 183, 383, 255), fill="#071a31")
    draw.rectangle((0, 188, 383, 193), fill="#154568")
    for y in range(196, 253, 5):
        for x in range(rng.randrange(-12, 1), 384, rng.randrange(15, 27)):
            length = rng.randrange(4, 18)
            color = rng.choice(("#0d3150", "#164d68", "#13f4ef", "#74406f"))
            draw.line((x, y, min(383, x + length), y), fill=color)
    for y, half_width in ((194, 30), (201, 26), (209, 21), (218, 17), (229, 12), (242, 8)):
        draw.line((332 - half_width, y, 332 + half_width, y), fill="#ff6ca4", width=2)

    # Multi-level observatory, echoing the real facility on the left foreground.
    observatory_ground = ((0, 206), (58, 173), (170, 180), (218, 220), (218, 255), (0, 255))
    draw.polygon(observatory_ground, fill="#081327")
    draw.rectangle((18, 183, 170, 224), fill="#121a35", outline="#13f4ef", width=2)
    draw.rectangle((10, 201, 179, 229), fill="#0b1028", outline="#263466", width=2)
    draw.rectangle((26, 190, 74, 221), fill="#1c294b", outline="#536b9c")
    draw.rectangle((80, 187, 126, 220), fill="#151f42", outline="#ff3bd4")
    draw.rectangle((132, 192, 167, 221), fill="#18284a", outline="#13f4ef")
    for x in (32, 45, 58, 86, 99, 112, 139, 151):
        draw.rectangle((x, 201, x + 7, 211), fill=rng.choice(("#13f4ef", "#b8ff4a", "#ff3bd4")))
        draw.rectangle((x + 1, 202, x + 5, 209), fill="#b9f8ff")
    for x in range(20, 172, 12):
        draw.rectangle((x, 218, x + 8, 220), fill="#536b9c")
    draw.line((12, 198, 174, 198), fill="#f7f4ff")
    for x in range(14, 176, 9):
        draw.line((x, 194, x, 200), fill="#f7f4ff")

    # Detailed telescope dome with segmented plating and slit lighting.
    draw.ellipse((45, 137, 119, 198), fill="#1b294e", outline="#13f4ef", width=2)
    draw.rectangle((44, 168, 120, 199), fill="#192542", outline="#13f4ef", width=2)
    draw.arc((49, 141, 115, 196), 190, 350, fill="#91afd0", width=2)
    draw.line((82, 139, 82, 169), fill="#f7f4ff", width=3)
    draw.line((82, 144, 105, 154), fill="#536b9c", width=2)
    for x in (56, 68, 94, 106):
        draw.line((x, 157, x + 5, 193), fill="#263466")

    # Landing pad, service bridge, antennae, cables, and small props.
    draw.ellipse((183, 210, 297, 254), fill="#10182e", outline="#ff3bd4", width=2)
    draw.ellipse((195, 217, 285, 248), outline="#536b9c", width=2)
    draw.ellipse((215, 224, 265, 242), outline="#13f4ef", width=2)
    draw.line((168, 218, 204, 228), fill="#f7f4ff", width=3)
    draw.line((168, 224, 201, 234), fill="#263466", width=2)
    draw.line((139, 190, 139, 135), fill="#f7f4ff", width=2)
    draw.line((139, 139, 159, 124), fill="#13f4ef", width=2)
    draw.rectangle((157, 121, 165, 128), fill="#b8ff4a")
    draw.line((139, 151, 179, 145), fill="#ff3bd4")
    for x in (7, 178, 302):
        draw.rectangle((x, 218, x + 4, 226), fill="#ffb45e")

    # A richer 32-bit-style field operator: backpack, articulated suit, visor, gear and pose.
    draw.rectangle((309, 177, 331, 196), fill="#dce8f5", outline="#050713", width=2)
    draw.rectangle((312, 180, 328, 191), fill="#132546")
    draw.rectangle((314, 182, 326, 187), fill="#13f4ef")
    draw.rectangle((316, 184, 324, 188), fill="#b8ff4a")
    draw.rectangle((306, 181, 311, 194), fill="#ff3bd4")
    draw.rectangle((330, 184, 334, 193), fill="#536b9c")
    draw.rectangle((308, 196, 332, 222), fill="#d7e3ef", outline="#050713", width=2)
    draw.rectangle((313, 199, 328, 213), fill="#24385b")
    draw.rectangle((316, 202, 325, 206), fill="#ff3bd4")
    draw.rectangle((316, 208, 321, 212), fill="#13f4ef")
    draw.rectangle((304, 199, 310, 216), fill="#9eb1c8", outline="#050713")
    draw.rectangle((330, 198, 336, 218), fill="#9eb1c8", outline="#050713")
    draw.rectangle((302, 214, 309, 221), fill="#b8ff4a", outline="#050713")
    draw.rectangle((332, 216, 339, 223), fill="#13f4ef", outline="#050713")
    draw.rectangle((310, 221, 319, 241), fill="#bdcadb", outline="#050713", width=2)
    draw.rectangle((323, 221, 332, 241), fill="#bdcadb", outline="#050713", width=2)
    draw.rectangle((306, 238, 319, 245), fill="#ff3bd4", outline="#050713")
    draw.rectangle((323, 238, 337, 245), fill="#13f4ef", outline="#050713")
    draw.line((334, 205, 353, 192), fill="#f7f4ff", width=2)
    draw.rectangle((351, 188, 357, 195), fill="#ffb45e", outline="#050713")

    # Foreground snow and rock texture add depth around the character and pad.
    foreground = (
        (0, 228), (76, 216), (142, 232), (202, 227),
        (267, 246), (384, 236), (384, 256), (0, 256),
    )
    draw.polygon(foreground, fill="#10182a")
    for _ in range(110):
        x = rng.randrange(0, 384)
        y = rng.randrange(226, 256)
        color = rng.choice(("#223553", "#526c8d", "#d6e3f5", "#13f4ef"))
        draw.rectangle((x, y, x + rng.randrange(1, 5), y + 1), fill=color)

    OBSERVATORY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.resize((1536, 1024), Image.Resampling.NEAREST).save(
        OBSERVATORY_OUTPUT,
        format="PNG",
        optimize=True,
    )
    return OBSERVATORY_OUTPUT


def _render_space_operator_icon() -> Path:
    image = Image.new("RGBA", (64, 64), (5, 7, 19, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((2, 2, 61, 61), fill="#09112b", outline="#13f4ef", width=3)
    draw.line((8, 24, 8, 8, 24, 8), fill="#263466", width=2)
    draw.line((40, 8, 56, 8, 56, 24), fill="#263466", width=2)
    draw.line((8, 40, 8, 56, 24, 56), fill="#263466", width=2)
    draw.line((40, 56, 56, 56, 56, 40), fill="#263466", width=2)

    # A sharper image-generation operator with antenna, visor and camera core.
    draw.rectangle((29, 5, 34, 11), fill="#ff3bd4")
    draw.rectangle((24, 4, 39, 6), fill="#ff3bd4")
    draw.rectangle((18, 14, 45, 18), fill="#f7f4ff")
    draw.rectangle((13, 19, 50, 41), fill="#f7f4ff")
    draw.rectangle((18, 42, 45, 46), fill="#f7f4ff")
    draw.rectangle((18, 20, 45, 38), fill="#10183a")
    draw.rectangle((21, 23, 28, 29), fill="#13f4ef")
    draw.rectangle((23, 25, 28, 29), fill="#b8ff4a")
    draw.rectangle((35, 23, 41, 29), fill="#b8ff4a")
    draw.rectangle((29, 33, 35, 36), fill="#13f4ef")
    draw.rectangle((6, 27, 12, 39), fill="#ff3bd4")
    draw.rectangle((51, 27, 57, 39), fill="#13f4ef")
    draw.rectangle((20, 42, 43, 46), fill="#ff3bd4")
    draw.rectangle((27, 47, 37, 50), fill="#ff3bd4")
    draw.rectangle((29, 45, 35, 53), fill="#b8ff4a")
    draw.rectangle((10, 49, 16, 55), fill="#13f4ef")
    draw.rectangle((50, 8, 56, 14), fill="#13f4ef")
    draw.rectangle((47, 17, 51, 21), fill="#ffb45e")

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
