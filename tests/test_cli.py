from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from packaging.version import Version

from gpt_image_cli.cli import main
from gpt_image_cli.updater import ReleaseCandidate, UpdateArtifact, UpdateCheck


def test_generate_dry_run_is_machine_readable_and_redacts_key(
    monkeypatch: object,
    capsys: object,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GPT_IMAGE_API_BASE", "https://relay.example/v1")
    monkeypatch.setenv("GPT_IMAGE_API_KEY", "must-never-be-printed")

    exit_code = main(
        [
            "generate",
            "a test image",
            "--size",
            "landscape",
            "--output",
            str(tmp_path / "result.png"),
            "--dry-run",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["success"] is True
    assert payload["parameters"]["size"] == "1536x1024"
    assert "must-never-be-printed" not in captured.out
    assert "must-never-be-printed" not in captured.err


def test_python_module_entrypoint_displays_help() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "gpt_image_cli", "--help"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0
    assert "Generate and validate GPT-Image output" in completed.stdout


def test_update_check_is_machine_readable(monkeypatch: object, capsys: object) -> None:
    candidate = ReleaseCandidate(
        source="gitee",
        version=Version("0.3.0"),
        tag="v0.3.0",
        artifact=UpdateArtifact(
            name="gpt_image_2_cli-0.3.0-py3-none-any.whl",
            size=123,
            sha256="a" * 64,
            url="https://gitee.com/example/release.whl",
        ),
        release_url="https://gitee.com/example/releases/tag/v0.3.0",
    )
    monkeypatch.setattr(
        "gpt_image_cli.cli.check_for_updates",
        lambda **_kwargs: UpdateCheck(
            current_version=Version("0.2.0"),
            candidate=candidate,
            checked_sources=("github", "gitee", "gitcode"),
            source_errors={"github": "unavailable"},
        ),
    )
    assert main(["update", "--check", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["update_available"] is True
    assert payload["latest_version"] == "0.3.0"
    assert payload["selected_release"]["source"] == "gitee"
