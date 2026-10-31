"""Run contract analysis from the command line."""

import argparse
import logging
import os
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from src.config import ConfigurationError, load_settings
from src.exceptions import LegalMoveError
from src.observability import TelemetryError
from src.pipeline import analyze_contracts_traced


def build_parser() -> argparse.ArgumentParser:
    """Define the public command-line interface."""
    parser = argparse.ArgumentParser(
        description="Compare original contract and amendment images."
    )
    parser.add_argument(
        "original",
        type=Path,
        help="Path to the original contract JPEG or PNG image.",
    )
    parser.add_argument(
        "amendment",
        type=Path,
        help="Path to the amendment JPEG or PNG image.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional destination for the validated JSON report.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show additional application diagnostics on stderr.",
    )
    return parser


def write_report(path: Path, content: str) -> None:
    """Replace the destination only after the complete report is written."""
    temporary_path = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=".legalmove-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)

        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def validate_output_path(output: Path | None, original: Path, amendment: Path) -> None:
    """Prevent an output destination from replacing either input image."""
    if output is None:
        return
    if output.resolve() in {original.resolve(), amendment.resolve()}:
        raise ValueError("The output path must differ from both input images.")
    if not output.parent.is_dir():
        raise ValueError("The output parent directory must already exist.")
    if output.is_dir():
        raise ValueError("The output path must not be a directory.")


def main(argv: list[str] | None = None) -> int:
    """Print JSON on success and return a nonzero code on failure."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.WARNING,
        stream=sys.stderr,
        format="%(levelname)s: %(message)s",
    )

    try:
        validate_output_path(args.output, args.original, args.amendment)
        settings = load_settings()
        if args.verbose:
            print(
                f"Vision model: {settings.vision_model}\n"
                f"Agent model: {settings.agent_model}",
                file=sys.stderr,
            )

        result = analyze_contracts_traced(
            args.original, args.amendment, settings=settings
        )
        content = result.analysis.model_dump_json(indent=2) + "\n"
        if args.output is not None:
            write_report(args.output, content)

        if result.trace_id is not None:
            print(f"Trace ID: {result.trace_id}", file=sys.stderr)
        sys.stdout.write(content)
        return 0
    except (ConfigurationError, LegalMoveError, TelemetryError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except OSError:
        print("Error: unable to read or write an application file.", file=sys.stderr)
        return 1
    except Exception as error:
        print("Error: unexpected analysis failure.", file=sys.stderr)
        if args.verbose:
            print(f"Failure type: {type(error).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
