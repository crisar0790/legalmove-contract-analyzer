"""Exercise extraction through the SDK with simulated HTTP responses."""

import json

import httpx
import pytest
from langchain_openai import ChatOpenAI

from src.agents.extraction_agent import ExtractionAgent
from src.exceptions import ModelResponseError


@pytest.mark.parametrize(
    ("status", "details", "text", "expected_error"),
    [
        (
            "incomplete",
            {"reason": "max_output_tokens"},
            '{"sections_changed": ["Cláusula 3"],',
            "output token limit",
        ),
        (
            "completed",
            None,
            json.dumps(
                {
                    "sections_changed": [],
                    "topics_touched": [],
                    "summary_of_the_change": "Sin cambios.",
                    "unexpected": True,
                }
            ),
            "structured output validation",
        ),
    ],
)
def test_response_status_precedes_schema_validation(
    status, details, text, expected_error
):
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "resp_offline",
                "object": "response",
                "created_at": 0,
                "model": "offline-model",
                "status": status,
                "incomplete_details": details,
                "error": None,
                "parallel_tool_calls": False,
                "tool_choice": "auto",
                "tools": [],
                "output": [
                    {
                        "id": "msg_offline",
                        "type": "message",
                        "role": "assistant",
                        "status": status,
                        "content": [
                            {
                                "type": "output_text",
                                "text": text,
                                "annotations": [],
                            }
                        ],
                    }
                ],
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        model = ChatOpenAI(
            model="offline-model",
            api_key="offline-test-key",
            base_url="https://offline.invalid/v1",
            http_client=client,
            max_retries=0,
            use_responses_api=True,
            output_version="responses/v1",
        )
        agent = ExtractionAgent(model, max_retries=0)

        with pytest.raises(ModelResponseError, match=expected_error):
            agent.run("Original", "Amendment", "Contextual map")

    assert len(requests) == 1
    assert requests[0]["text"]["format"]["type"] == "json_schema"
    assert requests[0]["text"]["format"]["strict"] is True
