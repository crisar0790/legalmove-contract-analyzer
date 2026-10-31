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
```

## Configuration

Copy `.env.example` to `.env` and configure the OpenAI and Langfuse
credentials. Set `LANGFUSE_HOST` to the base URL for your Langfuse project.

Configuration is loaded explicitly with `load_settings()`. Process environment
variables take precedence over `.env`. Loading configuration does not create
clients or make network requests.

Vision and agent models are configured separately, with `gpt-4o` as the
initial baseline.

Timeouts apply per HTTP attempt. `MAX_RETRIES=N` allows at most `N+1`
attempts per logical model call; zero retries is valid. Client integration
will enforce this budget in a later implementation step.

Output token budgets and the image size limit are initial application
settings and will be reviewed during evaluation.

Run offline tests with:

```bash
python -m pytest

## Output validation

`ContractChangeOutput` defines exactly three required fields:

| Field | Type | Meaning |
| --- | --- | --- |
| `sections_changed` | `list[str]` | Modified, added, or explicitly deleted section identifiers |
| `topics_touched` | `list[str]` | Topics affected by the changes |
| `summary_of_the_change` | `str` | Summary supported by the source documents |

Validation rejects additional fields, incorrect types, blank list items,
and blank summaries. Empty lists are allowed for reports without changes.
Valid text is preserved without automatic trimming or deduplication.

Illustrative output, not a measured model result:

```json
{
  "sections_changed": ["Cláusula 3"],
  "topics_touched": ["Condiciones de pago"],
  "summary_of_the_change": "La cláusula 3 modifica el importe mensual de USD 500 a USD 650 y el vencimiento del día 5 al día 10."
}
```

Schema validation checks the report structure. Factual accuracy and
completeness must be evaluated against the source documents separately.

## Image input validation

Input images are validated locally before model requests.

Validation checks file availability, readability, byte size, actual JPEG/PNG
content, and successful decoding. Empty, corrupted, unsupported, and oversized
files are rejected.

MIME types are detected from image content rather than filename extensions.
Valid images are encoded as base64 data URIs without modifying their bytes.

The byte limit is configured through `MAX_IMAGE_SIZE_BYTES`.
Image validation and encoding require no API credentials or network access.

## Model clients and API errors

Vision and agent clients are constructed explicitly from application settings.
SDK retries are disabled; `call_with_retries()` owns the retry budget.

Connection failures, timeouts, HTTP 408, 409, 429, and server errors may be
retried with bounded exponential backoff. Other HTTP errors fail immediately.
Each logical call allows at most `MAX_RETRIES + 1` attempts.

Application error messages omit provider response bodies. Empty text,
refusals, and incomplete text completions are rejected rather than published
as successful reports.

The model selection remains subject to requirement verification and real
evaluation. GPT-4o is the initial baseline; vision and agent models remain
separately configurable.
