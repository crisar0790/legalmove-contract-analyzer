"""Regression tests for the extraction output acceptance boundary."""

import json

import pytest
from langchain_core.messages import AIMessage
from pydantic import ValidationError

from src.agents.extraction_agent import validate_extraction_response
from src.exceptions import ModelResponseError
from src.models import ContractChangeOutput


def completed_message(text="Candidate output"):
    """Create a completed Responses API message for offline tests."""
    return AIMessage(
        content=text,
        response_metadata={"status": "completed"},
    )


@pytest.mark.parametrize(
    "candidate",
    [
        '{"sections_changed":',
        json.dumps({}),
        json.dumps(
            {
                "sections_changed": [],
                "topics_touched": [],
                "summary_of_the_change": " ",
            }
        ),
        json.dumps(
            {
                "sections_changed": ["Cláusula 3"],
                "topics_touched": [],
                "summary_of_the_change": "Cambio de importe.",
                "extra_field": "Not allowed",
            }
        ),
        json.dumps(
            {
                "sections_changed": [3],
                "topics_touched": [],
                "summary_of_the_change": "Cambio de importe.",
            }
        ),
    ],
)
def test_rejects_actual_pydantic_parsing_failures(candidate):
    with pytest.raises(ValidationError) as caught:
        ContractChangeOutput.model_validate_json(candidate)

    response = {
        "raw": completed_message(candidate),
        "parsed": None,
        "parsing_error": caught.value,
    }

    with pytest.raises(ModelResponseError, match="validation"):
        validate_extraction_response(response)


@pytest.mark.parametrize(
    "response",
    [
        None,
        [],
        {},
        {"raw": completed_message()},
        {"raw": None, "parsed": None, "parsing_error": None},
    ],
)
def test_rejects_invalid_response_envelopes(response):
    with pytest.raises(ModelResponseError):
        validate_extraction_response(response)


def test_accepts_validated_no_change_report():
    report = ContractChangeOutput(
        sections_changed=[],
        topics_touched=[],
        summary_of_the_change="No se identificaron cambios.",
    )

    result = validate_extraction_response(
        {
            "raw": completed_message(report.model_dump_json()),
            "parsed": report,
            "parsing_error": None,
        }
    )

    assert result is report


@pytest.mark.parametrize("status", ["incomplete", "failed", None])
def test_rejects_unsuccessful_status_even_with_valid_report(status):
    report = ContractChangeOutput(
        sections_changed=[],
        topics_touched=[],
        summary_of_the_change="No se identificaron cambios.",
    )

    with pytest.raises(ModelResponseError):
        validate_extraction_response(
            {
                "raw": AIMessage(
                    content=report.model_dump_json(),
                    response_metadata={"status": status},
                ),
                "parsed": report,
                "parsing_error": None,
            }
        )


def test_rejects_refusal_even_with_valid_report():
    report = ContractChangeOutput(
        sections_changed=[],
        topics_touched=[],
        summary_of_the_change="No se identificaron cambios.",
    )

    with pytest.raises(ModelResponseError, match="refused"):
        validate_extraction_response(
            {
                "raw": AIMessage(
                    content=report.model_dump_json(),
                    response_metadata={"status": "completed"},
                    additional_kwargs={"refusal": "Refused"},
                ),
                "parsed": report,
                "parsing_error": None,
            }
        )
