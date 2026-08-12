#!/usr/bin/env python3
"""Mirror the latest GitHub wheel and latest.json to Gitee or GitCode."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = "gpt-image-2-cli-release-sync/1.0"


def request_json(
    method: str,
    url: str,
    *,
    token: str = "",
    token_in_query: bool = False,
    form_encoded: bool = False,
    fields: dict[str, object] | None = None,
    expected: tuple[int, ...] = (200,),
) -> object:
    safe_url = url.split("?", maxsplit=1)[0]
    if token and token_in_query:
        separator = "&" if "?" in url else "?"
        url = f"{url}{separator}{urllib.parse.urlencode({'access_token': token})}"
    request_fields = dict(fields or {})
    if token and form_encoded:
        request_fields["access_token"] = token
    if fields is None:
        data = None
    elif form_encoded:
        data = urllib.parse.urlencode(request_fields).encode("utf-8")
    else:
        data = json.dumps(request_fields).encode("utf-8")
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if fields is not None and not form_encoded:
        headers["Content-Type"] = "application/json"
    if form_encoded:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if token and not token_in_query:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            status = int(response.status)
            body = response.read()
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = exc.read()
    if status not in expected:
        raise RuntimeError(f"HTTP {status} from {safe_url}: {body[:600].decode(errors='replace')}")
    return json.loads(body.decode("utf-8")) if body.strip() else {}


def multipart_upload(
    url: str,
    path: Path,
    *,
    field: str,
    token: str,
    token_field: bool = False,
) -> object:
    boundary = f"----gpt-image-release-{secrets.token_hex(16)}"
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    prefix = b""
    if token_field:
        prefix = (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="access_token"\r\n\r\n'
            f"{token}\r\n"
        ).encode()
    body = (
        prefix
        + (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{field}"; filename="{path.name}"\r\n'
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode()
        + path.read_bytes()
        + f"\r\n--{boundary}--\r\n".encode()
    )
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "User-Agent": USER_AGENT,
    }
    if not token_field:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        payload = response.read()
    return json.loads(payload.decode("utf-8")) if payload.strip() else {}


def github_release(repository: str) -> dict[str, object]:
    payload = request_json(
        "GET",
        f"https://api.github.com/repos/{repository}/releases/latest",
        token=os.getenv("GITHUB_TOKEN", ""),
    )
    if not isinstance(payload, dict):
        raise RuntimeError("GitHub latest release returned an invalid payload")
    return payload


def download_assets(release: dict[str, object]) -> list[Path]:
    wanted = {"latest.json"}
    assets = release.get("assets")
    if not isinstance(assets, list):
        raise RuntimeError("GitHub release has no asset list")
    selected = []
    for item in assets:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        if name.endswith(".whl") or name in wanted:
            selected.append(item)
    if len(selected) != 2:
        raise RuntimeError("GitHub release must contain exactly one wheel and latest.json")
    output = []
    for item in selected:
        name = str(item["name"])
        url = str(item["browser_download_url"])
        destination = Path("dist") / name
        with urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=180
        ) as response:
            destination.write_bytes(response.read())
        output.append(destination)
    return output


def sync_gitee(release: dict[str, object], assets: list[Path]) -> None:
    token = os.environ["GITEE_TOKEN"]
    owner = os.environ["GITEE_OWNER"]
    repo = os.environ["GITEE_REPO"]
    tag = str(release["tag_name"])
    base = f"https://gitee.com/api/v5/repos/{owner}/{repo}/releases"
    try:
        target = request_json("GET", f"{base}/tags/{tag}")
    except RuntimeError as exc:
        if "HTTP 404" not in str(exc):
            raise
        target = request_json(
            "POST",
            base,
            token=token,
            form_encoded=True,
            fields={
                "tag_name": tag,
                "name": str(release.get("name") or tag),
                "body": str(release.get("body") or ""),
                "target_commitish": str(release.get("target_commitish") or "main"),
            },
            expected=(201,),
        )
    if not isinstance(target, dict) or not target.get("id"):
        raise RuntimeError("Gitee release creation returned an invalid payload")
    release_id = int(target["id"])
    existing = request_json(
        "GET",
        f"{base}/{release_id}/attach_files?per_page=100",
    )
    if not isinstance(existing, list):
        raise RuntimeError("Gitee attachment listing returned an invalid payload")
    by_name = {str(item.get("name")): item for item in existing if isinstance(item, dict)}
    for path in assets:
        old = by_name.get(path.name)
        if old:
            request_json(
                "DELETE",
                f"{base}/{release_id}/attach_files/{old['id']}",
                token=token,
                token_in_query=True,
                expected=(204,),
            )
        multipart_upload(
            f"{base}/{release_id}/attach_files",
            path,
            field="file",
            token=token,
            token_field=True,
        )


def sync_gitcode(release: dict[str, object], assets: list[Path]) -> None:
    token = os.environ["GITCODE_TOKEN"]
    owner = os.environ["GITCODE_OWNER"]
    repo = os.environ["GITCODE_REPO"]
    tag = str(release["tag_name"])
    base = f"https://api.gitcode.com/api/v5/repos/{owner}/{repo}/releases"
    try:
        request_json("GET", f"{base}/tags/{tag}", token=token)
    except RuntimeError as exc:
        if "HTTP 404" not in str(exc):
            raise
        request_json(
            "POST",
            base,
            token=token,
            fields={
                "tag_name": tag,
                "name": str(release.get("name") or tag),
                "body": str(release.get("body") or ""),
                "target_commitish": str(release.get("target_commitish") or "main"),
                "release_status": "latest",
            },
        )
    upload = request_json("GET", f"{base}/{tag}/upload_url", token=token)
    if not isinstance(upload, dict):
        raise RuntimeError("GitCode upload URL response was invalid")
    upload_url = str(upload.get("upload_url") or upload.get("url") or "")
    if not upload_url.startswith("https://"):
        raise RuntimeError("GitCode did not return a safe upload URL")
    for path in assets:
        multipart_upload(upload_url, path, field="file", token=token)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("provider", choices=("gitee", "gitcode"))
    args = parser.parse_args()
    release = github_release(os.environ["GITHUB_REPOSITORY"])
    assets = download_assets(release)
    if args.provider == "gitee":
        sync_gitee(release, assets)
    else:
        sync_gitcode(release, assets)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
