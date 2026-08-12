#!/usr/bin/env python3
"""Verify that a public release source exposes a usable update manifest and wheel."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.request

SOURCES = {
    "github": (
        "https://api.github.com/repos/{owner}/{repo}/releases/latest",
        "Lijinzh",
        "gpt-image-2-cli",
    ),
    "gitee": (
        "https://gitee.com/api/v5/repos/{owner}/{repo}/releases/latest",
        os.getenv("GITEE_OWNER", "shan-yujun"),
        os.getenv("GITEE_REPO", "gpt-image-2-cli"),
    ),
    "gitcode": (
        "https://api.gitcode.com/api/v5/repos/{owner}/{repo}/releases/latest",
        os.getenv("GITCODE_OWNER", "Lijinzh"),
        os.getenv("GITCODE_REPO", "gpt-image-2-cli"),
    ),
}


def read(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "gpt-image-release-verify/1"})
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", choices=tuple(SOURCES))
    args = parser.parse_args()
    template, owner, repo = SOURCES[args.source]
    release = json.loads(read(template.format(owner=owner, repo=repo)))
    assets = {item["name"]: item["browser_download_url"] for item in release["assets"]}
    manifest = json.loads(read(assets["latest.json"]))
    artifact = manifest["artifact"]
    wheel = read(assets[artifact["name"]])
    assert release["tag_name"] == manifest["tag"]
    assert len(wheel) == artifact["size"]
    assert hashlib.sha256(wheel).hexdigest() == artifact["sha256"]
    print(
        json.dumps(
            {
                "source": args.source,
                "tag": manifest["tag"],
                "asset": artifact["name"],
                "bytes": len(wheel),
                "sha256": artifact["sha256"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
