"""Offline tests for contextualization agent wiring and response handling."""

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from src.agents.contextualization_agent import ContextualizationAgent
from src.exceptions import ModelResponseError


def test_receives_both_documents_and_specialized_system_prompt():
    received = []

    def respond(prompt):
        received.extend(prompt.to_messages())
        return AIMessage(
            content="Mapa contextual de prueba.",
            response_metadata={"status": "completed"},
        )

    agent = ContextualizationAgent(RunnableLambda(respond))

    result = agent.run(
        "Original: cláusula 3, honorarios.",
        "Adenda: cláusula 1 remite a la cláusula 3.",
    )

    assert result == "Mapa contextual de prueba."
    assert received[0].type == "system"
    assert "senior contract contextualization analyst" in received[0].content
    assert "Original: cláusula 3, honorarios." in received[1].content
    assert "Adenda: cláusula 1 remite a la cláusula 3." in received[1].content
    assert "<original_contract>" in received[1].content
    assert "<amendment>" in received[1].content


@pytest.mark.parametrize(
    ("original", "amendment"),
    [("", "Adenda"), ("Original", " "), ("\n", "")],
)
def test_rejects_blank_inputs_without_invoking_model(original, amendment):
    calls = []

    def respond(prompt):
        calls.append(prompt)
        return AIMessage(content="Unexpected invocation")

    agent = ContextualizationAgent(RunnableLambda(respond))

    with pytest.raises(ValueError, match="nonblank"):
        agent.run(original, amendment)

    assert calls == []


@pytest.mark.parametrize(
    "message",
    [
        AIMessage(
            content="Partial map",
            response_metadata={"status": "incomplete"},
        ),
        AIMessage(content="Unknown completion status"),
        AIMessage(
            content=" ",
            response_metadata={"status": "completed"},
        ),
        AIMessage(
            content="",
            response_metadata={"status": "completed"},
            additional_kwargs={"refusal": "Refused"},
        ),
        AIMessage(
            content=[{"type": "refusal", "refusal": "Refused"}],
            response_metadata={"status": "completed"},
        ),
    ],
)
def test_rejects_unusable_model_messages(message):
    agent = ContextualizationAgent(RunnableLambda(lambda _: message))

    with pytest.raises(ModelResponseError):
        agent.run("Original", "Adenda")


def test_extracts_text_from_responses_content_blocks():
    message = AIMessage(
        content=[
            {"type": "text", "text": "Mapa contextual."},
        ],
        response_metadata={"status": "completed"},
    )
    agent = ContextualizationAgent(RunnableLambda(lambda _: message))

    assert agent.run("Original", "Adenda") == "Mapa contextual."
