# Technical decisions

## Two-stage agent design

Contract comparison involves two distinct responsibilities: aligning
document sections and extracting substantive changes.

ContextualizationAgent inventories both documents and maps their sections.
This makes numbering differences, unmatched sections, collective
ratifications, and ambiguous references visible before extraction.

ExtractionAgent receives both complete transcriptions and the contextual
map. It checks the proposed correspondences against the source texts and
produces the three-field report through structured output.

Keeping these responsibilities separate makes failures easier to inspect:
a reviewer can distinguish transcription errors, alignment errors, and
extraction errors. It also allows each stage to have its own prompt and
output budget.

The contextual map is an auxiliary interpretation, not an authoritative
source. Supplying both original texts to the extractor reduces dependence
on an incomplete or incorrect map, but does not eliminate error propagation.

The implementation uses sequential LangChain chains with a fixed handoff.
It does not implement autonomous planning or tool selection. No controlled
single-agent comparison was performed, so the two-stage design is justified
by separation of responsibilities and inspectability rather than a measured
accuracy improvement.

## System prompt design

The prompts are maintained as separate versioned files so their roles,
constraints, and changes can be reviewed independently of application code.

### Vision transcription

The vision prompt requests faithful transcription rather than comparison.
It emphasizes numbering, amounts, dates, currencies, and negations because
errors in these details can change the meaning of a contractual provision.

Unreadable fragments are marked as [ILEGIBLE] instead of being completed
from context. Document content is treated as data, including text that
resembles instructions to the model.

### Contextualization

The contextualization prompt assigns an alignment role and requires fixed
headings for document inventories, correspondences, unmatched sections,
and ambiguities. This produces an intermediate artifact that a reviewer
can inspect.

It distinguishes amendment numbering from original clause identifiers and
prevents omission from a partial amendment from being treated automatically
as deletion.

The prompt was refined after an observed ratification error: a collective
reference to unchanged clauses must exclude provisions explicitly modified,
replaced, or deleted by the amendment.

### Extraction

The extraction prompt assigns an auditing role and requires findings to be
supported by the source documents. It instructs the agent to verify the
contextual map, review unmatched sections, preserve material uncertainty,
and distinguish substantive changes from visual differences.

The system prompt defines the semantic requirements. The structured-output
schema defines the required fields and types, while Pydantic validates the
returned structure. These mechanisms complement each other; schema
validation does not establish factual correctness.

### Evaluation boundaries

The prompts request Spanish maps and reports while preserving the source
language during transcription. Illustrative findings are explicitly marked
as examples rather than evidence for the supplied documents.

Prompt instructions are tested through reviewed examples, including one
case containing embedded instructions. These observations do not establish
universal resistance to prompt injection.

The prompts distinguish partial amendments, complete revised versions,
and uncertain scope. Missing provisions are treated as removals only when
complete-version evidence supports that interpretation. Renumbering and
equivalent paraphrases alone are not substantive changes.

Observed failures led to explicit rules against reporting renumbering as
a change or inferring partial scope solely from an amendment title.
These refinements were followed by reviewed evaluations; they do not
establish general reliability.

## Model selection

- Vision: `gpt-4o`, preserving the assignment requirement.
- Contextualization and extraction: `gpt-6-luna`.
- Initial quality baseline: `gpt-6.1-sol`.

Both models produced complete reports for the two baseline document pairs.
Luna initially mapped a general ratification too broadly in the complex
contextual map, although its final extraction remained correct.

The contextualization prompt was clarified to exclude replaced, modified,
and deleted clauses from general ratification mappings. A subsequent Luna
execution corrected the alignment and preserved all expected findings.

With the revised prompt, Luna also passed manual review of five additional
text-based cases and their 13 criteria: no changes, partial amendment,
different numbering, unreadable amount, and embedded document instructions.

These observations support selecting Luna for this academic prototype.
They do not establish general equivalence to Sol. Sol was not evaluated
on the five additional cases, and the revised prompt was not benchmarked
across both models.

## Cost and latency evidence

The inspected complex Luna comparison recorded approximately USD 0.000840
across its two agent generations in Langfuse. Vision was excluded.

Do not compare agent-only evaluation latency directly with full image
pipeline latency. No general speedup or fixed per-document cost is claimed.

## Model settings

Reasoning effort remains `low`. Output budgets remain 4096 tokens for vision
and 2048 for each agent. The reviewed executions completed with these budgets;
longer documents may require different limits.

The request timeout remains 60 seconds per attempt. At most two additional
retries are allowed for eligible transient errors. These are operational
bounds, not globally optimized settings.

No temperature value is explicitly configured. No automatic output repair
is performed.

## Vision lifecycle

GPT-4o is deprecated, with API removal scheduled for January 14, 2027,
according to the official documentation checked during model selection.
Replacing the required vision model must be reconciled with the assignment.

## Evidence and limitations

Image-based baseline evidence is stored in `evaluation/runs/` and
`evaluation/report.json`. Candidate model evidence is stored in
`evaluation/comparisons/`; text-based edge cases are in
`evaluation/semantic_runs/`.

The baseline image evaluation used Sol. Luna's candidate comparisons used
reviewed transcriptions and did not rerun vision.

A subsequent clean-checkout verification ran both synthetic image pairs
through vision and both agents using GPT-4o and GPT-6 Luna. Both reports
were manually reviewed, and the Langfuse traces and configured models
were confirmed. See [evaluation notes](evaluation.md) for details.

This final verification is separate from the preserved Sol baseline.
Subsequent evaluation covered nine text-based cases and 29 prepared
criteria, including complete revisions, absent provisions, uncertain scope,
and non-substantive renumbering. All criteria passed the latest content
review, with an unnecessary scope warning noted in the no-change map.

Three course-provided image pairs were also executed. Case 1 was rerun
after correcting an unsupported partial-scope classification.
See [course evidence](../evaluation/course_runs/20261101/README.md)
and [evaluation instructions](../evaluation/README.md) for provenance
and review limitations.

Results cover a small synthetic dataset. They do not prove production
readiness, universal prompt injection resistance, or legal accuracy.
