# Course image evaluation

Three course-provided image pairs were analyzed using GPT-4o for
transcription and GPT-6 Luna for both agents.

Source:
https://drive.google.com/drive/folders/1JGZmR0UiJLvs1yxoh6VhWUnfm8FaidSw

| Output | Trace ID | Dashboard duration |
| --- | --- | --- |
| case_1_initial.json | `992488d2533fb0499092aba60d869831` | 23.70 s |
| case_1_scope_review.json | `eb0086bd3f4f95cdad10253b9ad832ca` | 19.43 s |
| case_2.json | `b390327a655672fafaf5cded3436d035` | 15.23 s |
| case_3.json | `991a4e9227ab1ce76b48fa3219db8e42` | 14.19 s |

The initial case 1 contextual map incorrectly inferred partial scope
from the amendment title and the absence of a full-replacement statement.
The initial output is preserved as evidence of that limitation.

After prompt refinement, case 1 was rerun. Its contextual map and report
consistently describe replacement scope as uncertain while retaining
the supported changes in sections 1, 2, 3, 4, 5, and 7.

The case 1 report also identifies the disappearance of the express
non-transferability restriction, which is not listed in the course's
expected-differences document.

Cases 2 and 3 contain the changes listed in the course reference.
They were executed before the final scope-classification refinement.

Trace screenshots confirm remote trace presence and the visible workflow
stages. They do not establish complete transcription fidelity or verification
of every generation's model metadata.

Durations are individual observations, not benchmark averages.
These results do not establish general accuracy on arbitrary contracts.
