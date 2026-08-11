from __future__ import annotations

import json
import os
import re
import sqlite3
import tomllib
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .errors import ConfigError


@dataclass(frozen=True, slots=True)
class ApiConfig:
    provider: str
    api_base: str
    api_key: str = field(repr=False)
    source: str

    @property
    def images_endpoint(self) -> str:
        return f"{self.api_base}/images/generations"

    @property
    def models_endpoint(self) -> str:
        return f"{self.api_base}/models"


def normalize_api_base(value: str, *, allow_http: bool = False) -> str:
    api_base = value.strip().rstrip("/")
    parsed = urlparse(api_base)
    if not parsed.scheme or not parsed.netloc:
        raise ConfigError("API base URL is not a valid absolute URL.")
    if parsed.username or parsed.password:
        raise ConfigError("API base URL must not contain embedded credentials.")
    if parsed.query or parsed.fragment:
        raise ConfigError("API base URL must not contain a query string or fragment.")
    if parsed.scheme != "https":
        is_local = parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        if not (allow_http or is_local):
            raise ConfigError("Refusing a non-HTTPS API base URL; use --allow-http intentionally.")
    return api_base


def _parse_base_url(config_text: str) -> str:
    try:
        config = tomllib.loads(config_text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Current CC-Switch provider config is invalid TOML: {exc}") from exc

    provider_id = config.get("model_provider")
    providers = config.get("model_providers", {})
    provider_config = providers.get(provider_id, {}) if provider_id else {}
    base_url = provider_config.get("base_url")
    if not isinstance(base_url, str) or not base_url.strip():
        match = re.search(r"(?m)^\s*base_url\s*=\s*['\"]([^'\"]+)['\"]", config_text)
        base_url = match.group(1) if match else ""
    if not base_url:
        raise ConfigError("Current CC-Switch provider does not define base_url.")
    return base_url


def _open_readonly_database(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise ConfigError(f"CC-Switch database not found: {path}")
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def load_cc_switch(db_path: Path, *, allow_http: bool = False) -> ApiConfig:
    try:
        with closing(_open_readonly_database(db_path)) as database:
            row = database.execute(
                """
                SELECT name, settings_config
                FROM providers
                WHERE app_type = 'codex' AND is_current = 1
                ORDER BY sort_index ASC
                LIMIT 1
                """
            ).fetchone()
    except sqlite3.Error as exc:
        raise ConfigError(f"Cannot read CC-Switch provider database: {exc}") from exc

    if row is None:
        raise ConfigError("CC-Switch has no current Codex provider.")
    provider_name, settings_text = row
    try:
        settings: dict[str, Any] = json.loads(settings_text)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ConfigError("Current CC-Switch provider settings are invalid JSON.") from exc

    auth = settings.get("auth", {})
    api_key = auth.get("OPENAI_API_KEY") if isinstance(auth, dict) else None
    config_text = settings.get("config")
    if not isinstance(api_key, str) or not api_key.strip():
        raise ConfigError("Current CC-Switch Codex provider has no OPENAI_API_KEY.")
    if not isinstance(config_text, str) or not config_text.strip():
        raise ConfigError("Current CC-Switch Codex provider has no config text.")

    return ApiConfig(
        provider=str(provider_name or "CC-Switch"),
        api_base=normalize_api_base(_parse_base_url(config_text), allow_http=allow_http),
        api_key=api_key,
        source="cc-switch",
    )


def resolve_api_config(
    *,
    api_base: str | None,
    cc_switch_db: Path,
    allow_http: bool = False,
) -> ApiConfig:
    direct_base = api_base or os.getenv("GPT_IMAGE_API_BASE") or os.getenv("OPENAI_BASE_URL")
    direct_key = os.getenv("GPT_IMAGE_API_KEY") or os.getenv("OPENAI_API_KEY")

    if direct_base or direct_key:
        if not direct_base or not direct_key:
            raise ConfigError(
                "Direct configuration needs both GPT_IMAGE_API_BASE and GPT_IMAGE_API_KEY."
            )
        return ApiConfig(
            provider="environment",
            api_base=normalize_api_base(direct_base, allow_http=allow_http),
            api_key=direct_key,
            source="environment",
        )

    return load_cc_switch(cc_switch_db, allow_http=allow_http)


def redact(text: str, api_key: str = "") -> str:
    safe = text.replace(api_key, "<redacted>") if api_key else text
    safe = re.sub(r"(?i)bearer\s+[A-Za-z0-9._~+\-/=]+", "Bearer <redacted>", safe)
    return safe[:4000]
