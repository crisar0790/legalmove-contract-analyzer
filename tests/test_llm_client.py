"""Offline tests for model clients and API failure handling."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
)

from src.exceptions import ModelAPIError, ModelResponseError
from src.llm_client import (
    build_agent_client,
    build_vision_client,
    call_with_retries,
    validate_completion_text,
)


def status_error(status_code):
    """Build a simulated API error without making HTTP requests."""
    response = Mock()
    response.status_code = status_code
    return APIStatusError(
        "Provider details must not appear in application errors.",
        response=response,
        body=None,
    )


@pytest.mark.parametrize("status_code", [408, 409, 429, 500, 503])
def test_retries_transient_status_errors(status_code):
    operation = Mock(side_effect=[status_error(status_code), "success"])
    wait = Mock()

    result = call_with_retries(operation, max_retries=2, wait=wait)

    assert result == "success"
    assert operation.call_count == 2
    wait.assert_called_once_with(1)


@pytest.mark.parametrize("status_code", [400, 401, 403, 404, 422])
def test_does_not_retry_permanent_status_errors(status_code):
    operation = Mock(side_effect=status_error(status_code))
    wait = Mock()

    with pytest.raises(ModelAPIError):
        call_with_retries(operation, max_retries=2, wait=wait)

    assert operation.call_count == 1
    wait.assert_not_called()


@pytest.mark.parametrize("error_type", [APIConnectionError, APITimeoutError])
def test_bounds_connection_and_timeout_retries(error_type):
    error = error_type(request=Mock())
    operation = Mock(side_effect=error)
    wait = Mock()

    with pytest.raises(ModelAPIError):
        call_with_retries(operation, max_retries=2, wait=wait)

    assert operation.call_count == 3
    assert wait.call_count == 2


def test_zero_retries_means_one_attempt():
    operation = Mock(side_effect=status_error(503))
    wait = Mock()

    with pytest.raises(ModelAPIError):
        call_with_retries(operation, max_retries=0, wait=wait)

    assert operation.call_count == 1
    wait.assert_not_called()


def test_does_not_retry_unrelated_errors():
    operation = Mock(side_effect=ValueError("Invalid local input"))
    wait = Mock()

    with pytest.raises(ValueError, match="Invalid local input"):
        call_with_retries(operation, max_retries=2, wait=wait)

    assert operation.call_count == 1
    wait.assert_not_called()


def test_does_not_expose_provider_error_details():
    operation = Mock(side_effect=status_error(401))

    with pytest.raises(ModelAPIError) as caught:
        call_with_retries(operation, max_retries=0)

    assert str(caught.value) == "Model API authentication failed."


def test_accepts_completed_text():
    assert (
        validate_completion_text("Contract text", finish_reason="stop")
        == "Contract text"
    )


@pytest.mark.parametrize(
    ("text", "finish_reason", "refusal"),
    [
        ("Partial text", "length", None),
        ("Blocked text", "content_filter", None),
        ("Text", None, None),
        ("", "stop", None),
        (" \n", "stop", None),
        (None, "stop", None),
        ("Text", "stop", "Request refused"),
    ],
)
def test_rejects_unusable_responses(text, finish_reason, refusal):
    with pytest.raises(ModelResponseError):
        validate_completion_text(
            text,
            finish_reason=finish_reason,
            refusal=refusal,
        )


def test_builds_clients_with_sdk_retries_disabled(monkeypatch):
    settings = SimpleNamespace(
        openai_api_key="test-key",
        request_timeout_seconds=30,
        agent_model="test-model",
    )
    openai_constructor = Mock()
    agent_constructor = Mock()
    monkeypatch.setattr("src.llm_client.OpenAI", openai_constructor)
    monkeypatch.setattr("src.llm_client.ChatOpenAI", agent_constructor)

    build_vision_client(settings)
    build_agent_client(settings, max_output_tokens=1024)

    openai_constructor.assert_called_once_with(
        api_key="test-key",
        timeout=30,
        max_retries=0,
    )
    agent_constructor.assert_called_once_with(
        model="test-model",
        api_key="test-key",
        timeout=30,
        max_retries=0,
        max_tokens=1024,
        use_responses_api=True,
        output_version="responses/v1",
        reasoning={"effort": "low"},
    )


def test_rejects_negative_retry_budget():
    with pytest.raises(ValueError, match="negative"):
        call_with_retries(Mock(), max_retries=-1)
