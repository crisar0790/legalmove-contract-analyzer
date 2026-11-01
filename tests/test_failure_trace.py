"""Check trace diagnostics without contacting external services."""

import logging
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src import pipeline
from src.exceptions import ModelResponseError
from src.observability import TelemetryError


@pytest.mark.parametrize("trace_id", ["offline-trace", None])
def test_failure_preserves_error_and_logs_only_existing_trace(
    monkeypatch, caplog, trace_id
):
    settings = SimpleNamespace(
        vision_model="vision-test",
        agent_model="agent-test",
        max_retries=0,
        vision_max_output_tokens=100,
        context_max_output_tokens=100,
        extraction_max_output_tokens=100,
    )
    analysis_error = ModelResponseError("Extraction failed")

    monkeypatch.setattr(pipeline, "build_langfuse_client", Mock())
    monkeypatch.setattr(pipeline, "tracing_session", lambda client: nullcontext())
    monkeypatch.setattr(pipeline, "observation", lambda *args, **kwargs: nullcontext())
    monkeypatch.setattr(pipeline, "current_trace_id", lambda: trace_id)
    monkeypatch.setattr(pipeline, "build_callback", Mock())
    analyze = Mock(side_effect=analysis_error)
    monkeypatch.setattr(pipeline, "analyze_contracts", analyze)

    with caplog.at_level(logging.ERROR, logger="src.pipeline"):
        with pytest.raises(
            ModelResponseError if trace_id else TelemetryError
        ) as caught:
            pipeline.analyze_contracts_traced(
                "original.png", "amendment.png", settings=settings
            )

    if trace_id:
        assert caught.value is analysis_error
        assert "Trace ID: offline-trace" in caplog.text
    else:
        analyze.assert_not_called()
        assert "Trace ID:" not in caplog.text
