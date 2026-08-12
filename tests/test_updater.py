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
    automatic_update_notice,
    check_for_updates,
    install_update,
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


def test_automatic_notice_is_rate_limited(monkeypatch: object, tmp_path: Path) -> None:
    state_path = tmp_path / "state" / "update-state.json"
    release = candidate("github", "0.3.0")
    calls = 0

    def fake_check(**_kwargs: object) -> object:
        nonlocal calls
        calls += 1
        from gpt_image_cli.updater import UpdateCheck

        return UpdateCheck(
            current_version=Version("0.2.0"),
            candidate=release,
            checked_sources=("github",),
            source_errors={},
        )

    monkeypatch.setattr("gpt_image_cli.updater.check_for_updates", fake_check)
    monkeypatch.setattr(
        "gpt_image_cli.updater.install_update",
        lambda *_args, **_kwargs: {"update_scheduled": True},
    )
    first = automatic_update_notice(now=1000, interval=100, state_path=state_path)
    second = automatic_update_notice(now=1050, interval=100, state_path=state_path)
    third = automatic_update_notice(now=1101, interval=100, state_path=state_path)
    assert "install automatically" in (first or "")
    assert second is None
    assert "install automatically" in (third or "")
    assert calls == 2


def test_automatic_notice_falls_back_to_manual_instruction(
    monkeypatch: object, tmp_path: Path
) -> None:
    from gpt_image_cli.updater import UpdateCheck

    monkeypatch.setattr(
        "gpt_image_cli.updater.check_for_updates",
        lambda **_kwargs: UpdateCheck(
            current_version=Version("0.2.0"),
            candidate=candidate("github", "0.3.0"),
            checked_sources=("github",),
            source_errors={},
        ),
    )
    monkeypatch.setattr(
        "gpt_image_cli.updater.install_update",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(UpdateError("not uv managed")),
    )
    notice = automatic_update_notice(state_path=tmp_path / "state.json")
    assert "Run `gpt-image update`" in (notice or "")


def test_automatic_notice_can_be_disabled(monkeypatch: object, tmp_path: Path) -> None:
    monkeypatch.setenv("GPT_IMAGE_DISABLE_UPDATE_CHECK", "1")
    monkeypatch.setattr(
        "gpt_image_cli.updater.check_for_updates",
        lambda **_kwargs: pytest.fail("disabled update check should not use the network"),
    )
    assert automatic_update_notice(state_path=tmp_path / "state.json") is None


def test_install_update_schedules_verified_wheel(
    monkeypatch: object, tmp_path: Path
) -> None:
    release = candidate("github", "0.3.0")
    launched: list[Path] = []

    monkeypatch.setattr("gpt_image_cli.updater.shutil.which", lambda _name: "uv")
    monkeypatch.setattr(
        "gpt_image_cli.updater._uv_manages_current_environment",
        lambda _uv: True,
    )
    monkeypatch.setattr(
        "gpt_image_cli.updater._update_work_dir",
        lambda: tmp_path / "updates",
    )

    def fake_download(_candidate: object, destination: Path, **_kwargs: object) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"verified wheel")
        return destination

    def fake_write_helper(_uv: str, _wheel: Path, _candidate: object) -> Path:
        helper = tmp_path / "updates" / "install-update.ps1"
        helper.write_text("# helper", encoding="utf-8")
        return helper

    monkeypatch.setattr("gpt_image_cli.updater.download_update", fake_download)
    monkeypatch.setattr("gpt_image_cli.updater._write_update_helper", fake_write_helper)
    monkeypatch.setattr(
        "gpt_image_cli.updater._launch_update_helper", lambda helper: launched.append(helper)
    )

    result = install_update(release)

    assert result["success"] is True
    assert result["updated"] is False
    assert result["update_scheduled"] is True
    assert result["version"] == "0.3.0"
    assert launched == [tmp_path / "updates" / "install-update.ps1"]
