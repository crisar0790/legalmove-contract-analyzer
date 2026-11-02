"""Orchestrate image transcription and specialized contract agents."""

import logging
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from langchain_core.runnables import RunnableConfig

from src.agents.contextualization_agent import ContextualizationAgent
from src.agents.extraction_agent import ExtractionAgent
from src.config import Settings
from src.image_parser import (
    ParsedDocument,
    encode_contract_image,
    parse_contract_document,
)
from src.llm_client import build_agent_client, build_vision_client
from src.models import ContractChangeOutput
from src.observability import (
    TelemetryError,
    build_callback,
    build_langfuse_client,
    current_trace_id,
    observation,
    tracing_session,
    update_output,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineResult:
    """Internal analysis result with evaluation and tracing evidence."""

    analysis: ContractChangeOutput
    trace_id: str | None = None
    original_document: ParsedDocument | None = None
    amendment_document: ParsedDocument | None = None
    contextual_map: str | None = None


class ContractAnalysisPipeline:
    """Coordinate injected components in a deterministic execution order."""

    def __init__(
        self,
        *,
        settings: Settings,
        parser: Callable[[Path], ParsedDocument],
        contextualization_agent: ContextualizationAgent,
        extraction_agent: ExtractionAgent,
    ) -> None:
        self._settings = settings
        self._parser = parser
        self._contextualization_agent = contextualization_agent
        self._extraction_agent = extraction_agent

    def run(
        self,
        original_path: str | Path,
        amendment_path: str | Path,
        *,
        config: RunnableConfig | None = None,
    ) -> PipelineResult:
        """Analyze two images with observable stages and exact handoff."""
        original_path = Path(original_path)
        amendment_path = Path(amendment_path)

        with observation("validate_inputs") as span:
            for path in (original_path, amendment_path):
                encode_contract_image(
                    path,
                    max_size_bytes=self._settings.max_image_size_bytes,
                )
            update_output(span, {"valid": True})

        with observation(
            "parse_original_contract",
            input={"filename": original_path.name},
        ) as span:
            original = self._parser(original_path)
            update_output(span, original.text)

        with observation(
            "parse_amendment_contract",
            input={"filename": amendment_path.name},
        ) as span:
            amendment = self._parser(amendment_path)
            update_output(span, amendment.text)

        with observation(
            "contextualization_agent",
            input={
                "original": original.text,
                "amendment": amendment.text,
            },
        ) as span:
            contextual_map = self._contextualization_agent.run(
                original.text, amendment.text, config=config
            )
            update_output(span, contextual_map)

        with observation(
            "extraction_agent",
            input={
                "original": original.text,
                "amendment": amendment.text,
                "contextual_map": contextual_map,
            },
        ) as span:
            analysis = self._extraction_agent.run(
                original.text, amendment.text, contextual_map, config=config
            )
            update_output(span, analysis.model_dump())

        return PipelineResult(
            analysis=analysis,
            original_document=original,
            amendment_document=amendment,
            contextual_map=contextual_map,
        )


def analyze_contracts(
    original_path: str | Path,
    amendment_path: str | Path,
    *,
    settings: Settings,
    config: RunnableConfig | None = None,
) -> PipelineResult:
    """Build application components and execute one complete analysis."""
    context_model = build_agent_client(
        settings,
        max_output_tokens=settings.context_max_output_tokens,
    )
    extraction_model = build_agent_client(
        settings,
        max_output_tokens=settings.extraction_max_output_tokens,
    )

    with build_vision_client(settings) as vision_client:

        def parser(path: Path) -> ParsedDocument:
            return parse_contract_document(
                path, settings=settings, client=vision_client
            )

        pipeline = ContractAnalysisPipeline(
            settings=settings,
            parser=parser,
            contextualization_agent=ContextualizationAgent(
                context_model, max_retries=settings.max_retries
            ),
            extraction_agent=ExtractionAgent(
                extraction_model, max_retries=settings.max_retries
            ),
        )
        return pipeline.run(original_path, amendment_path, config=config)


def analyze_contracts_traced(
    original_path: str | Path,
    amendment_path: str | Path,
    *,
    settings: Settings,
) -> PipelineResult:
    """Execute tracing and log the available trace ID on failure."""
    trace_id = None
    try:
        client = build_langfuse_client(settings)

        with tracing_session(client):
            with observation(
                "contract-analysis",
                input={
                    "original": Path(original_path).name,
                    "amendment": Path(amendment_path).name,
                },
                metadata={
                    "vision_model": settings.vision_model,
                    "agent_model": settings.agent_model,
                    "max_retries": settings.max_retries,
                    "vision_max_output_tokens": settings.vision_max_output_tokens,
                    "context_max_output_tokens": settings.context_max_output_tokens,
                    "extraction_max_output_tokens": (
                        settings.extraction_max_output_tokens
                    ),
                },
            ) as root:
                trace_id = current_trace_id()
                if trace_id is None:
                    raise TelemetryError("No active Langfuse trace was created.")

                result = analyze_contracts(
                    original_path,
                    amendment_path,
                    settings=settings,
                    config={"callbacks": [build_callback(settings)]},
                )
                update_output(root, result.analysis.model_dump())
                return replace(result, trace_id=trace_id)
    except Exception:
        if trace_id is not None:
            logger.error("Traced workflow failed. Trace ID: %s", trace_id)
        raise
