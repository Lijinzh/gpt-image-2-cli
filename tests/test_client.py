from __future__ import annotations

import base64
import io
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest
from PIL import Image

from gpt_image_cli.client import GenerationRequestState, ImageClient
from gpt_image_cli.config import ApiConfig
from gpt_image_cli.errors import GenerationError
from gpt_image_cli.models import GenerationOptions


def make_png(width: int = 16, height: int = 8) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (width, height), color=(12, 34, 56)).save(output, format="PNG")
    return output.getvalue()


def test_client_rejects_non_positive_limits() -> None:
    config = ApiConfig(
        provider="test",
        api_base="https://relay.example/v1",
        api_key="test-key",
        source="test",
    )
    with pytest.raises(GenerationError, match="greater than zero"):
        ImageClient(config, max_response_mb=0)
    with pytest.raises(GenerationError, match="cannot be negative"):
        ImageClient(config, connect_retries=-1)


def test_client_handles_openai_compatible_base64_response() -> None:
    png = make_png()
    state: dict[str, Any] = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args: Any) -> None:
            return

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers["Content-Length"])
            state["payload"] = json.loads(self.rfile.read(length))
            body = json.dumps(
                {"data": [{"b64_json": base64.b64encode(png).decode("ascii")}]}
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("X-Request-Id", "req-test")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        config = ApiConfig(
            provider="test",
            api_base=f"http://127.0.0.1:{server.server_port}/v1",
            api_key="test-key",
            source="test",
        )
        result = ImageClient(config, trust_env=False).generate(
            GenerationOptions(
                model="gpt-image-2",
                prompt="test",
                size="1536x1024",
                quality="high",
            ),
            show_progress=False,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert result.request_id == "req-test"
    assert result.images[0].data == png
    assert state["payload"]["size"] == "1536x1024"
    assert "response_format" not in state["payload"]


def test_client_accepts_an_explicit_proxy_configuration() -> None:
    config = ApiConfig(
        provider="test",
        api_base="https://relay.example/v1",
        api_key="test-key",
        source="test",
    )
    client = ImageClient(
        config,
        trust_env=False,
        proxy="http://127.0.0.1:7890",
    )
    assert client.proxy == "http://127.0.0.1:7890"
    assert client.trust_env is False


def test_client_rejects_error_object_wrapped_in_http_200() -> None:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args: Any) -> None:
            return

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers["Content-Length"])
            self.rfile.read(length)
            body = json.dumps(
                {"error": {"message": "request was blocked", "code": "blocked"}}
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        config = ApiConfig(
            provider="test",
            api_base=f"http://127.0.0.1:{server.server_port}/v1",
            api_key="test-key",
            source="test",
        )
        with pytest.raises(GenerationError, match="request was blocked"):
            ImageClient(config, trust_env=False).generate(
                GenerationOptions(model="gpt-image-2", prompt="test"),
                show_progress=False,
            )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_slow_request_emits_submitted_and_heartbeat_events_once() -> None:
    png = make_png()
    events: list[tuple[str, dict[str, Any]]] = []
    state = {"posts": 0}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args: Any) -> None:
            return

        def do_POST(self) -> None:  # noqa: N802
            state["posts"] += 1
            length = int(self.headers["Content-Length"])
            self.rfile.read(length)
            time.sleep(0.12)
            body = json.dumps(
                {"data": [{"b64_json": base64.b64encode(png).decode("ascii")}]}
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        config = ApiConfig(
            provider="test",
            api_base=f"http://127.0.0.1:{server.server_port}/v1",
            api_key="must-never-appear",
            source="test",
        )
        request_state = GenerationRequestState()
        result = ImageClient(config, trust_env=False).generate(
            GenerationOptions(model="gpt-image-2", prompt="slow test"),
            show_progress=False,
            progress_callback=lambda event, details: events.append((event, details)),
            request_state=request_state,
            progress_interval=0.03,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    names = [event for event, _details in events]
    assert result.images[0].data == png
    assert request_state.request_submitted is True
    assert state["posts"] == 1
    assert names.count("request_submitted") == 1
    assert "heartbeat" in names
    assert names.index("request_submitted") < names.index("heartbeat")
    assert "must-never-appear" not in json.dumps(events)


def test_submitted_connect_error_is_not_retried(monkeypatch: object) -> None:
    calls = 0
    events: list[str] = []

    class FakeClient:
        def __init__(self, **_kwargs: Any) -> None:
            return

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *_args: Any) -> None:
            return

        def stream(self, _method: str, url: str, **kwargs: Any) -> None:
            nonlocal calls
            calls += 1
            kwargs["extensions"]["trace"]("http11.send_request_body.complete", {})
            request = httpx.Request("POST", url)
            raise httpx.ConnectError("connection lost", request=request)

    import httpx

    monkeypatch.setattr("gpt_image_cli.client.httpx.Client", FakeClient)
    config = ApiConfig(
        provider="test",
        api_base="https://relay.example/v1",
        api_key="test-key",
        source="test",
    )
    request_state = GenerationRequestState()
    with pytest.raises(GenerationError, match="after the image request was submitted") as error:
        ImageClient(config, trust_env=False, connect_retries=3).generate(
            GenerationOptions(model="gpt-image-2", prompt="test"),
            show_progress=False,
            progress_callback=lambda event, _details: events.append(event),
            request_state=request_state,
        )

    assert calls == 1
    assert events == ["request_submitted"]
    assert request_state.request_submitted is True
    assert error.value.possibly_billed is True


def test_connection_setup_retry_is_marked_safe_and_automatic(monkeypatch: object) -> None:
    png = make_png()
    body = json.dumps(
        {"data": [{"b64_json": base64.b64encode(png).decode("ascii")}]}
    ).encode()
    calls = 0
    events: list[tuple[str, dict[str, Any]]] = []

    class FakeStream:
        def __enter__(self) -> httpx.Response:
            return httpx.Response(
                200,
                headers={"Content-Type": "application/json"},
                content=body,
            )

        def __exit__(self, *_args: Any) -> None:
            return

    class FakeClient:
        def __init__(self, **_kwargs: Any) -> None:
            return

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *_args: Any) -> None:
            return

        def stream(self, _method: str, url: str, **kwargs: Any) -> FakeStream:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise httpx.ConnectError("not connected", request=httpx.Request("POST", url))
            kwargs["extensions"]["trace"]("http11.send_request_body.complete", {})
            return FakeStream()

    import httpx

    monkeypatch.setattr("gpt_image_cli.client.httpx.Client", FakeClient)
    config = ApiConfig(
        provider="test",
        api_base="https://relay.example/v1",
        api_key="test-key",
        source="test",
    )
    result = ImageClient(config, trust_env=False, connect_retries=2).generate(
        GenerationOptions(model="gpt-image-2", prompt="test"),
        show_progress=False,
        progress_callback=lambda event, details: events.append((event, details)),
    )

    assert result.images[0].data == png
    assert calls == 2
    assert events[0] == (
        "connection_retry",
        {
            "attempt": 1,
            "maximum_retries": 2,
            "request_submitted": False,
            "possibly_billed": False,
            "automatic_retry": True,
        },
    )
    assert events[1][0] == "request_submitted"
