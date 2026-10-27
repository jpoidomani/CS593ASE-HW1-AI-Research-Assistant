# Initial Test Suite Evaluation

## Generation summary

The initial suite contains 59 collected pytest cases:

- 12 SQLite persistence cases
- 13 OpenAlex search and normalization cases
- 10 PDF validation, extraction, metadata, and storage cases
- 9 PDF download and attachment cases
- 13 OpenAI validation, request construction, and error cases
- 2 basic Streamlit workflow cases

Temporary pytest directories isolate SQLite and uploaded-file operations. The
autouse fixture removes API credentials, and all OpenAlex, OpenAI, and PDF
download requests are mocked.

## Execution result

- Passed: 57
- Failed: 2
- Errors: 0
- Total collected: 59

Both failures are incorrect generated tests, not application defects. Streamlit
resolves relative `AppTest.from_file` paths against the test file, so `"app.py"`
incorrectly referred to `tests/app.py`. Consequently, the app was never imported.
The initial tests and results are intentionally left unchanged for the baseline.

## Initial coverage

Coverage.py reported 95.60% statement/line coverage (326 of 341 statements) and
94.68% branch coverage (89 of 94 branches) for the modules that were imported.
Its combined line-and-branch metric was 95.40%, displayed as 95% in the terminal.

| Module | Statement/line coverage | Branch coverage |
| --- | ---: | ---: |
| `models/paper.py` | 100.00% | N/A |
| `services/database.py` | 96.10% | 95.45% |
| `services/llm_service.py` | 88.24% | 100.00% |
| `services/paper_content.py` | 100.00% | 100.00% |
| `services/paper_search.py` | 100.00% | 95.45% |
| `services/pdf_processor.py` | 93.55% | 87.50% |
| `app.py` | Not measured | Not measured |

The high overall percentage is incomplete because both Streamlit tests failed
before importing `app.py`. It should not be interpreted as 95% coverage of the
whole application.

## Weaknesses and incorrect assumptions

- Both Streamlit tests use an incorrect relative entrypoint and test no UI behavior.
- Most service tests are isolated unit tests with heavily mocked collaborators;
  cross-service integration is largely untested.
- PDF extraction uses fake readers rather than a real generated PDF, so compatibility
  with actual `pypdf` parsing is not demonstrated.
- Several assertions mirror implementation details, such as exact HTTP keyword
  arguments and exact OpenAI request construction, which may be brittle.
- Database update tests do not verify timestamp behavior or database constraints
  beyond duplicate external IDs.
- Only three OpenAI SDK error classes are exercised.
- No clearly redundant cases were identified, although several parameterized
  validation cases exercise closely related paths.

## Important uncovered functionality

- All Streamlit rendering and workflows in `app.py`, including search success and
  failure, saving, upload review, library selection, PDF attachment/download,
  summary caching/generation, and question answering.
- The default database path and the defensive post-insert failure branch.
- OpenAI handling for unavailable models, bad requests, generic API status errors,
  and generic API errors.
- Several PDF metadata exception/fallback branches, parser error categories,
  title fallback behavior, author delimiter variants, and year boundary behavior.
- A malformed OpenAlex abstract position branch.

## Fault detection

No genuine existing application bugs were detected by the initial suite. The two
failures are caused by an incorrect generated test path. There were no dependency
or runtime environment errors in the preserved test run.
