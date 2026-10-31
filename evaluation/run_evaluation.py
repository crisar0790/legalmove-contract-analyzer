"""Run and record real image-based contract evaluations."""

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from time import perf_counter

from src.config import load_settings
from src.pipeline import analyze_contracts_traced

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "test_contracts"
EVALUATION_DIR = PROJECT_ROOT / "evaluation"
EXAMPLES_DIR = PROJECT_ROOT / "outputs" / "examples"


def write_json(path: Path, value: object) -> None:
    """Write UTF-8 evaluation evidence."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def section_metrics(expected: list[str], detected: list[str]) -> dict:
    """Compare section labels, ignoring case and repeated whitespace."""

    def normalize(value):
        return " ".join(value.casefold().split())

    expected_set = {normalize(value) for value in expected}
    detected_set = {normalize(value) for value in detected}
    true_positives = expected_set & detected_set
    false_positives = detected_set - expected_set
    false_negatives = expected_set - detected_set

    precision = (
        len(true_positives) / len(detected_set)
        if detected_set
        else float(not expected_set)
    )
    recall = len(true_positives) / len(expected_set) if expected_set else 1.0
    return {
        "true_positives": sorted(true_positives),
        "false_positives": sorted(false_positives),
        "false_negatives": sorted(false_negatives),
        "precision": precision,
        "recall": recall,
    }


def prompt_hashes() -> dict[str, str]:
    """Identify the exact prompt files used for this evaluation."""
    return {
        name: sha256((PROJECT_ROOT / "prompts" / f"{name}.md").read_bytes()).hexdigest()
        for name in ("vision", "contextualization", "extraction")
    }


def evaluate_case(case_name: str, settings) -> dict:
    """Run a real image pair and retain evidence for manual review."""
    reference_path = DATA_DIR / "reference" / f"{case_name}_expected.json"
    reference = json.loads(reference_path.read_text(encoding="utf-8"))
    original_path = DATA_DIR / reference["original_image"]
    amendment_path = DATA_DIR / reference["amendment_image"]

    started = perf_counter()
    result = analyze_contracts_traced(
        original_path,
        amendment_path,
        settings=settings,
    )
    elapsed = perf_counter() - started

    evidence_dir = EVALUATION_DIR / "runs" / case_name
    evidence_dir.mkdir(parents=True, exist_ok=True)

    documents = {}
    for role, document in (
        ("original", result.original_document),
        ("amendment", result.amendment_document),
    ):
        if document is None:
            raise RuntimeError("Pipeline transcription evidence is missing.")
        documents[role] = asdict(document)
        (evidence_dir / f"{role}_transcription.md").write_text(
            document.text, encoding="utf-8"
        )

    if result.contextual_map is None:
        raise RuntimeError("Pipeline contextual map is missing.")

    (evidence_dir / "contextual_map.md").write_text(
        result.contextual_map, encoding="utf-8"
    )
    write_json(evidence_dir / "vision_metadata.json", documents)
    write_json(
        EXAMPLES_DIR / f"{case_name}.json",
        result.analysis.model_dump(),
    )

    return {
        "case": case_name,
        "execution_status": "success",
        "json_valid": True,
        "trace_id": result.trace_id,
        "latency_including_flush_seconds": elapsed,
        "expected_sections": reference["sections_changed"],
        "detected_sections": result.analysis.sections_changed,
        "section_metrics": section_metrics(
            reference["sections_changed"],
            result.analysis.sections_changed,
        ),
        "vision_usage": {
            role: metadata["usage"] for role, metadata in documents.items()
        },
        "agent_usage": None,
        "agent_usage_note": (
            "Available in Langfuse generations; not collected locally yet."
        ),
        "input_sha256": {
            "original": sha256(original_path.read_bytes()).hexdigest(),
            "amendment": sha256(amendment_path.read_bytes()).hexdigest(),
        },
        "manual_review": {
            "transcription_fidelity": None,
            "context_alignment": None,
            "expected_facts": [
                {"fact": fact, "passed": None} for fact in reference["expected_facts"]
            ],
            "unchanged_facts": [
                {"fact": fact, "passed": None} for fact in reference["unchanged_facts"]
            ],
            "change_types_correct": None,
            "no_unsupported_claims": None,
            "trace_verified": None,
            "notes": "",
        },
    }


def main() -> int:
    """Evaluate selected cases without claiming unreviewed semantic success."""
    parser = argparse.ArgumentParser(
        description="Run real image-based evaluations; consumes API usage."
    )
    parser.add_argument(
        "--case",
        choices=["simple", "complex", "all"],
        default="all",
    )
    args = parser.parse_args()
    settings = load_settings()
    cases = ["simple", "complex"] if args.case == "all" else [args.case]

    report = {
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "vision_model": settings.vision_model,
            "agent_model": settings.agent_model,
            "reasoning_effort": "low",
            "request_timeout_seconds": settings.request_timeout_seconds,
            "max_retries": settings.max_retries,
            "vision_max_output_tokens": settings.vision_max_output_tokens,
            "context_max_output_tokens": settings.context_max_output_tokens,
            "extraction_max_output_tokens": settings.extraction_max_output_tokens,
        },
        "prompt_sha256": prompt_hashes(),
        "semantic_review_status": "pending",
        "cases": [],
    }
    failed = False
    for case_name in cases:
        print(f"Evaluating {case_name}...")
        try:
            entry = evaluate_case(case_name, settings)
        except Exception as error:
            failed = True
            entry = {
                "case": case_name,
                "execution_status": "failed",
                "error_type": type(error).__name__,
            }
        report["cases"].append(entry)
        write_json(EVALUATION_DIR / "report.json", report)
        print(f"{case_name}: {entry['execution_status']}")

    print("Report saved to evaluation/report.json")
    print("Semantic review remains pending.")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
