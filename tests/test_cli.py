from __future__ import annotations

import json
import signal
import subprocess
import sys
from pathlib import Path

from packaging.version import Version

from gpt_image_cli.cli import main
from gpt_image_cli.models import GenerationResult, ImagePayload
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


def test_jsonl_progress_keeps_final_json_on_stdout(
    monkeypatch: object,
    capsys: object,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GPT_IMAGE_API_BASE", "https://relay.example/v1")
    monkeypatch.setenv("GPT_IMAGE_API_KEY", "must-never-be-printed")

    def generate(_self: object, _options: object, **kwargs: object) -> GenerationResult:
        state = kwargs["request_state"]
        callback = kwargs["progress_callback"]
        callback(
            "connection_retry",
            {
                "attempt": 1,
                "maximum_retries": 2,
                "request_submitted": False,
                "possibly_billed": False,
                "automatic_retry": True,
            },
        )
        state.mark_submitted()
        callback("request_submitted", {"elapsed_seconds": 0.01})
        callback("heartbeat", {"elapsed_seconds": 15})
        return GenerationResult(
            images=(ImagePayload(b"not-used", "base64"),),
            elapsed_seconds=15.2,
            request_id="req-jsonl",
            response_bytes=8,
        )

    monkeypatch.setattr("gpt_image_cli.cli.ImageClient.generate", generate)
    monkeypatch.setattr(
        "gpt_image_cli.cli.save_images",
        lambda *_args, **_kwargs: [],
    )

    exit_code = main(
        [
            "generate",
            "jsonl test",
            "--output",
            str(tmp_path / "result.png"),
            "--json",
            "--jsonl-progress",
        ]
    )

    captured = capsys.readouterr()
    final = json.loads(captured.out)
    events = [json.loads(line) for line in captured.err.splitlines()]
    assert exit_code == 0
    assert final["success"] is True
    assert [event["event"] for event in events] == [
        "request_started",
        "connection_retry",
        "request_submitted",
        "heartbeat",
        "completed",
    ]
    assert events[1]["automatic_retry"] is True
    assert events[1]["request_submitted"] is False
    assert events[1]["possibly_billed"] is False
    assert events[2]["request_submitted"] is True
    assert events[2]["possibly_billed"] is True
    assert "automatic_retry" not in events[0]
    assert all(event["automatic_retry"] is False for event in events[2:])
    assert "must-never-be-printed" not in captured.out
    assert "must-never-be-printed" not in captured.err


def test_sigterm_after_submission_reports_billing_risk_without_output(
    monkeypatch: object,
    capsys: object,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GPT_IMAGE_API_BASE", "https://relay.example/v1")
    monkeypatch.setenv("GPT_IMAGE_API_KEY", "must-never-be-printed")
    output = tmp_path / "must-not-exist.png"
    calls = 0

    def interrupted(_self: object, _options: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        state = kwargs["request_state"]
        callback = kwargs["progress_callback"]
        state.mark_submitted()
        callback("request_submitted", {"elapsed_seconds": 0.01})
        signal.raise_signal(signal.SIGTERM)

    monkeypatch.setattr("gpt_image_cli.cli.ImageClient.generate", interrupted)

    exit_code = main(
        [
            "generate",
            "interrupt test",
            "--output",
            str(output),
            "--jsonl-progress",
            "--no-progress",
        ]
    )

    captured = capsys.readouterr()
    json_lines = [
        json.loads(line)
        for line in captured.err.splitlines()
        if line.startswith("{")
    ]
    assert exit_code == 128 + signal.SIGTERM
    assert calls == 1
    assert output.exists() is False
    assert [event["event"] for event in json_lines] == [
        "request_started",
        "request_submitted",
        "interrupted",
    ]
    assert json_lines[-1] == {
        "event": "interrupted",
        "signal": "SIGTERM",
        "request_submitted": True,
        "possibly_billed": True,
        "automatic_retry": False,
    }
    assert "request_submitted=true possibly_billed=true automatic_retry=false" in captured.err
    assert "must-never-be-printed" not in captured.out
    assert "must-never-be-printed" not in captured.err


def test_keyboard_interrupt_before_submission_is_not_marked_billed(
    monkeypatch: object,
    capsys: object,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GPT_IMAGE_API_BASE", "https://relay.example/v1")
    monkeypatch.setenv("GPT_IMAGE_API_KEY", "must-never-be-printed")

    def interrupted(_self: object, _options: object, **_kwargs: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr("gpt_image_cli.cli.ImageClient.generate", interrupted)

    exit_code = main(
        [
            "generate",
            "interrupt before submit",
            "--output",
            str(tmp_path / "must-not-exist.png"),
            "--jsonl-progress",
            "--no-progress",
        ]
    )

    captured = capsys.readouterr()
    json_lines = [
        json.loads(line)
        for line in captured.err.splitlines()
        if line.startswith("{")
    ]
    assert exit_code == 130
    assert json_lines[-1] == {
        "event": "interrupted",
        "signal": "KeyboardInterrupt",
        "request_submitted": False,
        "possibly_billed": False,
        "automatic_retry": False,
    }
    assert "request_submitted=false possibly_billed=false automatic_retry=false" in captured.err
    assert "may already have been billed" not in captured.err
    assert "must-never-be-printed" not in captured.err


def test_no_progress_suppresses_jsonl_heartbeat_but_keeps_lifecycle_events(
    monkeypatch: object,
    capsys: object,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("GPT_IMAGE_API_BASE", "https://relay.example/v1")
    monkeypatch.setenv("GPT_IMAGE_API_KEY", "test-key")

    def generate(_self: object, _options: object, **kwargs: object) -> GenerationResult:
        state = kwargs["request_state"]
        callback = kwargs["progress_callback"]
        assert kwargs["emit_progress_heartbeats"] is False
        state.mark_submitted()
        callback("request_submitted", {"elapsed_seconds": 0.01})
        return GenerationResult(
            images=(ImagePayload(b"not-used", "base64"),),
            elapsed_seconds=0.02,
            request_id=None,
            response_bytes=8,
        )

    monkeypatch.setattr("gpt_image_cli.cli.ImageClient.generate", generate)
    monkeypatch.setattr("gpt_image_cli.cli.save_images", lambda *_args, **_kwargs: [])

    assert main(
        [
            "generate",
            "no heartbeat",
            "--output",
            str(tmp_path / "result.png"),
            "--json",
            "--jsonl-progress",
            "--no-progress",
        ]
    ) == 0

    events = [json.loads(line)["event"] for line in capsys.readouterr().err.splitlines()]
    assert events == ["request_started", "request_submitted", "completed"]
