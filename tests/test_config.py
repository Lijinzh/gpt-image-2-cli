from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from gpt_image_cli.config import ConfigError, load_cc_switch, normalize_api_base


def test_normalize_api_base_allows_local_http() -> None:
    assert normalize_api_base("http://127.0.0.1:9999/v1/") == "http://127.0.0.1:9999/v1"


def test_normalize_api_base_rejects_remote_http() -> None:
    with pytest.raises(ConfigError, match="non-HTTPS"):
        normalize_api_base("http://example.com/v1")


def test_load_cc_switch_reads_current_codex_provider(tmp_path: Path) -> None:
    database_path = tmp_path / "cc-switch.db"
    database = sqlite3.connect(database_path)
    database.execute(
        "CREATE TABLE providers "
        "(name TEXT, settings_config TEXT, app_type TEXT, is_current INTEGER, sort_index INTEGER)"
    )
    settings = {
        "auth": {"OPENAI_API_KEY": "secret-test-key"},
        "config": (
            'model_provider = "relay"\n'
            "[model_providers.relay]\n"
            'base_url = "https://relay.example/v1"\n'
        ),
    }
    database.execute(
        "INSERT INTO providers VALUES (?, ?, ?, ?, ?)",
        ("Test Relay", json.dumps(settings), "codex", 1, 0),
    )
    database.commit()
    database.close()

    config = load_cc_switch(database_path)
    assert config.provider == "Test Relay"
    assert config.api_base == "https://relay.example/v1"
    assert config.api_key == "secret-test-key"
    assert config.images_endpoint.endswith("/images/generations")
