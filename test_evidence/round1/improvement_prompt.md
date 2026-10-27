# Round 1 improvement context

Correct the two initial Streamlit failures caused by resolving `app.py` relative
to `tests/`. Ensure the corrected tests execute the application and make
meaningful interface assertions. Use the original requirements and initial
coverage feedback to add focused tests for Streamlit workflows, database
validation and errors, PDF failures and partial-extraction warnings, OpenAlex
normalization and errors, and LLM configuration, validation, and API errors.
Keep external calls mocked and data isolated. Preserve Round 1 results separately,
do not change application functionality, and do not begin Round 2.
