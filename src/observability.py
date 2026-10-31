"""Provide explicit Langfuse tracing and bounded flush waiting."""

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from threading import Event, Thread

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from openai.types.chat import ChatCompletion

from src.config import Settings

logger = logging.getLogger(__name__)
_current_client: ContextVar[Langfuse | None] = ContextVar(
    "legalmove_langfuse_client", default=None
)


class TelemetryError(RuntimeError):
    """Raised when telemetry cannot be completed or confirmed."""


def build_langfuse_client(settings: Settings) -> Langfuse:
    """Map the project host setting to the SDK base URL parameter."""
    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        base_url=settings.langfuse_host,
        timeout=5,
    )


@contextmanager
def observation(name: str, **kwargs) -> Iterator:
    """Create an observation only inside an explicitly enabled session."""
    client = _current_client.get()
    if client is None:
        yield None
        return

    with client.start_as_current_observation(name=name, **kwargs) as span:
        try:
            yield span
        except Exception as error:
            span.update(
                level="ERROR",
                status_message=type(error).__name__,
            )
            raise


def update_output(span, output: object) -> None:
    """Attach an output when tracing is enabled."""
    if span is not None:
        span.update(output=output)


def flush_with_deadline(client: Langfuse, timeout_seconds: float = 10) -> None:
    """Bound application waiting; the SDK flush itself is not cancellable."""
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive.")

    completed = Event()
    failures = []

    def flush():
        try:
            client.flush()
        except Exception as error:
            failures.append(type(error).__name__)
        finally:
            completed.set()

    Thread(target=flush, daemon=True).start()

    if not completed.wait(timeout_seconds):
        raise TelemetryError("Timed out waiting for Langfuse flush.")
    if failures:
        raise TelemetryError("Langfuse flush failed.")


@contextmanager
def tracing_session(client: Langfuse) -> Iterator:
    """Activate tracing and preserve analysis errors if flushing also fails."""
    token = _current_client.set(client)
    analysis_failed = False
    try:
        yield
    except BaseException:
        analysis_failed = True
        raise
    finally:
        _current_client.reset(token)
        try:
            flush_with_deadline(client)
        except TelemetryError:
            if not analysis_failed:
                raise
            logger.error("Telemetry flush failed while handling an analysis failure.")


def build_callback(settings: Settings) -> CallbackHandler:
    """Use the Langfuse client registered for the configured project."""
    return CallbackHandler(public_key=settings.langfuse_public_key)


def current_trace_id() -> str | None:
    """Return the active trace identifier without inventing one."""
    client = _current_client.get()
    return client.get_current_trace_id() if client is not None else None


def trace_vision_call(
    operation: Callable[[], ChatCompletion],
    *,
    model: str,
    prompt: str,
    image_metadata: dict,
    max_output_tokens: int,
) -> ChatCompletion:
    """Record one actual vision request without uploading base64 to traces."""
    with observation(
        "vision_transcription",
        as_type="generation",
        model=model,
        input={"system_prompt": prompt, "image": image_metadata},
        model_parameters={
            "detail": "high",
            "max_completion_tokens": max_output_tokens,
        },
    ) as generation:
        response = operation()
        if generation is not None:
            usage = response.usage
            usage_details = (
                {
                    "input": usage.prompt_tokens,
                    "output": usage.completion_tokens,
                    "total": usage.total_tokens,
                }
                if usage is not None
                else None
            )
            choices = [
                {
                    "text": choice.message.content,
                    "refusal": choice.message.refusal,
                    "finish_reason": choice.finish_reason,
                }
                for choice in response.choices
            ]
            generation.update(
                model=response.model,
                output=choices,
                usage_details=usage_details,
                metadata={"response_id": response.id},
            )
            if not response.choices or any(
                choice.finish_reason != "stop"
                or choice.message.refusal is not None
                or not choice.message.content
                or not choice.message.content.strip()
                for choice in response.choices
            ):
                generation.update(
                    level="ERROR",
                    status_message="Unusable transcription response",
                )
        return response
