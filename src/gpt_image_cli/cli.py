from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .client import ImageClient
from .config import ApiConfig, resolve_api_config
from .errors import CliError, GenerationError
from .image_io import save_images
from .models import (
    SIZE_ALIASES,
    SUPPORTED_BACKGROUNDS,
    SUPPORTED_QUALITIES,
    SUPPORTED_SIZES,
    GenerationOptions,
)
from .proxy import ProxyConfig, resolve_proxy_config
from .updater import check_for_updates, install_update

DEFAULT_CC_SWITCH_DB = Path.home() / ".cc-switch" / "cc-switch.db"
DEFAULT_MODEL = os.getenv("GPT_IMAGE_MODEL", "gpt-image-2")


def _add_connection_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--api-base",
        help="OpenAI-compatible API base. The key must come from GPT_IMAGE_API_KEY.",
    )
    parser.add_argument(
        "--cc-switch-db",
        type=Path,
        default=DEFAULT_CC_SWITCH_DB,
        help="CC-Switch database used when direct environment configuration is absent.",
    )
    parser.add_argument(
        "--allow-http",
        action="store_true",
        help=(
            "Allow a non-HTTPS remote API base intentionally (localhost is allowed automatically)."
        ),
    )
    parser.add_argument(
        "--proxy",
        help=(
            "Explicit HTTP(S) proxy URL. By default the CLI uses proxy environment "
            "variables or the enabled Windows system proxy."
        ),
    )
    parser.add_argument(
        "--no-proxy",
        action="store_true",
        help="Ignore HTTP_PROXY/HTTPS_PROXY and system proxy environment variables.",
    )
    parser.add_argument(
        "--connect-timeout", type=float, default=30, help="Connect timeout in seconds."
    )
    parser.add_argument(
        "--connect-retries",
        type=int,
        default=2,
        help="Retries for connection setup failures only; submitted requests are never retried.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gpt-image",
        description="Generate and validate GPT-Image output through an OpenAI-compatible relay.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser(
        "doctor", help="Resolve credentials and check the relay model list."
    )
    _add_connection_arguments(doctor)
    doctor.add_argument("--model", default=DEFAULT_MODEL)
    doctor.add_argument("--json", action="store_true", help="Emit machine-readable JSON only.")

    generate = subparsers.add_parser("generate", help="Generate one or more images.")
    _add_connection_arguments(generate)
    generate.add_argument("prompt", nargs="?", help="Text-to-image prompt.")
    generate.add_argument("--prompt-file", type=Path, help="UTF-8 file containing the prompt.")
    generate.add_argument("-o", "--output", type=Path, required=True, help="Output image path.")
    generate.add_argument("--model", default=DEFAULT_MODEL)
    generate.add_argument(
        "--size",
        default="auto",
        choices=(*SUPPORTED_SIZES, *SIZE_ALIASES),
        help="Image size or a square/landscape/portrait alias.",
    )
    generate.add_argument("--quality", choices=SUPPORTED_QUALITIES, default="auto")
    generate.add_argument("--background", choices=SUPPORTED_BACKGROUNDS, default="auto")
    generate.add_argument("-n", type=int, default=1, help="Number of images, from 1 to 10.")
    generate.add_argument(
        "--timeout",
        type=float,
        default=1800,
        help="Read timeout in seconds. Large images can take several minutes.",
    )
    generate.add_argument("--download-timeout", type=float, default=300)
    generate.add_argument("--max-response-mb", type=int, default=150)
    generate.add_argument("--overwrite", action="store_true")
    generate.add_argument(
        "--fit-output-size",
        action="store_true",
        help=(
            "If the API returns a different canvas, center-crop and resize it to "
            "the explicitly requested --size."
        ),
    )
    generate.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve configuration and validate parameters without a paid API request.",
    )
    generate.add_argument("--no-progress", action="store_true", help="Disable waiting heartbeats.")
    generate.add_argument("--json", action="store_true", help="Emit machine-readable JSON only.")

    update = subparsers.add_parser(
        "update",
        help="Check public Release mirrors and install a verified newer wheel.",
    )
    update.add_argument(
        "--check",
        action="store_true",
        help="Only check for a newer version; do not change the installation.",
    )
    update.add_argument(
        "--source",
        choices=("auto", "github", "gitee", "gitcode"),
        default="auto",
        help="Release source to use. Auto checks all configured public mirrors.",
    )
    update.add_argument(
        "--prerelease",
        action="store_true",
        help="Allow a prerelease version to be selected.",
    )
    update.add_argument("--proxy", help="Explicit HTTP(S) proxy URL for update traffic.")
    update.add_argument(
        "--no-proxy",
        action="store_true",
        help="Ignore proxy environment variables and Windows system proxy settings.",
    )
    update.add_argument("--timeout", type=float, default=30, help="Network timeout in seconds.")
    update.add_argument("--json", action="store_true", help="Emit machine-readable JSON only.")
    return parser


def _emit(payload: dict[str, Any], *, json_only: bool) -> None:
    if json_only:
        print(json.dumps(payload, ensure_ascii=False))
        return
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _read_prompt(args: argparse.Namespace) -> str:
    if args.prompt and args.prompt_file:
        raise GenerationError("Use either a prompt argument or --prompt-file, not both.")
    if args.prompt_file:
        try:
            prompt = args.prompt_file.read_text(encoding="utf-8")
        except OSError as exc:
            raise GenerationError(f"Cannot read prompt file: {exc}") from exc
    else:
        prompt = args.prompt or ""
    prompt = prompt.strip()
    if not prompt:
        raise GenerationError("Prompt cannot be empty.")
    return prompt


def _client(args: argparse.Namespace) -> tuple[ApiConfig, ImageClient, ProxyConfig]:
    config = resolve_api_config(
        api_base=args.api_base,
        cc_switch_db=args.cc_switch_db,
        allow_http=args.allow_http,
    )
    proxy = resolve_proxy_config(
        config.images_endpoint,
        explicit_proxy=args.proxy,
        no_proxy=args.no_proxy,
    )
    client = ImageClient(
        config,
        read_timeout=getattr(args, "timeout", 1800),
        connect_timeout=args.connect_timeout,
        download_timeout=getattr(args, "download_timeout", 300),
        max_response_mb=getattr(args, "max_response_mb", 150),
        trust_env=proxy.trust_env,
        proxy=proxy.url,
        connect_retries=args.connect_retries,
    )
    return config, client, proxy


def _doctor(args: argparse.Namespace) -> int:
    config, client, proxy = _client(args)
    models = client.list_models()
    image_models = [
        model for model in models if "image" in model.lower() or "dall" in model.lower()
    ]
    model_available = args.model in models
    payload = {
        "success": model_available,
        "provider": config.provider,
        "source": config.source,
        "api_base": config.api_base,
        "endpoint": config.images_endpoint,
        "requested_model": args.model,
        "model_available": model_available,
        "image_models": image_models,
        "proxy_mode": proxy.mode,
        "proxy": proxy.display_url,
    }
    _emit(payload, json_only=args.json)
    return 0 if model_available else 4


def _generate(args: argparse.Namespace) -> int:
    prompt = _read_prompt(args)
    config, client, proxy = _client(args)
    options = GenerationOptions(
        model=args.model,
        prompt=prompt,
        n=args.n,
        size=args.size,
        quality=args.quality,
        background=args.background,
    )
    wire_payload = options.payload()
    base_summary = {
        "provider": config.provider,
        "source": config.source,
        "endpoint": config.images_endpoint,
        "model": args.model,
        "prompt_characters": len(prompt),
        "output": str(args.output.expanduser().resolve()),
        "parameters": {key: value for key, value in wire_payload.items() if key != "prompt"},
        "response_format_omitted": True,
        "proxy_mode": proxy.mode,
        "proxy": proxy.display_url,
    }
    if args.dry_run:
        _emit({**base_summary, "dry_run": True, "success": True}, json_only=args.json)
        return 0

    if not args.json:
        print(
            f"Submitting {args.model} request to {config.provider}; "
            f"size={options.normalized_size()}, timeout={args.timeout:g}s",
            file=sys.stderr,
            flush=True,
        )
    result = client.generate(options, show_progress=not args.no_progress and not args.json)
    expected_size = None
    if options.normalized_size() != "auto":
        expected_size = tuple(
            int(part) for part in options.normalized_size().split("x", maxsplit=1)
        )
    saved = save_images(
        args.output,
        result.images,
        overwrite=args.overwrite,
        expected_size=expected_size,
        fit_output_size=args.fit_output_size,
    )
    payload = {
        **base_summary,
        "success": True,
        "elapsed_seconds": round(result.elapsed_seconds, 2),
        "request_id": result.request_id,
        "response_bytes": result.response_bytes,
        "images": [
            {
                "path": str(item.path),
                "width": item.width,
                "height": item.height,
                "format": item.format,
                "bytes": item.bytes,
                "source": item.source,
            }
            for item in saved
        ],
    }
    _emit(payload, json_only=args.json)
    return 0


def _update(args: argparse.Namespace) -> int:
    result = check_for_updates(
        source_name=args.source,
        allow_prerelease=args.prerelease,
        timeout=args.timeout,
        explicit_proxy=args.proxy,
        no_proxy=args.no_proxy,
    )
    if args.check or not result.update_available:
        payload = {"success": True, "updated": False, **result.public_summary()}
        _emit(payload, json_only=args.json)
        return 0
    if not args.json:
        candidate = result.candidate
        assert candidate is not None
        print(
            f"Installing verified {candidate.version} wheel from {candidate.source}...",
            file=sys.stderr,
            flush=True,
        )
    assert result.candidate is not None
    payload = install_update(
        result.candidate,
        timeout=args.timeout,
        explicit_proxy=args.proxy,
        no_proxy=args.no_proxy,
    )
    payload["checked_sources"] = list(result.checked_sources)
    payload["source_errors"] = result.source_errors
    _emit(payload, json_only=args.json)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            return _doctor(args)
        if args.command == "generate":
            return _generate(args)
        if args.command == "update":
            return _update(args)
        parser.error("Unknown command.")
    except CliError as exc:
        print(f"{exc.label}: {exc}", file=sys.stderr)
        if exc.possibly_billed:
            print(
                "The request may already have been billed. It was not retried automatically.",
                file=sys.stderr,
            )
        return exc.exit_code
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
