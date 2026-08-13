from __future__ import annotations

import argparse
import json
import os
import queue
import signal
import sys
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from types import FrameType
from typing import Any, TypeVar

from . import __version__
from .client import GenerationRequestState, ImageClient
from .config import ApiConfig, resolve_api_config
from .errors import CliError, GenerationError, GenerationInterrupted
from .image_io import save_images
from .models import (
    SIZE_ALIASES,
    SUPPORTED_BACKGROUNDS,
    SUPPORTED_QUALITIES,
    SUPPORTED_SIZES,
    GenerationOptions,
)
from .proxy import ProxyConfig, resolve_proxy_config
from .updater import automatic_update_notice, check_for_updates, install_update

DEFAULT_CC_SWITCH_DB = Path.home() / ".cc-switch" / "cc-switch.db"
DEFAULT_MODEL = os.getenv("GPT_IMAGE_MODEL", "gpt-image-2")
ResultT = TypeVar("ResultT")


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
    generate.add_argument(
        "--jsonl-progress",
        action="store_true",
        help="Emit redacted JSON Lines progress events to stderr.",
    )
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


def _emit_progress(enabled: bool, event: str, **details: Any) -> None:
    if not enabled:
        return
    print(
        json.dumps({"event": event, **details}, ensure_ascii=False, separators=(",", ":")),
        file=sys.stderr,
        flush=True,
    )


@contextmanager
def _generation_interrupts(state: GenerationRequestState) -> Iterator[None]:
    previous: dict[int, Any] = {}

    def interrupt(signum: int, _frame: FrameType | None) -> None:
        name = signal.Signals(signum).name
        raise GenerationInterrupted(
            name,
            request_submitted=state.request_submitted,
            exit_code=128 + signum,
        )

    for name in ("SIGTERM", "SIGHUP", "SIGBREAK"):
        signum = getattr(signal, name, None)
        if signum is None:
            continue
        previous[signum] = signal.getsignal(signum)
        signal.signal(signum, interrupt)
    try:
        yield
    except KeyboardInterrupt as exc:
        raise GenerationInterrupted(
            "KeyboardInterrupt",
            request_submitted=state.request_submitted,
        ) from exc
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def _run_interruptibly(action: Callable[[], ResultT]) -> ResultT:
    """Keep the main thread available for signals during blocking network I/O."""

    results: queue.Queue[tuple[bool, ResultT | BaseException]] = queue.Queue(maxsize=1)

    def run() -> None:
        try:
            results.put((True, action()))
        except BaseException as exc:
            results.put((False, exc))

    thread = threading.Thread(target=run, name="gpt-image-request", daemon=True)
    thread.start()
    while True:
        try:
            succeeded, value = results.get(timeout=0.1)
            break
        except queue.Empty:
            continue
    if not succeeded:
        assert isinstance(value, BaseException)
        raise value
    return value


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

    request_state = GenerationRequestState()
    _emit_progress(
        args.jsonl_progress,
        "request_started",
        model=args.model,
        size=options.normalized_size(),
        image_count=args.n,
        request_submitted=False,
        possibly_billed=False,
    )

    def progress(event: str, details: dict[str, Any]) -> None:
        submitted = details.pop("request_submitted", request_state.request_submitted)
        possibly_billed = details.pop("possibly_billed", submitted)
        automatic_retry = details.pop("automatic_retry", False)
        _emit_progress(
            args.jsonl_progress,
            event,
            request_submitted=submitted,
            possibly_billed=possibly_billed,
            automatic_retry=automatic_retry,
            **details,
        )

    if not args.json:
        print(
            f"Submitting {args.model} request to {config.provider}; "
            f"size={options.normalized_size()}, timeout={args.timeout:g}s",
            file=sys.stderr,
            flush=True,
        )
    try:
        with _generation_interrupts(request_state):
            result = _run_interruptibly(
                lambda: client.generate(
                    options,
                    show_progress=not args.no_progress and not args.json,
                    progress_callback=progress if args.jsonl_progress else None,
                    request_state=request_state,
                    emit_progress_heartbeats=not args.no_progress,
                )
            )
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
    except GenerationInterrupted as exc:
        _emit_progress(
            args.jsonl_progress,
            "interrupted",
            signal=exc.signal_name,
            request_submitted=exc.request_submitted,
            possibly_billed=exc.possibly_billed,
            automatic_retry=exc.automatic_retry,
        )
        raise
    except CliError as exc:
        if request_state.request_submitted:
            exc.possibly_billed = True
        _emit_progress(
            args.jsonl_progress,
            "failed",
            error_type=exc.label.lower().replace(" ", "_"),
            request_submitted=request_state.request_submitted,
            possibly_billed=exc.possibly_billed,
            automatic_retry=False,
        )
        raise
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
    _emit_progress(
        args.jsonl_progress,
        "completed",
        elapsed_seconds=round(result.elapsed_seconds, 2),
        image_count=len(saved),
        request_submitted=request_state.request_submitted,
        possibly_billed=False,
        automatic_retry=False,
    )
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
            f"Downloading verified {candidate.version} wheel from {candidate.source}; "
            "installation will start after this command exits...",
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


def _emit_automatic_update_notice(args: argparse.Namespace) -> None:
    if getattr(args, "json", False) or not sys.stderr.isatty():
        return
    notice = automatic_update_notice()
    if notice:
        print(notice, file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            exit_code = _doctor(args)
            _emit_automatic_update_notice(args)
            return exit_code
        if args.command == "generate":
            exit_code = _generate(args)
            _emit_automatic_update_notice(args)
            return exit_code
        if args.command == "update":
            return _update(args)
        parser.error("Unknown command.")
    except CliError as exc:
        print(f"{exc.label}: {exc}", file=sys.stderr)
        if isinstance(exc, GenerationInterrupted):
            print(
                "Interruption state: "
                f"request_submitted={str(exc.request_submitted).lower()} "
                f"possibly_billed={str(exc.possibly_billed).lower()} "
                f"automatic_retry={str(exc.automatic_retry).lower()}",
                file=sys.stderr,
            )
        if exc.possibly_billed:
            print(
                "The request may already have been billed. It was not retried automatically.",
                file=sys.stderr,
            )
        return exc.exit_code
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
