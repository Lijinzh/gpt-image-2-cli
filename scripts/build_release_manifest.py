#!/usr/bin/env python3
"""Build latest.json for a wheel and optionally verify an existing manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from email.parser import Parser
from pathlib import Path

PACKAGE_NAME = "gpt-image-2-cli"


def wheel_version(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if name.endswith(".dist-info/METADATA")]
        if len(names) != 1:
            raise RuntimeError(f"{path.name} has invalid wheel metadata")
        metadata = Parser().parsestr(archive.read(names[0]).decode("utf-8"))
    if metadata.get("Name") != PACKAGE_NAME:
        raise RuntimeError(f"{path.name} is not {PACKAGE_NAME}")
    version = metadata.get("Version", "").strip()
    if not version:
        raise RuntimeError(f"{path.name} has no package version")
    return version


def build_manifest(path: Path) -> dict[str, object]:
    version = wheel_version(path)
    return {
        "schema_version": 1,
        "package": PACKAGE_NAME,
        "version": version,
        "tag": f"v{version}",
        "artifact": {
            "name": path.name,
            "size": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--output", type=Path, default=Path("dist/latest.json"))
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    expected = build_manifest(args.wheel)
    encoded = json.dumps(expected, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != encoded:
            print(f"{args.output} is missing or stale", file=sys.stderr)
            return 1
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8", newline="\n")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
