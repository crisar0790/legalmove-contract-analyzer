"""Offline tests for extraction inputs and structured output handling."""

from unittest.mock import Mock

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from src.agents.extraction_agent import ExtractionAgent
from src.exceptions import ModelResponseError
from src.models import ContractChangeOutput


@pytest.fixture
def report():
    return ContractChangeOutput(
        sections_changed=["Cláusula 3"],
        topics_touched=["Condiciones de pago"],
        summary_of_the_change="El importe cambia de USD 500 a USD 650.",
    )


def build_model(response, received):
    """Create a fake structured model that records its prompt."""

    def respond(prompt):
        received.extend(prompt.to_messages())
        return response

    model = Mock()
    model.with_structured_output.return_value = RunnableLambda(respond)
    return model


def test_passes_both_documents_and_map_to_structured_model(report):
    received = []
    response = {
        "raw": AIMessage(
            content=report.model_dump_json(),
            response_metadata={"status": "completed"},
        ),
        "parsed": report,
        "parsing_error": None,
    }
    model = build_model(response, received)
    agent = ExtractionAgent(model)

    result = agent.run(
        "Original: USD 500.",
        "Adenda: USD 650.",
        "La cláusula 1 de la adenda remite a la cláusula 3.",
    )

    assert result is report
    model.with_structured_output.assert_called_once_with(
        ContractChangeOutput,
        method="json_schema",
        strict=True,
        include_raw=True,
    )
    assert "contract amendment auditor" in received[0].content
    human_message = received[1].content
    assert "Original: USD 500." in human_message
    assert "Adenda: USD 650." in human_message
    assert "remite a la cláusula 3" in human_message


@pytest.mark.parametrize(
    ("parsed", "parsing_error"),
    [
        (None, ValueError("Invalid output")),
        (None, None),
        ({"sections_changed": []}, None),
    ],
)
def test_rejects_missing_or_invalid_parsed_report(parsed, parsing_error):
    response = {
        "raw": AIMessage(
            content="Candidate output",
            response_metadata={"status": "completed"},
        ),
        "parsed": parsed,
        "parsing_error": parsing_error,
    }
    agent = ExtractionAgent(build_model(response, []))

    with pytest.raises(ModelResponseError):
        agent.run("Original", "Adenda", "Mapa")


def test_rejects_incomplete_response_even_if_parsed_report_exists(report):
    response = {
        "raw": AIMessage(
            content=report.model_dump_json(),
            response_metadata={"status": "incomplete"},
        ),
        "parsed": report,
        "parsing_error": None,
    }
    agent = ExtractionAgent(build_model(response, []))

    with pytest.raises(ModelResponseError, match="did not complete"):
        agent.run("Original", "Adenda", "Mapa")


@pytest.mark.parametrize(
    "inputs",
    [
        ("", "Adenda", "Mapa"),
        ("Original", " ", "Mapa"),
        ("Original", "Adenda", ""),
    ],
)
def test_rejects_blank_inputs_without_calling_model(inputs):
    received = []
    agent = ExtractionAgent(build_model({}, received))

    with pytest.raises(ValueError, match="required"):
        agent.run(*inputs)

    assert received == []


def test_translates_direct_validation_error_without_retrying():
    calls = []

    def respond(_):
        calls.append(True)
        return ContractChangeOutput.model_validate({})

    model = Mock()
    model.with_structured_output.return_value = RunnableLambda(respond)
    agent = ExtractionAgent(model, max_retries=2)

    with pytest.raises(ModelResponseError, match="validation"):
        agent.run("Original", "Adenda", "Mapa")

    assert len(calls) == 1
