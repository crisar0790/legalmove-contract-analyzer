# Initial model selection

## Selected configuration

- Vision: `gpt-4o`, preserving the requirement recorded in the project plan.
- Contextualization and extraction: `gpt-6.1-sol`.
- Lower-cost evaluation candidate: `gpt-6-luna`.

This is an initial selection, not a measured quality comparison.

## Lifecycle constraint

OpenAI lists GPT-4o as deprecated, with API removal scheduled for
January 14, 2027. Its recommended replacement is GPT-6 Luna.

Replacing the required vision model needs clarification against the
assignment requirements.

## Evaluation criteria

Compare transcription accuracy, section alignment, additions, explicit
deletions, modifications, false positives, omissions, structured output
validity, latency, and measured token usage.

Check amounts, currencies, dates, negations, and clause identifiers
against manually prepared references.

Record model identifiers, prompt versions, settings, and execution dates.
Include reasoning tokens in cost calculations when applicable.

## Sources

- https://developers.openai.com/api/docs/models/gpt-4o
- https://developers.openai.com/api/docs/models/gpt-6.1-sol
- https://developers.openai.com/api/docs/models/gpt-6-luna
- https://developers.openai.com/api/docs/deprecations
