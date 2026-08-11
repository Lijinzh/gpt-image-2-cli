from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from gpt_image_cli.cli import main


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
