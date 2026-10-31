"""Run opt-in semantic evaluations using real agent calls and no vision."""

import argparse
import json
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256

from evaluation.compare_agents import BASELINE_DIR, compare_case
from evaluation.run_evaluation import prompt_hashes, write_json
from src.config import load_settings


def main() -> int:
    """Record actual outputs without automatically approving their meaning."""
    parser = argparse.ArgumentParser(
        description="Evaluate text-based agent cases; consumes API usage."
    )
    parser.add_argument("--model", required=True)
    args = parser.parse_args()

    cases_path = BASELINE_DIR / "semantic_cases.json"
    cases_bytes = cases_path.read_bytes()
    cases = json.loads(cases_bytes)

    settings = replace(load_settings(), agent_model=args.model)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output_dir = BASELINE_DIR / "semantic_runs" / timestamp
    output_dir.mkdir(parents=True, exist_ok=False)

    report = {
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "agent_model": settings.agent_model,
        "reasoning_effort": "low",
        "context_max_output_tokens": settings.context_max_output_tokens,
        "extraction_max_output_tokens": settings.extraction_max_output_tokens,
        "max_retries": settings.max_retries,
        "request_timeout_seconds": settings.request_timeout_seconds,
        "input_source": "Text-based semantic cases; no vision calls.",
        "cases_sha256": sha256(cases_bytes).hexdigest(),
        "prompt_sha256": prompt_hashes(),
        "semantic_review_status": "pending",
        "cases": [],
    }
    failed = False

    for case in cases:
        case_name = case["id"]
        print(f"Evaluating {case_name}...")
        try:
            entry = compare_case(
                case_name,
                settings,
                output_dir,
                case_data=case,
            )
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
    print("Execution success does not imply semantic correctness.")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
