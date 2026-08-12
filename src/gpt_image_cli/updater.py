"""Discover and install verified CLI releases from public release mirrors."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from email.parser import Parser
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

import httpx
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

from . import __version__
from .errors import UpdateError
from .proxy import resolve_proxy_config

PACKAGE_NAME = "gpt-image-2-cli"
MANIFEST_NAME = "latest.json"
MANIFEST_SCHEMA = 1
USER_AGENT = f"gpt-image-2-cli/{__version__} updater"
DOWNLOAD_CHUNK_BYTES = 1024 * 1024
MAX_MANIFEST_BYTES = 256 * 1024
MAX_WHEEL_BYTES = 64 * 1024 * 1024
AUTO_CHECK_INTERVAL_SECONDS = 24 * 60 * 60
AUTO_CHECK_TIMEOUT_SECONDS = 3
UPDATE_CHECK_DISABLED_ENV = "GPT_IMAGE_DISABLE_UPDATE_CHECK"


@dataclass(frozen=True, slots=True)
class SourceSpec:
    name: str
    api_url: str
    owner: str
    repo: str
    token_environment: str | None = None


DEFAULT_SOURCES = (
    SourceSpec(
        name="github",
        api_url="https://api.github.com/repos/Lijinzh/gpt-image-2-cli/releases/latest",
        owner="Lijinzh",
        repo="gpt-image-2-cli",
        token_environment="GITHUB_TOKEN",
    ),
    SourceSpec(
        name="gitee",
        api_url="https://gitee.com/api/v5/repos/shan-yujun/gpt-image-2-cli/releases/latest",
        owner="shan-yujun",
        repo="gpt-image-2-cli",
        token_environment="GITEE_TOKEN",
    ),
    SourceSpec(
        name="gitcode",
        api_url="https://api.gitcode.com/api/v5/repos/Lijinzh/gpt-image-2-cli/releases/latest",
        owner="Lijinzh",
        repo="gpt-image-2-cli",
        token_environment="GITCODE_TOKEN",
    ),
)


@dataclass(frozen=True, slots=True)
class UpdateArtifact:
    name: str
    size: int
    sha256: str
    url: str


@dataclass(frozen=True, slots=True)
class ReleaseCandidate:
    source: str
    version: Version
    tag: str
    artifact: UpdateArtifact
    release_url: str | None

    def public_summary(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "version": str(self.version),
            "tag": self.tag,
            "asset": self.artifact.name,
            "bytes": self.artifact.size,
            "sha256": self.artifact.sha256,
            "release_url": self.release_url,
        }


@dataclass(frozen=True, slots=True)
class UpdateCheck:
    current_version: Version
    candidate: ReleaseCandidate | None
    checked_sources: tuple[str, ...]
    source_errors: dict[str, str]

    @property
    def update_available(self) -> bool:
        return self.candidate is not None and self.candidate.version > self.current_version

    def public_summary(self) -> dict[str, Any]:
        return {
            "current_version": str(self.current_version),
            "latest_version": str(self.candidate.version) if self.candidate else None,
            "update_available": self.update_available,
            "selected_release": self.candidate.public_summary() if self.candidate else None,
            "checked_sources": list(self.checked_sources),
            "source_errors": self.source_errors,
        }


def _update_state_path() -> Path:
    override = os.getenv("GPT_IMAGE_STATE_DIR", "").strip()
    if override:
        return Path(override).expanduser() / "update-state.json"
    if sys.platform == "win32":
        root = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Caches"
    else:
        root = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))
    return root / PACKAGE_NAME / "update-state.json"


def _automatic_check_due(path: Path, *, now: float, interval: float) -> bool:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        last_checked = float(payload.get("last_checked", 0))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return True
    return now - last_checked >= interval


def _record_automatic_check(path: Path, *, now: float) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary.write_text(
            json.dumps(
                {
                    "last_checked": now,
                    "cli_version": __version__,
                    "platform": platform.system().lower(),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        temporary.replace(path)
    except OSError:
        return


def automatic_update_notice(
    *,
    now: float | None = None,
    interval: float = AUTO_CHECK_INTERVAL_SECONDS,
    timeout: float = AUTO_CHECK_TIMEOUT_SECONDS,
    state_path: Path | None = None,
) -> str | None:
    """Schedule a verified low-frequency update after the current command exits."""
    disabled = os.getenv(UPDATE_CHECK_DISABLED_ENV, "").strip().lower()
    if disabled in {"1", "true", "yes", "on"}:
        return None
    timestamp = time.time() if now is None else now
    path = state_path or _update_state_path()
    if not _automatic_check_due(path, now=timestamp, interval=interval):
        return None
    try:
        result = check_for_updates(timeout=timeout)
    except UpdateError:
        return None
    _record_automatic_check(path, now=timestamp)
    if not result.update_available or result.candidate is None:
        return None
    candidate = result.candidate
    try:
        install_update(candidate, timeout=max(30, timeout * 10))
    except UpdateError:
        return (
            f"Update available: gpt-image {result.current_version} -> {candidate.version} "
            f"({candidate.source}). Run `gpt-image update` to install it."
        )
    return (
        f"Verified gpt-image {candidate.version} from {candidate.source}; "
        "it will install automatically after this command exits."
    )


def _headers(source: SourceSpec) -> dict[str, str]:
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    token = os.getenv(source.token_environment or "", "").strip()
    if token:
        if source.name == "gitee":
            headers["Authorization"] = f"token {token}"
        else:
            headers["Authorization"] = f"Bearer {token}"
    if source.name == "github":
        headers["X-GitHub-Api-Version"] = "2022-11-28"
        headers["Accept"] = "application/vnd.github+json"
    return headers


def _client_for(
    target_url: str,
    *,
    timeout: float,
    explicit_proxy: str | None,
    no_proxy: bool,
) -> httpx.Client:
    proxy = resolve_proxy_config(
        target_url,
        explicit_proxy=explicit_proxy,
        no_proxy=no_proxy,
    )
    return httpx.Client(
        timeout=httpx.Timeout(timeout),
        follow_redirects=True,
        trust_env=proxy.trust_env,
        proxy=proxy.url,
        headers={"User-Agent": USER_AGENT},
    )


def _read_limited(response: httpx.Response, limit: int) -> bytes:
    content_length = response.headers.get("content-length")
    if content_length and int(content_length) > limit:
        raise UpdateError(f"Update metadata exceeds the {limit}-byte safety limit.")
    body = response.content
    if len(body) > limit:
        raise UpdateError(f"Update metadata exceeds the {limit}-byte safety limit.")
    return body


def _asset_map(payload: dict[str, Any]) -> dict[str, str]:
    assets = payload.get("assets")
    if not isinstance(assets, list):
        raise UpdateError("Release metadata does not contain an asset list.")
    result: dict[str, str] = {}
    for item in assets:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        url = str(item.get("browser_download_url") or "").strip()
        if not name or Path(name).name != name or not url:
            continue
        if name in result:
            raise UpdateError(f"Release contains duplicate asset name: {name}")
        result[name] = url
    return result


def _manifest_payload(body: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise UpdateError("Release latest.json is not valid UTF-8 JSON.") from exc
    if not isinstance(payload, dict):
        raise UpdateError("Release latest.json must contain a JSON object.")
    return payload


def _parse_manifest(payload: dict[str, Any]) -> tuple[Version, str, str, int, str]:
    if payload.get("schema_version") != MANIFEST_SCHEMA:
        raise UpdateError("Release latest.json uses an unsupported schema version.")
    if payload.get("package") != PACKAGE_NAME:
        raise UpdateError("Release latest.json names an unexpected package.")
    version_text = str(payload.get("version") or "").strip()
    try:
        version = Version(version_text)
    except InvalidVersion as exc:
        raise UpdateError("Release latest.json contains an invalid version.") from exc
    tag = str(payload.get("tag") or "").strip()
    if tag != f"v{version}":
        raise UpdateError("Release tag and package version do not match.")
    artifact = payload.get("artifact")
    if not isinstance(artifact, dict):
        raise UpdateError("Release latest.json does not describe the wheel artifact.")
    name = str(artifact.get("name") or "").strip()
    expected_name = f"gpt_image_2_cli-{version}-py3-none-any.whl"
    if name != expected_name or Path(name).name != name:
        raise UpdateError("Release latest.json contains an unexpected wheel filename.")
    try:
        size = int(artifact.get("size") or 0)
    except (TypeError, ValueError) as exc:
        raise UpdateError("Release latest.json contains an invalid wheel size.") from exc
    if size <= 0 or size > MAX_WHEEL_BYTES:
        raise UpdateError("Release wheel size is outside the allowed safety range.")
    digest = str(artifact.get("sha256") or "").strip().lower()
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise UpdateError("Release latest.json contains an invalid SHA-256 digest.")
    return version, tag, name, size, digest


def _validate_download_url(source: SourceSpec, tag: str, name: str, url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.username or parsed.password:
        raise UpdateError(f"{source.name} returned an unsafe release asset URL.")
    host = (parsed.hostname or "").lower()
    encoded_tag = quote(tag, safe="")
    if source.name == "github":
        expected = f"/{source.owner}/{source.repo}/releases/download/{encoded_tag}/{name}"
        valid = host == "github.com" and parsed.path == expected
    elif source.name == "gitee":
        expected = f"/{source.owner}/{source.repo}/releases/download/{encoded_tag}/{name}"
        valid = host == "gitee.com" and parsed.path == expected
    else:
        valid = host == "gitcode.com" or host.endswith(".gitcode.com")
    if not valid:
        raise UpdateError(f"{source.name} returned an asset outside the approved repository.")


def _release_page(source: SourceSpec, tag: str) -> str:
    if source.name == "github":
        return f"https://github.com/{source.owner}/{source.repo}/releases/tag/{tag}"
    if source.name == "gitee":
        return f"https://gitee.com/{source.owner}/{source.repo}/releases/tag/{tag}"
    return f"https://gitcode.com/{source.owner}/{source.repo}/-/releases/{tag}"


def _github_direct_candidate(
    source: SourceSpec,
    *,
    timeout: float,
    explicit_proxy: str | None,
    no_proxy: bool,
) -> ReleaseCandidate:
    manifest_url = (
        f"https://github.com/{source.owner}/{source.repo}/releases/latest/download/{MANIFEST_NAME}"
    )
    with _client_for(
        manifest_url,
        timeout=timeout,
        explicit_proxy=explicit_proxy,
        no_proxy=no_proxy,
    ) as client:
        response = client.get(manifest_url)
        response.raise_for_status()
        payload = _manifest_payload(_read_limited(response, MAX_MANIFEST_BYTES))
    version, tag, name, size, digest = _parse_manifest(payload)
    artifact_url = (
        f"https://github.com/{source.owner}/{source.repo}/releases/download/"
        f"{quote(tag, safe='')}/{name}"
    )
    _validate_download_url(source, tag, name, artifact_url)
    return ReleaseCandidate(
        source=source.name,
        version=version,
        tag=tag,
        artifact=UpdateArtifact(name=name, size=size, sha256=digest, url=artifact_url),
        release_url=_release_page(source, tag),
    )


def _candidate_from_source(
    source: SourceSpec,
    *,
    timeout: float,
    explicit_proxy: str | None,
    no_proxy: bool,
) -> ReleaseCandidate:
    try:
        with _client_for(
            source.api_url,
            timeout=timeout,
            explicit_proxy=explicit_proxy,
            no_proxy=no_proxy,
        ) as client:
            response = client.get(source.api_url, headers=_headers(source))
            response.raise_for_status()
            release = response.json()
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        if source.name == "github":
            try:
                return _github_direct_candidate(
                    source,
                    timeout=timeout,
                    explicit_proxy=explicit_proxy,
                    no_proxy=no_proxy,
                )
            except (httpx.HTTPError, UpdateError) as fallback_exc:
                raise UpdateError(f"GitHub release lookup failed: {fallback_exc}") from exc
        raise UpdateError(f"{source.name} release lookup failed: {exc}") from exc
    if not isinstance(release, dict):
        raise UpdateError(f"{source.name} returned invalid release metadata.")
    assets = _asset_map(release)
    manifest_url = assets.get(MANIFEST_NAME)
    if not manifest_url:
        raise UpdateError(f"{source.name} latest release does not contain {MANIFEST_NAME}.")
    with _client_for(
        manifest_url,
        timeout=timeout,
        explicit_proxy=explicit_proxy,
        no_proxy=no_proxy,
    ) as client:
        try:
            response = client.get(manifest_url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise UpdateError(f"Could not download {source.name} {MANIFEST_NAME}: {exc}") from exc
        manifest = _manifest_payload(_read_limited(response, MAX_MANIFEST_BYTES))
    version, tag, name, size, digest = _parse_manifest(manifest)
    release_tag = str(release.get("tag_name") or "").strip()
    if release_tag and release_tag != tag:
        raise UpdateError(f"{source.name} release tag does not match {MANIFEST_NAME}.")
    artifact_url = assets.get(name)
    if not artifact_url and source.name in {"github", "gitee"}:
        artifact_url = (
            f"https://{source.name}.com/{source.owner}/{source.repo}/releases/download/"
            f"{quote(tag, safe='')}/{name}"
        )
    if not artifact_url:
        raise UpdateError(f"{source.name} latest release does not contain {name}.")
    _validate_download_url(source, tag, name, artifact_url)
    return ReleaseCandidate(
        source=source.name,
        version=version,
        tag=tag,
        artifact=UpdateArtifact(name=name, size=size, sha256=digest, url=artifact_url),
        release_url=str(release.get("html_url") or "").strip() or _release_page(source, tag),
    )


def check_for_updates(
    *,
    source_name: str = "auto",
    allow_prerelease: bool = False,
    timeout: float = 15,
    explicit_proxy: str | None = None,
    no_proxy: bool = False,
    sources: tuple[SourceSpec, ...] = DEFAULT_SOURCES,
) -> UpdateCheck:
    if timeout <= 0:
        raise UpdateError("Update timeout must be greater than zero.")
    selected = tuple(source for source in sources if source_name in {"auto", source.name})
    if not selected:
        raise UpdateError(f"Unknown update source: {source_name}")
    candidates: list[ReleaseCandidate] = []
    errors: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=len(selected)) as executor:
        futures = {
            executor.submit(
                _candidate_from_source,
                source,
                timeout=timeout,
                explicit_proxy=explicit_proxy,
                no_proxy=no_proxy,
            ): source
            for source in selected
        }
        for future in as_completed(futures):
            source = futures[future]
            try:
                candidate = future.result()
            except (UpdateError, httpx.HTTPError, ValueError) as exc:
                errors[source.name] = str(exc)
                continue
            if candidate.version.is_prerelease and not allow_prerelease:
                errors[source.name] = "latest release is a prerelease"
                continue
            candidates.append(candidate)
    if not candidates:
        details = "; ".join(f"{name}: {message}" for name, message in sorted(errors.items()))
        raise UpdateError(f"No usable release source was available. {details}")
    latest_version = max(candidate.version for candidate in candidates)
    latest = [candidate for candidate in candidates if candidate.version == latest_version]
    identities = {(item.artifact.name, item.artifact.size, item.artifact.sha256) for item in latest}
    if len(identities) != 1:
        raise UpdateError(
            f"Release mirrors disagree about the artifacts for version {latest_version}."
        )
    priority = {source.name: index for index, source in enumerate(sources)}
    candidate = min(latest, key=lambda item: priority.get(item.source, len(priority)))
    try:
        current = Version(__version__)
    except InvalidVersion as exc:
        raise UpdateError("The installed CLI has an invalid version string.") from exc
    return UpdateCheck(
        current_version=current,
        candidate=candidate,
        checked_sources=tuple(source.name for source in selected),
        source_errors=errors,
    )


def _verify_wheel(path: Path, candidate: ReleaseCandidate) -> None:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if path.stat().st_size != candidate.artifact.size:
        raise UpdateError("Downloaded wheel size does not match latest.json.")
    if digest != candidate.artifact.sha256:
        raise UpdateError("Downloaded wheel SHA-256 does not match latest.json.")
    try:
        with zipfile.ZipFile(path) as archive:
            metadata_names = [
                name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
            ]
            if len(metadata_names) != 1:
                raise UpdateError("Downloaded wheel contains invalid package metadata.")
            metadata = Parser().parsestr(archive.read(metadata_names[0]).decode("utf-8"))
    except (OSError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
        raise UpdateError("Downloaded update is not a valid Python wheel.") from exc
    if canonicalize_name(metadata.get("Name", "")) != canonicalize_name(PACKAGE_NAME):
        raise UpdateError("Downloaded wheel contains an unexpected package.")
    if metadata.get("Version") != str(candidate.version):
        raise UpdateError("Downloaded wheel version does not match latest.json.")


def download_update(
    candidate: ReleaseCandidate,
    destination: Path,
    *,
    timeout: float = 60,
    explicit_proxy: str | None = None,
    no_proxy: bool = False,
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.part")
    digest = hashlib.sha256()
    total = 0
    try:
        with (
            _client_for(
                candidate.artifact.url,
                timeout=timeout,
                explicit_proxy=explicit_proxy,
                no_proxy=no_proxy,
            ) as client,
            client.stream("GET", candidate.artifact.url) as response,
        ):
            response.raise_for_status()
            with temporary.open("wb") as output:
                for chunk in response.iter_bytes(DOWNLOAD_CHUNK_BYTES):
                    total += len(chunk)
                    if total > candidate.artifact.size or total > MAX_WHEEL_BYTES:
                        raise UpdateError("Downloaded wheel exceeded its declared size.")
                    digest.update(chunk)
                    output.write(chunk)
        if total != candidate.artifact.size or digest.hexdigest() != candidate.artifact.sha256:
            raise UpdateError("Downloaded wheel failed size or SHA-256 verification.")
        temporary.replace(destination)
        _verify_wheel(destination, candidate)
        return destination
    except (httpx.HTTPError, OSError) as exc:
        raise UpdateError(f"Could not download the verified update: {exc}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def _uv_manages_current_environment(uv: str) -> bool:
    result = subprocess.run(
        [uv, "tool", "dir"],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return False
    try:
        Path(sys.executable).resolve().relative_to(Path(result.stdout.strip()).resolve())
    except ValueError:
        return False
    return True


def _quote_powershell(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _update_work_dir() -> Path:
    path = _update_state_path().parent / "updates"
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise UpdateError(f"Could not create the update working directory: {exc}") from exc
    return path


def _write_update_helper(uv: str, wheel: Path, candidate: ReleaseCandidate) -> Path:
    work_dir = wheel.parent
    suffix = f"{candidate.version}-{os.getpid()}"
    result_path = work_dir / f"result-{suffix}.json"
    log_path = work_dir / f"install-{suffix}.log"
    uv_text = _quote_powershell(uv)
    wheel_text = _quote_powershell(str(wheel))
    log_text = _quote_powershell(str(log_path))
    result_text = _quote_powershell(str(result_path))
    version_text = _quote_powershell(str(candidate.version))
    if sys.platform == "win32":
        helper = work_dir / f"install-{suffix}.ps1"
        content = f"""$ErrorActionPreference = 'SilentlyContinue'
try {{ Wait-Process -Id {os.getpid()} -ErrorAction SilentlyContinue }} catch {{}}
Start-Sleep -Milliseconds 750
$env:UV_NO_PROGRESS = '1'
& {uv_text} tool install --force {wheel_text} *> {log_text}
$code = $LASTEXITCODE
$status = if ($code -eq 0) {{ 'success' }} else {{ 'failed' }}
@{{status=$status; exit_code=$code; version={version_text}}} |
    ConvertTo-Json -Compress |
    Set-Content -LiteralPath {result_text} -Encoding UTF8
Remove-Item -LiteralPath {wheel_text} -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $MyInvocation.MyCommand.Path -Force -ErrorAction SilentlyContinue
exit $code
"""
    else:
        helper = work_dir / f"install-{suffix}.sh"
        uv_shell = shlex.quote(uv)
        wheel_shell = shlex.quote(str(wheel))
        log_shell = shlex.quote(str(log_path))
        result_shell = shlex.quote(str(result_path))
        version_shell = shlex.quote(str(candidate.version))
        content = f"""#!/bin/sh
while kill -0 {os.getpid()} 2>/dev/null; do sleep 1; done
sleep 1
UV_NO_PROGRESS=1 {uv_shell} tool install --force {wheel_shell} \\
    >{log_shell} 2>&1
code=$?
if [ "$code" -eq 0 ]; then status=success; else status=failed; fi
printf '{{"status":"%s","exit_code":%s,"version":"%s"}}\n' \\
    "$status" "$code" {version_shell} >{result_shell}
rm -f -- {wheel_shell} "$0"
exit "$code"
"""
    try:
        helper.write_text(content, encoding="utf-8", newline="\n")
        if sys.platform != "win32":
            helper.chmod(0o700)
    except OSError as exc:
        raise UpdateError(f"Could not create the update helper: {exc}") from exc
    return helper


def _launch_update_helper(helper: Path) -> None:
    try:
        if sys.platform == "win32":
            powershell = (
                shutil.which("powershell.exe") or shutil.which("pwsh.exe") or shutil.which("pwsh")
            )
            if not powershell:
                raise UpdateError("PowerShell is required to finish the Windows self-update.")
            subprocess.Popen(
                [
                    powershell,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(helper),
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            subprocess.Popen(
                ["/bin/sh", str(helper)],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                start_new_session=True,
            )
    except OSError as exc:
        raise UpdateError(f"Could not start the update helper: {exc}") from exc


def install_update(
    candidate: ReleaseCandidate,
    *,
    timeout: float = 60,
    explicit_proxy: str | None = None,
    no_proxy: bool = False,
) -> dict[str, Any]:
    uv = shutil.which("uv")
    if not uv:
        raise UpdateError(
            "uv is required for self-update. Install uv, then run this command again."
        )
    if not _uv_manages_current_environment(uv):
        raise UpdateError(
            "This copy is not running from a uv-managed tool environment. "
            "Reinstall with `uv tool install --force <verified-wheel>` or update it through "
            "the package manager that installed it."
        )
    work_dir = _update_work_dir()
    wheel = download_update(
        candidate,
        work_dir / candidate.artifact.name,
        timeout=timeout,
        explicit_proxy=explicit_proxy,
        no_proxy=no_proxy,
    )
    helper = _write_update_helper(uv, wheel, candidate)
    try:
        _launch_update_helper(helper)
    except UpdateError:
        helper.unlink(missing_ok=True)
        wheel.unlink(missing_ok=True)
        raise
    return {
        "success": True,
        "updated": False,
        "update_scheduled": True,
        "previous_version": __version__,
        "version": str(candidate.version),
        "source": candidate.source,
        "asset": candidate.artifact.name,
        "sha256": candidate.artifact.sha256,
        "release_url": candidate.release_url,
    }
