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

These results describe two clear synthetic image pairs, not general accuracy.
Additional semantic cases have been prepared but not yet evaluated.
Blurred scans, handwriting, and longer documents remain untested.
No comparative model evaluation has been performed.
