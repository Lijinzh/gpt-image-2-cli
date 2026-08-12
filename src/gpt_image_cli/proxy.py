"""Resolve an explicit, environment, or Windows system proxy for HTTPX."""

from __future__ import annotations

import fnmatch
import os
import sys
from dataclasses import dataclass
from urllib.parse import urlparse, urlsplit, urlunsplit

from .errors import ConfigError


@dataclass(frozen=True, slots=True)
class ProxyConfig:
    mode: str
    url: str | None
    trust_env: bool

    @property
    def display_url(self) -> str | None:
        if not self.url:
            return None
        parsed = urlsplit(self.url)
        hostname = parsed.hostname or ""
        if ":" in hostname and not hostname.startswith("["):
            hostname = f"[{hostname}]"
        netloc = hostname
        if parsed.port is not None:
            netloc = f"{netloc}:{parsed.port}"
        return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def _normalize_proxy_url(value: str) -> str:
    candidate = value.strip()
    if "://" not in candidate:
        candidate = f"http://{candidate}"
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ConfigError("Proxy must be an absolute http:// or https:// URL.")
    return candidate


def _environment_has_proxy() -> bool:
    return any(
        os.getenv(name)
        for name in (
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
        )
    )


def _matches_windows_override(hostname: str, override: str) -> bool:
    for raw_pattern in override.split(";"):
        pattern = raw_pattern.strip()
        if not pattern:
            continue
        if pattern == "<local>" and "." not in hostname:
            return True
        if pattern == "<-loopback>":
            continue
        if fnmatch.fnmatch(hostname.lower(), pattern.lower()):
            return True
    return False


def _select_windows_proxy(proxy_server: str, scheme: str) -> str | None:
    if ";" not in proxy_server and "=" not in proxy_server:
        return proxy_server
    entries: dict[str, str] = {}
    for item in proxy_server.split(";"):
        key, separator, value = item.partition("=")
        if separator and value.strip():
            entries[key.strip().lower()] = value.strip()
    return entries.get(scheme) or entries.get("https") or entries.get("http")


def _windows_system_proxy(target_url: str) -> str | None:
    if sys.platform != "win32":
        return None
    try:
        import winreg

        path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            enabled = int(winreg.QueryValueEx(key, "ProxyEnable")[0])
            server = str(winreg.QueryValueEx(key, "ProxyServer")[0])
            try:
                override = str(winreg.QueryValueEx(key, "ProxyOverride")[0])
            except FileNotFoundError:
                override = ""
    except (FileNotFoundError, OSError, ValueError):
        return None
    if not enabled or not server.strip():
        return None
    parsed_target = urlparse(target_url)
    hostname = parsed_target.hostname or ""
    if _matches_windows_override(hostname, override):
        return None
    selected = _select_windows_proxy(server, parsed_target.scheme)
    return _normalize_proxy_url(selected) if selected else None


def resolve_proxy_config(
    target_url: str,
    *,
    explicit_proxy: str | None = None,
    no_proxy: bool = False,
) -> ProxyConfig:
    if explicit_proxy and no_proxy:
        raise ConfigError("Use either --proxy or --no-proxy, not both.")
    if no_proxy:
        return ProxyConfig(mode="disabled", url=None, trust_env=False)
    if explicit_proxy:
        return ProxyConfig(
            mode="explicit",
            url=_normalize_proxy_url(explicit_proxy),
            trust_env=False,
        )
    if _environment_has_proxy():
        return ProxyConfig(mode="environment", url=None, trust_env=True)
    system_proxy = _windows_system_proxy(target_url)
    if system_proxy:
        return ProxyConfig(mode="windows-system", url=system_proxy, trust_env=False)
    return ProxyConfig(mode="direct", url=None, trust_env=False)
