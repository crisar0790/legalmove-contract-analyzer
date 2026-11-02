# Contract image fixtures

This directory contains two fictional document pairs for evaluating
LegalMove. Each pair consists of an original contract and a partial
amendment, supplied as PNG images.

The documents contain synthetic information prepared for testing.

## Files

| Case | Original | Amendment |
| --- | --- | --- |
| Simple | `simple_original.png` | `simple_amendment.png` |
| Complex | `complex_original.png` | `complex_amendment.png` |

The `reference/` directory contains manually prepared source transcriptions
and expected findings. These references support evaluation; the application
does not receive them when analyzing images.

## Simple case

The original is a digital services agreement. Its amendment replaces
clause 3, effective July 1, 2026:

- Monthly fees increase from USD 500 to USD 650.
- The monthly payment deadline changes from day 5 to day 10.
- Other clauses are ratified without modification.

The expected changed section is clause 3.

## Complex case

The original is a software license agreement. Its amendment takes effect
on July 1, 2026 and introduces three types of change:

- Modification of clause 2: permitted territory expands from Argentina
  to Argentina, Chile, and Uruguay.
- Explicit deletion of clause 4: the prohibition on using the platform
  for internal staff training is removed.
- Addition of clause 7: remote support is available Monday through Friday,
  from 09:00 to 18:00 Argentina time, with a maximum first-response time
  of 24 business hours.

Other clauses remain unchanged, including the annual price of USD 1200,
its January 15 payment deadline, and the original 2026 contract term.

The expected changed sections are clauses 2, 4, and 7.

## Running the examples

From the repository root, with dependencies and credentials configured:

```bash
mkdir -p outputs

python -m src.main \
  data/test_contracts/simple_original.png \
  data/test_contracts/simple_amendment.png \
  --output outputs/simple.json

python -m src.main \
  data/test_contracts/complex_original.png \
  data/test_contracts/complex_amendment.png \
  --output outputs/complex.json
```

These commands consume OpenAI API usage and send traces to Langfuse.

The CLI also accepts other JPEG and PNG image paths. Each input represents
one image; PDF ingestion and multi-page assembly are not implemented.

These fictional fixtures use partial amendments. Separate evaluations
cover complete revised versions and uncertain document scope.
See [evaluation instructions](../../evaluation/README.md).
