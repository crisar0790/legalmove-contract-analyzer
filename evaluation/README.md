# Evaluation

## Image-based evaluation

The required simple and complex document pairs are stored in
`data/test_contracts/`. Their source transcripts and expected facts were
prepared before model execution.

Image-based evaluation must run the complete pipeline, including vision
and Langfuse tracing.

## Additional semantic cases

`semantic_cases.json` contains text-based cases for evaluating the agents:

- No substantive changes.
- A partial amendment that preserves omitted clauses.
- Different amendment and original numbering.
- An unreadable amended amount.
- An instruction embedded in document content.

These cases isolate agent behavior from image transcription.
They do not replace the two required image pairs.

Review the contextual map and final report against each case's criteria.
Matching section identifiers alone does not demonstrate factual accuracy
or completeness.

## Status and execution policy

The five additional semantic cases were evaluated with GPT-6 Luna using
the refined contextualization prompt. Manual review confirmed all 13
prepared criteria. Execution evidence is stored in `semantic_runs/`.

The initial image-based evaluation used GPT-4o for transcription and
GPT-6.1 Sol for both agents. Its evidence is stored in `report.json`,
`runs/`, and `../outputs/examples/`. These artifacts represent the initial
baseline, not the final GPT-6 Luna configuration.

A subsequent clean-checkout verification ran both image pairs through
the complete CLI pipeline using GPT-4o and GPT-6 Luna. Both reports were
manually reviewed, and their Langfuse traces and configured models were
confirmed. See [evaluation notes](../docs/evaluation.md) for trace IDs
and observed durations.

The three course-provided image pairs have not yet been evaluated.
Existing results do not establish performance on complete rewritten
contracts or implicit clause removals.

Offline tests exercise implementation behavior with simulated responses.
Real evaluation is separate, opt-in, and consumes API usage.

Record actual outputs, configuration, trace identifiers, and review findings
when running the evaluation. Never replace observed results with expected
answers.
