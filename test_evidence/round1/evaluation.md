# Improvement Round 1 Evaluation

## Strategy and changes

Round 1 used the original application requirements, the Homework 2 handout, and
the initial execution and coverage feedback. The two failing Streamlit tests now
resolve `app.py` from the project root with an absolute path. Their assertions
check navigation, empty-library guidance, and empty-search validation.

Eight additional Streamlit tests exercise search result rendering, saving to the
real temporary SQLite database, no-result and OpenAlex-error feedback, full-text
gating, partial-extraction warnings, cached and generated summaries, persisted
summary state, grounded questions, and question validation feedback.

Service additions cover configured/default database paths, the defensive
post-insert failure, every mapped OpenAI SDK error category, malformed OpenAlex
abstract positions and URL fallbacks, known PDF parser errors, broken PDF
metadata, filename title fallback, and supported author delimiters. Tests still
remove credentials, use temporary databases, and mock all external APIs.

## Execution result

- Passed: 79
- Failed: 0
- Errors: 0
- Total collected: 79

The initial suite had 57 passes and 2 failures among 59 cases. Round 1 corrected
both failures and added 20 cases.

## Coverage

| Module | Statement/line coverage | Branch coverage |
| --- | ---: | ---: |
| `app.py` | 66.09% | 68.75% |
| `models/paper.py` | 100.00% | N/A |
| `services/database.py` | 100.00% | 100.00% |
| `services/llm_service.py` | 100.00% | 100.00% |
| `services/paper_content.py` | 100.00% | 100.00% |
| `services/paper_search.py` | 100.00% | 100.00% |
| `services/pdf_processor.py` | 100.00% | 95.83% |

Across the complete measured application, statement coverage is 88.54% (456 of
515 statements) and branch coverage is 88.73% (126 of 142 branches). Coverage.py's
combined metric is 88.58%, displayed as 89%.

The numerical overall percentage is lower than the initial report because
`app.py` is now successfully measured and adds 174 statements. On the initial
scope of models and services, statement coverage improved from 95.60% to 100%,
and branch coverage improved from 94.68% to 98.94% (93 of 94 branches).

## Assertion quality

The new Streamlit cases assert user-visible messages, rendered paper metadata,
absence or presence of actions, collaborator inputs, and persisted database
effects. They therefore check application requirements rather than merely
confirming that the script launches. Service error tests assert the application's
user-facing error translations rather than raw SDK exceptions.

Remaining weaknesses:

- The PDF upload workflow is not exercised because AppTest does not currently
  provide a practical file-uploader interaction in this suite.
- Open-access download and manual attachment UI branches remain uncovered,
  although their underlying service is fully covered.
- UI error branches for duplicate saves, persistence failures, summary failures,
  and missing records remain uncovered.
- AppTest cases use Streamlit-generated widget keys, which couples them somewhat
  to the current UI implementation.
- API and LLM success behavior remains mocked; the tests verify integration
  contracts but not live third-party services.
- PDF extraction still uses fake reader objects rather than a real PDF fixture.
- One low-value PDF year-fallback branch remains uncovered.

## Correctness and fault detection

No genuine existing application bugs were detected in Round 1. During development,
one new PDF test incorrectly assumed that a metadata newline survived whitespace
normalization as an author separator. The test input was corrected to use the
supported semicolon delimiter; no application change was made.

The final Round 1 suite has no known incorrect tests or failing environment
assumptions. No application functionality or requirement was changed.
