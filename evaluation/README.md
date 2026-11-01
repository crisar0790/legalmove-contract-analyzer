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
- Complete rewritten contracts with implicit wording changes.
- A provision absent from an explicitly complete revised version.
- Uncertain document scope.
- Renumbering without substantive changes.

These cases isolate agent behavior from image transcription.
They do not replace the two required image pairs.

Review the contextual map and final report against each case's criteria.
Matching section identifiers alone does not demonstrate factual accuracy
or completeness.

## Status and execution policy

The initial five-case evaluation passed its 13 prepared criteria.
The suite was subsequently expanded to nine cases and 29 criteria.

The latest reviewed run is `semantic_runs/20261101T195330479288Z/`.
All 29 prepared criteria passed review of the contextual maps and final
reports. The no-change map adds unnecessary scope uncertainty, although
its alignment and final report are correct. Trace inspection for this
semantic run remains pending.

The initial image-based evaluation used GPT-4o for transcription and
GPT-6.1 Sol for both agents. Its evidence is stored in `report.json`,
`runs/`, and `../outputs/examples/`. These artifacts represent the initial
baseline, not the final GPT-6 Luna configuration.

A subsequent clean-checkout verification ran both image pairs through
the complete CLI pipeline using GPT-4o and GPT-6 Luna. Both reports were
manually reviewed, and their Langfuse traces and configured models were
confirmed. See [evaluation notes](../docs/evaluation.md) for trace IDs
and observed durations.

The three course-provided image pairs were executed through the CLI.
Their reports contain the changes listed in the course reference.
Case 1 additionally identifies the disappearance of an express
non-transferability restriction.

Case 1 was rerun after correcting an unsupported partial-scope
classification. Evidence and review limitations are recorded in
[the course evaluation](course_runs/20261101/README.md).

Offline tests exercise implementation behavior with simulated responses.
Real evaluation is separate, opt-in, and consumes API usage.

Record actual outputs, configuration, trace identifiers, and review findings
when running the evaluation. Never replace observed results with expected
answers.
