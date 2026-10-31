"""Tests for the public contract analysis schema."""

import json

import pytest
from pydantic import ValidationError

from src.models import ContractChangeOutput


@pytest.fixture
def valid_payload():
    """Provide an illustrative valid report."""
    return {
        "sections_changed": ["Cláusula 3"],
        "topics_touched": ["Condiciones de pago"],
        "summary_of_the_change": (
            "La cláusula 3 modifica el importe mensual de USD 500 a USD 650 "
            "y el vencimiento del día 5 al día 10."
        ),
    }


def test_accepts_valid_output(valid_payload):
    result = ContractChangeOutput.model_validate(valid_payload)

    assert result.model_dump() == valid_payload


def test_accepts_no_changes():
    result = ContractChangeOutput(
        sections_changed=[],
        topics_touched=[],
        summary_of_the_change="No se identificaron cambios.",
    )

    assert result.sections_changed == []
    assert result.topics_touched == []


@pytest.mark.parametrize(
    "field",
    ["sections_changed", "topics_touched", "summary_of_the_change"],
)
def test_rejects_missing_fields(valid_payload, field):
    del valid_payload[field]

    with pytest.raises(ValidationError):
        ContractChangeOutput.model_validate(valid_payload)


def test_rejects_additional_fields(valid_payload):
    valid_payload["trace_id"] = "example-trace"

    with pytest.raises(ValidationError):
        ContractChangeOutput.model_validate(valid_payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sections_changed", "Cláusula 3"),
        ("sections_changed", ("Cláusula 3",)),
        ("sections_changed", [3]),
        ("sections_changed", None),
        ("topics_touched", "Pago"),
        ("topics_touched", [True]),
        ("topics_touched", None),
        ("summary_of_the_change", 123),
        ("summary_of_the_change", ["Cambio"]),
        ("summary_of_the_change", None),
    ],
)
def test_rejects_incorrect_types(valid_payload, field, value):
    valid_payload[field] = value

    with pytest.raises(ValidationError):
        ContractChangeOutput.model_validate(valid_payload)


@pytest.mark.parametrize("field", ["sections_changed", "topics_touched"])
@pytest.mark.parametrize("blank", ["", " ", "\n\t"])
def test_rejects_blank_list_items(valid_payload, field, blank):
    valid_payload[field] = ["Valid item", blank]

    with pytest.raises(ValidationError):
        ContractChangeOutput.model_validate(valid_payload)


@pytest.mark.parametrize("summary", ["", " ", "\n\t"])
def test_rejects_blank_summary(valid_payload, summary):
    valid_payload["summary_of_the_change"] = summary

    with pytest.raises(ValidationError):
        ContractChangeOutput.model_validate(valid_payload)


def test_preserves_valid_text_without_normalization(valid_payload):
    valid_payload["sections_changed"] = [" Cláusula 3 "]

    result = ContractChangeOutput.model_validate(valid_payload)

    assert result.sections_changed == [" Cláusula 3 "]


def test_serializes_exactly_the_three_public_fields(valid_payload):
    result = ContractChangeOutput.model_validate(valid_payload)

    serialized = json.loads(result.model_dump_json())

    assert serialized == valid_payload
    assert set(serialized) == {
        "sections_changed",
        "topics_touched",
        "summary_of_the_change",
    }


def test_validates_json_input(valid_payload):
    result = ContractChangeOutput.model_validate_json(
        json.dumps(valid_payload, ensure_ascii=False)
    )

    assert result.model_dump() == valid_payload


def test_rejects_malformed_json():
    with pytest.raises(ValidationError):
        ContractChangeOutput.model_validate_json('{"sections_changed":')
