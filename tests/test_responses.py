from __future__ import annotations

from typing import Any

from gpt_image_cli.responses import decode_json_or_sse, extract_image_candidates


def test_extracts_base64_url_and_nested_data_uri() -> None:
    payload: dict[str, Any] = {
        "data": [
            {"b64_json": "YWJj"},
            {"url": "https://example.com/a.png"},
            {"result": {"image_base64": "data:image/png;base64,YWJj"}},
        ]
    }
    assert extract_image_candidates(payload) == [
        ("base64", "YWJj"),
        ("url", "https://example.com/a.png"),
        ("base64", "data:image/png;base64,YWJj"),
    ]


def test_decodes_sse_response() -> None:
    body = b'data: {"status":"working"}\n\ndata: {"data":[{"b64_json":"YWJj"}]}\n\ndata: [DONE]\n'
    decoded = decode_json_or_sse(body, "text/event-stream")
    assert extract_image_candidates(decoded) == [("base64", "YWJj")]
