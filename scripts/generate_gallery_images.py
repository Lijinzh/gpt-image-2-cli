"""Generate the website movie gallery through this repository's CLI."""

# Ruff intentionally leaves the editorial image prompts unwrapped.
# ruff: noqa: E501

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "docs" / "assets" / "examples"


@dataclass(frozen=True, slots=True)
class Scene:
    filename: str
    prompt: str


SCENES = (
    Scene(
        "star-wars-twin-sunset.png",
        "An original retro space-opera landscape on a vast alien desert ridge beneath two setting suns, "
        "with a rugged six-wheeled survey rover, tall communications mast and tiny cargo spacecraft far away. "
        "Premium high-density 1990s arcade pixel art, 32-bit Neo Geo-era visual richness, "
        "hand-authored pixel clusters, layered dunes and atmospheric perspective, cinematic "
        "orange-violet rim light, realistic weathered metal and sand textures, crisp silhouettes, "
        "wide establishing shot, no text, no logo, no watermark, not a film screenshot, "
        "not vector art, not minimalist, no smooth digital painting, entirely original vehicle designs.",
    ),
    Scene(
        "space-odyssey-monolith.png",
        "A silent lunar excavation site where two astronauts in retro-futurist white suits "
        "stand before a perfectly black rectangular monolith, Earth low above the horizon, "
        "geometric floodlights casting long hard shadows across detailed regolith and machinery. "
        "Premium high-density 1990s arcade pixel art, 32-bit Neo Geo-era visual richness, "
        "hand-authored pixel clusters, disciplined symmetrical widescreen composition, restrained "
        "white charcoal black and cobalt palette, physically convincing suit joints and equipment, "
        "cinematic depth, no text, no logo, no watermark, no actor likeness, not a film screenshot, "
        "not vector art, not minimalist, no smooth digital painting.",
    ),
    Scene(
        "troy-gates-duel.png",
        "Two legendary Bronze Age warriors facing each other outside colossal ancient city gates, "
        "one carrying a round shield and tall-crested helmet, spear formations and soldiers receding "
        "into dusty depth, towering stone walls and banners under a blood-orange sunset. Premium "
        "high-density 1990s arcade pixel art, 32-bit Neo Geo-era visual richness, hand-authored pixel "
        "clusters, archaeologically grounded bronze armor, leather and woven cloth, dramatic dust and "
        "backlight, epic widescreen composition, no text, no logo, no watermark, no actor likeness, "
        "not a film screenshot, not vector art, not minimalist, no smooth digital painting.",
    ),
    Scene(
        "spider-hero-rooftop.png",
        "An original futuristic high-altitude rescue operation above a rain-soaked megacity: a compact yellow "
        "maintenance drone stretches a luminous safety cable between two rooftops while a helmeted utility "
        "worker in teal weather gear secures an antenna platform, lightning revealing dense skyscrapers, "
        "traffic and thousands of windows. Extreme horizontal widescreen establishing composition with the "
        "small worker in the left third and a broad city panorama filling the frame. Premium high-density "
        "1990s arcade pixel art, "
        "32-bit Neo Geo-era visual richness, hand-authored pixel clusters, dynamic low three-quarter "
        "camera, believable industrial equipment, wet reflections, deep navy teal and electric-yellow palette, "
        "cinematic rain and rim light, no text, no logo, no watermark, no actor likeness, not a film "
        "screenshot, not vector art, not minimalist, no smooth digital painting, entirely original designs.",
    ),
    Scene(
        "iron-hero-workshop.png",
        "Inside a luminous underground technology workshop, an original copper-and-crimson exosuit engineer "
        "stands at the center while multi-axis robotic arms calibrate a hexagonal torso power cell, illuminated "
        "display bays holding industrial suit modules and abstract cyan holographic diagrams. Premium "
        "high-density 1990s arcade pixel art, 32-bit Neo Geo-era visual richness, hand-authored pixel "
        "clusters, dense readable machinery, realistic brushed metal and reflections, warm amber versus "
        "cool blue lighting, cinematic widescreen depth, no readable text, no logo, no watermark, no actor "
        "likeness, not a film screenshot, not vector art, not minimalist, no smooth digital painting, "
        "entirely original armor design.",
    ),
    Scene(
        "avengers-city-battle.png",
        "Six entirely original emergency-response champions forming a defensive circle in a shattered "
        "metropolitan avenue: a jetpack engineer, kinetic-shield guardian, weather channeler, massive stone "
        "rescue specialist, agile scout and precision archer, while unknown aircraft weave between towers "
        "and explosions throw debris and "
        "sparks through the street. Premium high-density 1990s arcade pixel art, 32-bit Neo Geo-era visual "
        "richness, hand-authored pixel clusters, readable ensemble silhouettes, layered urban destruction, "
        "bold comic palette with cinematic volumetric light, no text, no logo, no watermark, no actor "
        "likeness, not a film screenshot, not vector art, not minimalist, no smooth digital painting, "
        "entirely original costumes and insignia.",
    ),
    Scene(
        "silence-prison-corridor.png",
        "An original forensic interviewer at the end of a cold underground detention corridor facing an "
        "anonymous high-security detainee behind reinforced glass, guards and barred cells fading into darkness on "
        "both sides. Premium high-density 1990s arcade pixel art, 32-bit Neo Geo-era visual richness, "
        "hand-authored pixel clusters, strict one-point perspective and oppressive symmetry, realistic tiled "
        "walls, glass reflections and restrained expressions, fluorescent green-gray light with tiny dark-red "
        "accents, psychological tension without gore, no text, no logo, no watermark, no actor likeness, not "
        "a film screenshot, not vector art, not minimalist, no smooth digital painting, entirely original characters.",
    ),
    Scene(
        "constantine-cathedral.png",
        "An original weary paranormal archivist in a charcoal raincoat standing in a rain-lashed Gothic cathedral aisle, "
        "holding a small flame while supernatural smoke coils beneath ribbed vaults, stained glass casting "
        "gold and crimson shafts across reflective wet stone. Premium high-density 1990s arcade pixel art, "
        "extreme horizontal widescreen composition showing the full nave from left transept to right transept, "
        "32-bit Neo Geo-era visual richness, hand-authored pixel clusters, intricate carved architecture, "
        "believable coat and skin texture, dramatic chiaroscuro, amber teal and deep-red palette, cinematic "
        "noir depth, no readable text, no logo, no watermark, no actor likeness, not a film screenshot, not "
        "vector art, not minimalist, no smooth digital painting, entirely original character design.",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--proxy", help="Explicit proxy passed to gpt-image.")
    parser.add_argument("--start", type=int, default=1, choices=range(1, len(SCENES) + 1))
    parser.add_argument("--end", type=int, default=len(SCENES), choices=range(1, len(SCENES) + 1))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.start > args.end:
        raise SystemExit("--start must be less than or equal to --end")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for index, scene in enumerate(SCENES[args.start - 1 : args.end], start=args.start):
        output = OUTPUT_DIR / scene.filename
        command = [
            sys.executable,
            "-m",
            "gpt_image_cli",
            "generate",
            scene.prompt,
            "--size",
            "landscape",
            "--quality",
            "high",
            "--fit-output-size",
            "--output",
            str(output),
            "--json",
        ]
        if args.overwrite:
            command.append("--overwrite")
        if args.proxy:
            command.extend(("--proxy", args.proxy))
        print(f"[{index:02d}/{len(SCENES):02d}] {scene.filename}", flush=True)
        subprocess.run(command, cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
