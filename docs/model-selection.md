# Model selection

## Selected configuration

- Vision: `gpt-4o`, preserving the assignment requirement.
- Contextualization and extraction: `gpt-6-luna`.
- Initial evaluation baseline: `gpt-6.1-sol`.
- Agent reasoning effort: `low`.

Vision and agent models remain separately configurable through
`VISION_MODEL` and `AGENT_MODEL`.

## Selection evidence

The initial image-based evaluation used GPT-4o for transcription and
GPT-6.1 Sol for both agents. The two document pairs produced valid reports
containing all nine expected facts and the correct affected sections.

GPT-6 Luna was then evaluated using the same reviewed transcriptions,
without repeating vision calls. Its final reports preserved all expected
facts, but its first complex contextual map incorrectly included replaced
and deleted clauses in a general ratification mapping.

The contextualization prompt was clarified to exclude those clauses and
avoid references to unseen sections. A subsequent Luna execution corrected
the alignment while preserving the expected extraction results.

With the revised prompt, Luna also passed manual review of five additional
text-based cases and their 13 criteria:

- No substantive changes.
- Partial amendment without implied deletions.
- Different amendment and original numbering.
- An unreadable amended amount.
- Instructions embedded in document content.

These results support selecting Luna for the agents in this academic
prototype. GPT-4o remains the vision model.

## Cost and latency

The inspected complex Luna comparison recorded approximately USD 0.000840
across its two agent generations in Langfuse, excluding vision.

Agent-only latency must not be compared directly with full image pipeline
latency. No general speedup, measured savings percentage, or fixed
per-document cost is claimed.

Record actual token usage, including reasoning tokens where applicable,
when calculating costs.

## Evaluation limitations

The dataset is small and synthetic. Passing these cases does not establish
general accuracy, legal reliability, or complete prompt injection resistance.

Sol was not evaluated on the five additional semantic cases. The revised
contextualization prompt was not benchmarked across both models.

Luna's candidate evaluations used reviewed text. A subsequent verification
from a clean checkout ran both synthetic image pairs through the complete
pipeline with GPT-4o and GPT-6 Luna. Both final reports were manually
reviewed, and their Langfuse traces and configured models were confirmed.
See [evaluation notes](evaluation.md) for details.

Subsequent evaluation covered nine text-based cases and 29 prepared
criteria, including complete revisions, absent provisions, uncertain scope,
and non-substantive renumbering. All criteria passed the latest content
review, with an unnecessary scope warning noted in the no-change map.

Three course-provided image pairs were also executed. Case 1 was rerun
after correcting an unsupported partial-scope classification.
See [course evidence](../evaluation/course_runs/20261101/README.md)
and [evaluation instructions](../evaluation/README.md) for provenance
and review limitations.

## Lifecycle constraint

According to the official documentation checked during model selection,
GPT-4o is deprecated, with API removal scheduled for January 14, 2027.
OpenAI recommends GPT-6 Luna as its replacement.

Replacing the required vision model must be reconciled with the assignment
requirements before claiming compliance with that requirement.

## Evidence

- `evaluation/report.json`: initial image-based evaluation.
- `evaluation/runs/`: transcriptions and contextual maps from that evaluation.
- `evaluation/comparisons/`: candidate agent model executions.
- `evaluation/semantic_runs/`: additional text-based evaluations.
- `docs/technical-decisions.md`: parameter choices and implementation rationale.

## Sources

- https://developers.openai.com/api/docs/models/gpt-4o
- https://developers.openai.com/api/docs/models/gpt-6.1-sol
- https://developers.openai.com/api/docs/models/gpt-6-luna
- https://developers.openai.com/api/docs/deprecations
