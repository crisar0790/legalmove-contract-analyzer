"""Offline tests for multimodal document transcription."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PIL import Image

from src.exceptions import ImageValidationError, ModelResponseError
from src.image_parser import parse_contract_document, parse_contract_image


@pytest.fixture
def settings():
    return SimpleNamespace(
        max_image_size_bytes=10_000,
        vision_model="gpt-4o",
        vision_max_output_tokens=4096,
        max_retries=0,
    )


@pytest.fixture
def image_path(tmp_path):
    path = tmp_path / "contract.png"
    Image.new("RGB", (40, 40), "white").save(path)
    return path


@pytest.fixture
def client():
    usage = Mock()
    usage.model_dump.return_value = {
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "total_tokens": 150,
    }
    message = SimpleNamespace(
        content="Cláusula 3. El cliente abonará USD 500.",
        refusal=None,
    )
    response = SimpleNamespace(
        id="test-response",
        model="test-returned-model",
        choices=[SimpleNamespace(message=message, finish_reason="stop")],
        usage=usage,
    )
    api_client = Mock()
    api_client.chat.completions.create.return_value = response
    return api_client


def test_returns_text_and_real_response_metadata(image_path, settings, client):
    result = parse_contract_document(image_path, settings=settings, client=client)

    assert result.text == "Cláusula 3. El cliente abonará USD 500."
    assert result.model == "test-returned-model"
    assert result.response_id == "test-response"
    assert result.usage["total_tokens"] == 150
    assert result.latency_seconds >= 0
    client.chat.completions.create.assert_called_once()


def test_sends_base64_image_and_specialized_prompt(image_path, settings, client):
    parse_contract_document(image_path, settings=settings, client=client)

    arguments = client.chat.completions.create.call_args.kwargs
    assert arguments["model"] == settings.vision_model
    assert arguments["max_completion_tokens"] == 4096
    assert arguments["messages"][0]["role"] == "system"
    assert "Do not summarize" in arguments["messages"][0]["content"]

    image_block = arguments["messages"][1]["content"][1]
    assert image_block["image_url"]["detail"] == "high"
    assert image_block["image_url"]["url"].startswith("data:image/png;base64,")


def test_public_parser_returns_string(image_path, settings, client):
    result = parse_contract_image(image_path, settings=settings, client=client)

    assert isinstance(result, str)
    assert "USD 500" in result


def test_invalid_image_does_not_call_api(tmp_path, settings, client):
    with pytest.raises(ImageValidationError):
        parse_contract_document(
            tmp_path / "missing.png", settings=settings, client=client
        )

    client.chat.completions.create.assert_not_called()


@pytest.mark.parametrize(
    ("content", "finish_reason", "refusal"),
    [
        ("Partial text", "length", None),
        ("Text", "content_filter", None),
        ("", "stop", None),
        (None, "stop", None),
        ("Text", "stop", "Refused"),
    ],
)
def test_rejects_unusable_response(
    image_path, settings, client, content, finish_reason, refusal
):
    response = client.chat.completions.create.return_value
    response.choices[0].message.content = content
    response.choices[0].message.refusal = refusal
    response.choices[0].finish_reason = finish_reason

    with pytest.raises(ModelResponseError):
        parse_contract_document(image_path, settings=settings, client=client)


def test_rejects_missing_choices(image_path, settings, client):
    client.chat.completions.create.return_value.choices = []

    with pytest.raises(ModelResponseError, match="no completion choices"):
        parse_contract_document(image_path, settings=settings, client=client)


def test_preserves_missing_usage_as_unknown(image_path, settings, client):
    client.chat.completions.create.return_value.usage = None

    result = parse_contract_document(image_path, settings=settings, client=client)

    assert result.usage is None
