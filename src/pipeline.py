"""Orchestrate image transcription and specialized contract agents."""

from collections.abc import Callable
from dataclasses import dataclass
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


@dataclass(frozen=True)
class PipelineResult:
    """Internal result; only analysis belongs to the public JSON output."""

    analysis: ContractChangeOutput
    trace_id: str | None = None


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
        """Analyze two images, stopping immediately on any stage failure."""
        original_path = Path(original_path)
        amendment_path = Path(amendment_path)

        for path in (original_path, amendment_path):
            encode_contract_image(
                path,
                max_size_bytes=self._settings.max_image_size_bytes,
            )

        original = self._parser(original_path)
        amendment = self._parser(amendment_path)

        contextual_map = self._contextualization_agent.run(
            original.text, amendment.text, config=config
        )
        analysis = self._extraction_agent.run(
            original.text, amendment.text, contextual_map, config=config
        )
        return PipelineResult(analysis=analysis)


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
