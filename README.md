# LegalMove — Contract Analyzer

LegalMove is an academic Python project that compares an original contract
and an amendment provided as JPEG or PNG images.

The application will transcribe both documents with GPT-4o Vision, coordinate
two specialized agents through LangChain, and produce a structured report
validated with Pydantic. Langfuse will provide workflow observability.

## Project goals

- Extract document text while preserving clause numbering and structure.
- Map sections and relationships between the original contract and its amendment.
- Identify additions, deletions, and modifications supported by the documents.
- Validate the final report before exporting it as JSON.
- Trace model calls and workflow stages, including token usage and latency.

## Planned workflow

1. Validate both input images.
2. Transcribe the original contract and amendment.
3. Map document sections with `ContextualizationAgent`.
4. Identify changes with `ExtractionAgent`.
5. Validate the report with Pydantic.
6. Return the JSON report and record the workflow in Langfuse.

## Output schema

The final report will contain exactly these fields:

- `sections_changed`: identifiers of modified, added, or deleted sections.
- `topics_touched`: topics affected by the changes.
- `summary_of_the_change`: a summary supported by the source documents.

## Scope

The initial implementation will provide a command-line interface and two
synthetic document pairs: a simple case and a complex case.

PDF ingestion, a web interface, RAG, and vector databases are outside the
required scope.

## Project status

Repository initialized. The analysis pipeline, dependencies, tests, and
external integrations have not been implemented yet.

## Limitations

This project is an academic prototype. Schema validation does not guarantee
factual or legal accuracy, and its output does not replace professional
legal review.

## Development setup

Use Python 3.12. The exact setup version is recorded in `.python-version`.

Create and activate a virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
