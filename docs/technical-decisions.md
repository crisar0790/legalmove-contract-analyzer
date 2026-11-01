# Technical decisions

## Model selection

- Vision: `gpt-4o`, preserving the assignment requirement recorded in the plan.
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
Course-provided image pairs and complete rewritten contracts remain
pending evaluation.

Results cover a small synthetic dataset. They do not prove production
readiness, universal prompt injection resistance, or legal accuracy.
