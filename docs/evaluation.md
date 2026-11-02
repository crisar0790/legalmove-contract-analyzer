# Image-based evaluation

Two synthetic image pairs were evaluated using GPT-4o for transcription
and GPT-6.1 Sol with low reasoning effort for both agents.

| Case | Expected sections | Precision | Recall | Expected facts present |
| --- | --- | --- | --- | --- |
| Simple | Clause 3 | 1.0 | 1.0 | 3/3 |
| Complex | Clauses 2, 4, 7 | 1.0 | 1.0 | 6/6 |

Measured latency, including telemetry flush waiting, was approximately
13.09 seconds for the simple case and 17.63 seconds for the complex case.

## Content review

All four images were inspected. Their hashes match the evaluation report.
Transcriptions preserve the source content; observed differences are limited
to whitespace, line wrapping, and Markdown emphasis.

Both contextual maps distinguish amendment numbering from affected contract
clause identifiers. The complex map correctly aligns the territorial
modification, explicit deletion, and newly incorporated support clause.

Both final reports contain the expected changes. No unsupported claims or
false changes to preserved provisions were identified in these cases.

## Evidence

- `evaluation/report.json`: configuration, metrics, trace IDs, and review.
- `evaluation/runs/`: transcriptions, contextual maps, and vision metadata.
- `outputs/examples/`: actual validated reports.
- `data/test_contracts/`: images and manually prepared references.

Trace verification is recorded separately in each case's manual review.
Agent token usage is available in Langfuse and is not collected locally.

## Limitations

The initial image-based results above used GPT-6.1 Sol for both agents.
Subsequent text-based evaluations assessed GPT-6 Luna on the two reviewed
document pairs and five additional semantic cases. All 13 prepared semantic
criteria passed manual review.

The contextualization prompt was refined during evaluation. These runs
do not constitute a controlled comparison using identical final prompts
across both models. See [model selection](model-selection.md) for details.

Results are limited to small synthetic datasets and do not establish
general accuracy. Blurred scans, handwriting, and longer documents remain
untested. The unreadable-amount text case does not evaluate vision on a
blurred image.

## October 31 clean-checkout verification

On October 31, 2026, a fresh repository clone was installed with Python
3.12.14 and the pinned development requirements.

Dependency compatibility checks, Ruff linting, and formatting checks passed.
All 182 offline tests passed.

Both image pairs were then analyzed through the CLI using GPT-4o for vision
and GPT-6 Luna for both agents. Manual review confirmed the expected sections
and change details in both JSON reports. The reviewer also confirmed the
configured models in both Langfuse traces.

| Case | Changed sections | Trace ID | Dashboard duration |
| --- | --- | --- | --- |
| Simple | Clause 3 | `dfb5f90ff14498bc45375977f3922f80` | 10.41 s |
| Complex | Clauses 2, 4, and 7 | `ef2200578e4b6b71ecbb0b374164097d` | 16.08 s |

Each inspected trace contained two vision generations and one generation
per agent. Durations are individual observations, not benchmark averages.
This verification supports these two fixtures and does not establish
accuracy on arbitrary contracts.
