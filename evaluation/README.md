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

The additional semantic cases are prepared but not yet evaluated.
No passing results or quality metrics are claimed for them.

Offline tests exercise implementation behavior with simulated responses.
Real evaluation is separate, opt-in, and consumes API usage.

Record actual outputs, configuration, trace identifiers, and review findings
when running the evaluation. Never replace observed results with expected
answers.