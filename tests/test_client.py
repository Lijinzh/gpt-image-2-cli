from __future__ import annotations

import base64
import io
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest
from PIL import Image

from gpt_image_cli.client import ImageClient
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
