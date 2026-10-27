# Final Evaluation After Improvement Round 2

## Round 2 strategy

Round 2 emphasized test correctness, behavioral assertions, realistic integration,
and fault detection rather than adding tests solely to raise coverage. Five
existing tests were strengthened and two focused integration tests were added.
No tests were removed, and no production file was changed.

Strengthened assertions include:

- Database updates are reloaded from SQLite and checked for changed and preserved
  fields instead of locking in incidental surrounding whitespace.
- Search saving verifies authors, year, abstract, and external ID in persisted
  state rather than checking only the title.
- OpenAlex HTTP assertions use an explicit mock and compare the documented request
  contract without the previous dead conditional/import expression.
- PDF hashing checks the exact SHA-256 digest instead of only its length.
- LLM tests require the exact complete `<paper_text>` block, and the Q&A test
  separately verifies the cleaned question and full paper content.

The integration tests programmatically generate a valid two-page PDF using
`pypdf`: page one contains real extractable text and page two is blank. They run
the actual PDF parser, persist all extracted fields to temporary SQLite storage,
reload them, and verify metadata, abstract, full text, page count, and unreadable
page count. The second test executes Streamlit and checks the exact partial-PDF
warning derived from those persisted counts.

## Final execution

- Passed: 81
- Failed: 0
- Errors: 0
- Total collected: 81

## Coverage by module

| Module | Statement/line coverage | Branch coverage |
| --- | ---: | ---: |
| `app.py` | 66.09% | 68.75% |
| `models/paper.py` | 100.00% | N/A |
| `services/database.py` | 100.00% | 100.00% |
| `services/llm_service.py` | 100.00% | 100.00% |
| `services/paper_content.py` | 100.00% | 100.00% |
| `services/paper_search.py` | 100.00% | 100.00% |
| `services/pdf_processor.py` | 100.00% | 95.83% |

Complete-application coverage is 88.54% statements (456 of 515) and 88.73%
branches (126 of 142). Coverage.py's combined metric is 88.58%, displayed as 89%.

For the comparable models-and-services scope, coverage is 100% statements (341
of 341) and 98.94% branches (93 of 94). Round 2 intentionally did not add
low-value cases merely to move these percentages.

## Iteration comparison

| Measure | Initial | Round 1 | Final |
| --- | ---: | ---: | ---: |
| Tests passed | 57 | 79 | 81 |
| Tests failed | 2 | 0 | 0 |
| Tests errored | 0 | 0 | 0 |
| Complete-app statement coverage | Not available | 88.54% | 88.54% |
| Complete-app branch coverage | Not available | 88.73% | 88.73% |
| Service/model statement coverage | 95.60% | 100.00% | 100.00% |
| Service/model branch coverage | 94.68% | 98.94% | 98.94% |
| Real-PDF integration | No | No | Yes |
| Controlled faults detected | Not evaluated | Not evaluated | 4 of 4 |

The unchanged Round 1-to-final coverage is expected: the new tests exercise
already-covered statements through more realistic component combinations. Their
value is stronger correctness and fault-detection evidence, not new lines.

## Fault-detection capability

Four isolated runtime mutations were attempted, and all four were killed by the
suite:

1. Corrupting authors during database retrieval failed the round-trip assertion.
2. Discarding reconstructed OpenAlex abstracts failed metadata normalization.
3. Erasing unreadable-page counts failed the real-PDF persistence/warning test.
4. Removing full paper text from the LLM prompt failed the grounding assertion.

Each mutant test exited with status 1. The unmodified versions of the same tests
then passed 4 of 4. Details and reproduction commands are in
`mutation_results.md` and `mutation_runner.py`.

These are deliberately injected faults, not genuine bugs. No genuine existing
application defect was detected in Round 2.

## Remaining limitations

- Streamlit's test harness does not provide a stable, practical file-uploader
  interaction for this suite, so the upload form itself remains untested at UI
  level. Actual PDF extraction is now covered through integration tests.
- Open-access download and manual attachment UI controls remain untested, though
  their service workflows are fully covered.
- Some UI failure branches for duplicate saves, persistence failures, summary
  failures, and missing records remain uncovered.
- AppTest interactions still use some generated widget keys.
- OpenAI and OpenAlex are intentionally mocked; live service availability and
  third-party response changes are outside deterministic automated testing.
- One low-value PDF creation-date fallback branch remains uncovered.
- Fault injection is representative rather than exhaustive and is not a full
  mutation-testing framework.
