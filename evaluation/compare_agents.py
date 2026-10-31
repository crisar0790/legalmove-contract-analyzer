"""Evaluate a candidate agent model against reviewed baseline transcripts."""

import argparse
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from evaluation.run_evaluation import prompt_hashes, section_metrics, write_json
from src.agents.contextualization_agent import ContextualizationAgent
from src.agents.extraction_agent import ExtractionAgent
from src.config import load_settings
from src.llm_client import build_agent_client
from src.observability import (
    TelemetryError,
    build_callback,
    build_langfuse_client,
    current_trace_id,
    observation,
    tracing_session,
    update_output,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BASELINE_DIR = PROJECT_ROOT / "evaluation"


def load_case_inputs(
    case_name: str,
    case_data: dict | None = None,
) -> tuple[str, str, dict]:
    """Load reviewed transcripts or an explicit text-based evaluation case."""
    if case_data is not None:
        reference = {
            "sections_changed": case_data["expected_sections"],
            "review_criteria": case_data["review_criteria"],
        }
        return (
            case_data["original_text"],
            case_data["amendment_text"],
            reference,
        )

    baseline_case = BASELINE_DIR / "runs" / case_name
    original = (baseline_case / "original_transcription.md").read_text(encoding="utf-8")
    amendment = (baseline_case / "amendment_transcription.md").read_text(
        encoding="utf-8"
    )
    reference_path = (
        PROJECT_ROOT
        / "data"
        / "test_contracts"
        / "reference"
        / f"{case_name}_expected.json"
    )
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    return original, amendment, reference


def compare_case(
    case_name: str,
    settings,
    output_dir: Path,
    *,
    case_data: dict | None = None,
) -> dict:
    """Evaluate both agents using the exact baseline transcriptions."""
    original, amendment, reference = load_case_inputs(case_name, case_data)
    client = build_langfuse_client(settings)
    started = perf_counter()

    with tracing_session(client):
        with observation(
            "agent-model-comparison",
            input={"original": original, "amendment": amendment},
            metadata={
                "case": case_name,
                "agent_model": settings.agent_model,
                "reasoning_effort": "low",
                "prompt_sha256": prompt_hashes(),
            },
        ) as root:
            trace_id = current_trace_id()
            if trace_id is None:
                raise TelemetryError("No active comparison trace was created.")

            config = {"callbacks": [build_callback(settings)]}

            with observation("contextualization_agent") as span:
                context_agent = ContextualizationAgent(
                    build_agent_client(
                        settings,
                        max_output_tokens=settings.context_max_output_tokens,
                    ),
                    max_retries=settings.max_retries,
                )
                contextual_map = context_agent.run(original, amendment, config=config)
                update_output(span, contextual_map)

            with observation("extraction_agent") as span:
                extraction_agent = ExtractionAgent(
                    build_agent_client(
                        settings,
                        max_output_tokens=settings.extraction_max_output_tokens,
                    ),
                    max_retries=settings.max_retries,
                )
                result = extraction_agent.run(
                    original, amendment, contextual_map, config=config
                )
                update_output(span, result.model_dump())

            update_output(root, result.model_dump())

    elapsed = perf_counter() - started
    case_dir = output_dir / case_name
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "contextual_map.md").write_text(contextual_map, encoding="utf-8")
    write_json(case_dir / "analysis.json", result.model_dump())

    return {
        "case": case_name,
        "execution_status": "success",
        "trace_id": trace_id,
        "json_valid": True,
        "latency_including_flush_seconds": elapsed,
        "section_metrics": section_metrics(
            reference["sections_changed"], result.sections_changed
        ),
        "manual_review": {
            "all_expected_facts_present": None,
            "correct_context_alignment": None,
            "no_unsupported_claims": None,
            "trace_verified": None,
            "notes": "",
            "criteria": [
                {"criterion": criterion, "passed": None}
                for criterion in reference.get("review_criteria", [])
            ],
        },
    }


def main() -> int:
    """Run a separate, timestamped candidate evaluation."""
    parser = argparse.ArgumentParser(
        description="Compare agent models using reviewed text; consumes API usage."
    )
    parser.add_argument("--model", required=True)
    args = parser.parse_args()

    settings = replace(load_settings(), agent_model=args.model)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output_dir = BASELINE_DIR / "comparisons" / timestamp
    output_dir.mkdir(parents=True, exist_ok=False)

    report = {
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "agent_model": settings.agent_model,
        "reasoning_effort": "low",
        "context_max_output_tokens": settings.context_max_output_tokens,
        "extraction_max_output_tokens": settings.extraction_max_output_tokens,
        "max_retries": settings.max_retries,
        "request_timeout_seconds": settings.request_timeout_seconds,
        "input_source": "Reviewed baseline transcriptions; vision not rerun.",
        "prompt_sha256": prompt_hashes(),
        "semantic_review_status": "pending",
        "cases": [],
    }
    failed = False

    for case_name in ("simple", "complex"):
        print(f"Evaluating {case_name} with {settings.agent_model}...")
        try:
            entry = compare_case(case_name, settings, output_dir)
        except Exception as error:
            failed = True
            entry = {
                "case": case_name,
                "execution_status": "failed",
                "error_type": type(error).__name__,
            }
        report["cases"].append(entry)
        write_json(output_dir / "report.json", report)
        print(f"{case_name}: {entry['execution_status']}")

    print(f"Evidence saved to {output_dir}")
    print("Semantic review remains pending.")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
