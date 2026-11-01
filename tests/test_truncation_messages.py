"""Check actionable diagnostics for output token limits."""

import pytest
from langchain_core.messages import AIMessage

from src.exceptions import ModelResponseError
from src.llm_client import (
    validate_agent_message,
    validate_completion_text,
)


def test_vision_token_limit_rejects_partial_text():
    with pytest.raises(ModelResponseError, match="VISION_MAX_OUTPUT_TOKENS"):
        validate_completion_text(
            "Partial contract transcription",
            finish_reason="length",
        )


def test_agent_token_limit_rejects_partial_text():
    message = AIMessage(
        content="Partial analysis",
        response_metadata={
            "status": "incomplete",
            "incomplete_details": {"reason": "max_output_tokens"},
        },
    )

    with pytest.raises(ModelResponseError, match="output token limit"):
        validate_agent_message(message)


def test_unknown_incomplete_reason_keeps_generic_diagnostic():
    message = AIMessage(
        content="Partial analysis",
        response_metadata={"status": "incomplete"},
    )

    with pytest.raises(ModelResponseError, match="did not complete"):
        validate_agent_message(message)
