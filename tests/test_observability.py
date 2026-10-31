"""Offline tests for explicit Langfuse client configuration."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.observability import (
    TelemetryError,
    build_langfuse_client,
    flush_with_deadline,
    tracing_session,
)


def test_maps_settings_to_langfuse_client(monkeypatch):
    constructor = Mock()
    monkeypatch.setattr("src.observability.Langfuse", constructor)

    settings = SimpleNamespace(
        langfuse_public_key="test-public-key",
        langfuse_secret_key="test-secret-key",
        langfuse_host="https://langfuse.example.test",
    )

    result = build_langfuse_client(settings)

    constructor.assert_called_once_with(
        public_key="test-public-key",
        secret_key="test-secret-key",
        base_url="https://langfuse.example.test",
        timeout=5,
    )
    assert result is constructor.return_value


def test_flushes_successfully():
    client = Mock()

    flush_with_deadline(client)

    client.flush.assert_called_once()


def test_reports_flush_failure():
    client = Mock()
    client.flush.side_effect = RuntimeError("Simulated failure")

    with pytest.raises(TelemetryError, match="flush failed"):
        flush_with_deadline(client)


def test_preserves_analysis_error_when_flush_also_fails(monkeypatch):
    monkeypatch.setattr(
        "src.observability.flush_with_deadline",
        Mock(side_effect=TelemetryError("Flush failed")),
    )

    with pytest.raises(ValueError, match="Original analysis error"):
        with tracing_session(Mock()):
            raise ValueError("Original analysis error")


def test_reports_telemetry_failure_after_successful_analysis(monkeypatch):
    monkeypatch.setattr(
        "src.observability.flush_with_deadline",
        Mock(side_effect=TelemetryError("Flush failed")),
    )

    with pytest.raises(TelemetryError):
        with tracing_session(Mock()):
            pass


def test_reports_flush_deadline_without_blocking(monkeypatch):
    event = Mock()
    event.wait.return_value = False
    thread_constructor = Mock()

    monkeypatch.setattr("src.observability.Event", Mock(return_value=event))
    monkeypatch.setattr("src.observability.Thread", thread_constructor)

    with pytest.raises(TelemetryError, match="Timed out"):
        flush_with_deadline(Mock(), timeout_seconds=2)

    event.wait.assert_called_once_with(2)
    thread_constructor.return_value.start.assert_called_once()
    assert thread_constructor.call_args.kwargs["daemon"] is True
