from __future__ import annotations

import pytest

from gpt_image_cli.errors import ConfigError
from gpt_image_cli.proxy import resolve_proxy_config


def test_explicit_proxy_is_normalized_and_redacted_for_display() -> None:
    config = resolve_proxy_config(
        "https://relay.example/v1/images/generations",
        explicit_proxy="user:secret@127.0.0.1:7890",
    )
    assert config.url == "http://user:secret@127.0.0.1:7890"
    assert config.display_url == "http://127.0.0.1:7890"
    assert config.mode == "explicit"
    assert config.trust_env is False


def test_no_proxy_disables_all_proxy_discovery(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:7890")
    config = resolve_proxy_config(
        "https://relay.example/v1/images/generations",
        no_proxy=True,
    )
    assert config.mode == "disabled"
    assert config.url is None
    assert config.trust_env is False


def test_proxy_and_no_proxy_are_mutually_exclusive() -> None:
    with pytest.raises(ConfigError, match="either --proxy or --no-proxy"):
        resolve_proxy_config(
            "https://relay.example/v1/images/generations",
            explicit_proxy="http://127.0.0.1:7890",
            no_proxy=True,
        )
