from __future__ import annotations

import pytest

from gpt_image_cli.errors import GenerationError
from gpt_image_cli.models import GenerationOptions


def test_large_payload_uses_supported_size_without_response_format() -> None:
    payload = GenerationOptions(
        model="gpt-image-2",
        prompt="a landscape",
        size="landscape",
        quality="high",
    ).payload()
    assert payload == {
        "model": "gpt-image-2",
        "prompt": "a landscape",
        "n": 1,
        "size": "1536x1024",
        "quality": "high",
    }
    assert "response_format" not in payload


def test_image_count_is_validated_before_transport() -> None:
    with pytest.raises(GenerationError, match="between 1 and 10"):
        GenerationOptions(model="gpt-image-2", prompt="test", n=11).payload()
