"""Build model clients and handle API calls with bounded retries."""

from collections.abc import Callable
from time import sleep
from typing import TypeVar

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
)

from src.config import Settings
from src.exceptions import ModelAPIError, ModelResponseError

T = TypeVar("T")


def build_vision_client(settings: Settings) -> OpenAI:
    """Create an OpenAI client without making a request."""
    return OpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.request_timeout_seconds,
        max_retries=0,
    )


def build_agent_client(
    settings: Settings,
    *,
    max_output_tokens: int,
    reasoning_effort: str = "low",
) -> ChatOpenAI:
    """Create a Responses API model with a stage-specific output budget."""
    if max_output_tokens <= 0:
        raise ValueError("max_output_tokens must be positive.")

    return ChatOpenAI(
        model=settings.agent_model,
        api_key=settings.openai_api_key,
        timeout=settings.request_timeout_seconds,
        max_retries=0,
        max_tokens=max_output_tokens,
        use_responses_api=True,
        output_version="responses/v1",
        reasoning={"effort": reasoning_effort},
    )


def _is_transient(error: APIError) -> bool:
    """Identify failures eligible for a bounded retry."""
    if isinstance(error, APIConnectionError):
        return True
    if isinstance(error, APIStatusError):
        return error.status_code in {408, 409, 429} or error.status_code >= 500
    return False


def _error_message(error: APIError) -> str:
    """Describe a failure without exposing the provider response body."""
    if isinstance(error, APITimeoutError):
        return "Model request timed out."
    if isinstance(error, APIConnectionError):
        return "Unable to connect to the model API."
    if isinstance(error, APIStatusError):
        if error.status_code == 401:
            return "Model API authentication failed."
        if error.status_code == 403:
            return "Model API access was denied."
        if error.status_code == 429:
            return "Model API rate or quota limit reached."
        return f"Model API request failed with HTTP {error.status_code}."
    return "Model API request failed."


def call_with_retries(
    operation: Callable[[], T],
    *,
    max_retries: int,
    wait: Callable[[float], None] = sleep,
) -> T:
    """Run a model operation with at most max_retries + 1 attempts."""
    if max_retries < 0:
        raise ValueError("max_retries must not be negative.")

    for attempt in range(max_retries + 1):
        try:
            return operation()
        except APIError as error:
            if not _is_transient(error) or attempt == max_retries:
                raise ModelAPIError(_error_message(error)) from None
            wait(min(2**attempt, 8))

    raise RuntimeError("Unreachable retry state.")


def validate_completion_text(
    text: str | None,
    *,
    finish_reason: str | None,
    refusal: str | None = None,
) -> str:
    """Reject refusals, incomplete responses, and missing text."""
    if refusal is not None:
        raise ModelResponseError("The model refused the request.")
    if finish_reason == "length":
        raise ModelResponseError(
            "Vision response reached its output token limit. "
            "Review VISION_MAX_OUTPUT_TOKENS or use a shorter document."
        )
    if finish_reason != "stop":
        raise ModelResponseError("The model response did not finish normally.")
    if not isinstance(text, str) or not text.strip():
        raise ModelResponseError("The model returned no usable text.")
    return text


def validate_agent_message(message: AIMessage) -> AIMessage:
    """Reject incomplete, refused, or empty Responses API messages."""
    details = message.response_metadata.get("incomplete_details")
    if isinstance(details, dict) and details.get("reason") == "max_output_tokens":
        raise ModelResponseError(
            "Agent response reached its output token limit. "
            "Review the stage's CONTEXT_MAX_OUTPUT_TOKENS or "
            "EXTRACTION_MAX_OUTPUT_TOKENS, or use a shorter document."
        )

    if message.response_metadata.get("status") != "completed":
        raise ModelResponseError("The agent response did not complete.")

    if message.additional_kwargs.get("refusal") is not None:
        raise ModelResponseError("The agent refused the request.")

    if isinstance(message.content, list):
        for block in message.content:
            if isinstance(block, dict) and block.get("type") == "refusal":
                raise ModelResponseError("The agent refused the request.")

    if not message.text.strip():
        raise ModelResponseError("The agent returned no usable text.")

    return message
