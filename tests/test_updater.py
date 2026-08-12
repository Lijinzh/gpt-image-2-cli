from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest
from packaging.version import Version

from gpt_image_cli.errors import UpdateError
from gpt_image_cli.updater import (
    ReleaseCandidate,
    SourceSpec,
    UpdateArtifact,
    _parse_manifest,
    _verify_wheel,
    check_for_updates,
)


def candidate(source: str, version: str, digest: str = "a" * 64) -> ReleaseCandidate:
    normalized = Version(version)
    return ReleaseCandidate(
        source=source,
        version=normalized,
        tag=f"v{normalized}",
        artifact=UpdateArtifact(
            name=f"gpt_image_2_cli-{normalized}-py3-none-any.whl",
            size=123,
            sha256=digest,
            url=f"https://example.invalid/{normalized}.whl",
        ),
        release_url=None,
    )


def test_manifest_requires_exact_package_tag_filename_and_digest() -> None:
    parsed = _parse_manifest(
        {
            "schema_version": 1,
            "package": "gpt-image-2-cli",
            "version": "0.2.0",
            "tag": "v0.2.0",
            "artifact": {
                "name": "gpt_image_2_cli-0.2.0-py3-none-any.whl",
                "size": 123,
                "sha256": "a" * 64,
            },
        }
    )
    assert parsed == (
        Version("0.2.0"),
        "v0.2.0",
        "gpt_image_2_cli-0.2.0-py3-none-any.whl",
        123,
        "a" * 64,
    )


def test_auto_source_selects_highest_consistent_version(monkeypatch: object) -> None:
    sources = (
        SourceSpec("github", "https://example.invalid/gh", "owner", "repo"),
        SourceSpec("gitee", "https://example.invalid/ge", "owner", "repo"),
        SourceSpec("gitcode", "https://example.invalid/gc", "owner", "repo"),
    )

    def fake_lookup(source: SourceSpec, **_kwargs: object) -> ReleaseCandidate:
        versions = {"github": "0.2.0", "gitee": "0.2.0", "gitcode": "0.1.0"}
        return candidate(source.name, versions[source.name])

    monkeypatch.setattr("gpt_image_cli.updater._candidate_from_source", fake_lookup)
    result = check_for_updates(sources=sources)
    assert result.candidate is not None
    assert result.candidate.source == "github"
    assert result.candidate.version == Version("0.2.0")
    assert result.update_available is False


def test_auto_source_rejects_mirror_disagreement(monkeypatch: object) -> None:
    sources = (
        SourceSpec("github", "https://example.invalid/gh", "owner", "repo"),
        SourceSpec("gitee", "https://example.invalid/ge", "owner", "repo"),
    )

    def fake_lookup(source: SourceSpec, **_kwargs: object) -> ReleaseCandidate:
        digest = ("a" if source.name == "github" else "b") * 64
        return candidate(source.name, "0.3.0", digest=digest)

    monkeypatch.setattr("gpt_image_cli.updater._candidate_from_source", fake_lookup)
    with pytest.raises(UpdateError, match="disagree"):
        check_for_updates(sources=sources)


def test_wheel_verification_checks_embedded_name_and_version(tmp_path: Path) -> None:
    wheel = tmp_path / "gpt_image_2_cli-0.3.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            "gpt_image_2_cli-0.3.0.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: gpt-image-2-cli\nVersion: 0.3.0\n",
        )
    release = ReleaseCandidate(
        source="github",
        version=Version("0.3.0"),
        tag="v0.3.0",
        artifact=UpdateArtifact(
            name=wheel.name,
            size=wheel.stat().st_size,
            sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),
            url="https://example.invalid/wheel",
        ),
        release_url=None,
    )
    _verify_wheel(wheel, release)
