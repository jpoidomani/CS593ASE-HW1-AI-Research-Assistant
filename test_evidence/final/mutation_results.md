# Controlled Fault-Injection Results

All experiments used runtime `unittest.mock.patch` mutations from
`mutation_runner.py`. Each command ran in a fresh process, so production source
files were never edited and the patch was automatically restored on exit.

## Experiment 1: corrupted database retrieval

- Command: `.venv/bin/python test_evidence/final/mutation_runner.py database`
- Injected fault: replace every deserialized paper's authors with an empty list.
- Exercised test: `test_save_and_get_paper_round_trip`
- Result: **detected**, exit status 1.
- Failing assertion: expected `["Ada Lovelace", "Grace Hopper"]`, received `[]`.

## Experiment 2: lost OpenAlex abstract

- Command: `.venv/bin/python test_evidence/final/mutation_runner.py openalex`
- Injected fault: make abstract reconstruction always return `None`.
- Exercised test: `test_search_normalizes_openalex_result`
- Result: **detected**, exit status 1.
- Failing assertion: expected `"Useful work"`, received `None`.

## Experiment 3: erased partial-extraction count

- Command: `.venv/bin/python test_evidence/final/mutation_runner.py warning`
- Injected fault: deserialize `unreadable_page_count` as zero.
- Exercised test: `test_persisted_real_pdf_counts_drive_partial_extraction_warning`
- Result: **detected**, exit status 1.
- Failing assertion: expected one unreadable page, received zero. This prevents
  the accurate warning from being supported by persisted data.

## Experiment 4: omitted paper text from LLM prompt

- Command: `.venv/bin/python test_evidence/final/mutation_runner.py llm`
- Injected fault: remove all content between the `<paper_text>` delimiters before
  constructing the OpenAI request.
- Exercised test: `test_generate_summary_builds_grounded_request`
- Result: **detected**, exit status 1.
- Failing assertion: the exact full-text block was absent from the request input.

## Restoration verification

After the four isolated processes exited, the same four tests were run against
the normal implementation:

```text
....                                                                     [100%]
4 passed in 0.50s
```

These four failures are deliberate injected faults, not pre-existing application
bugs. The experiment harness initially needed its project-root import path fixed
before any mutation ran; that harness setup issue was not a test or application
failure.
