# Initial generation context

Generate an initial pytest suite for the existing Python/Streamlit AI Research
Assistant. Test normal behavior, edge cases, and error handling in the database,
OpenAlex search, PDF processing, paper-content, and OpenAI service modules, plus
basic Streamlit workflows where practical. Use meaningful assertions. Keep tests
away from the real database, uploads, credentials, and network by using temporary
paths and mocks. Measure line and branch coverage with pytest-cov. Do not change
application behavior to make tests pass, and do not perform improvement rounds.
