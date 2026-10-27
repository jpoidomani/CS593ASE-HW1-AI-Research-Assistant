# Round 2 improvement context

Review the current suite for weak, implementation-coupled, excessively mocked,
fragile, or redundant assertions. Strengthen a focused subset rather than
rewriting the suite. Add realistic integration tests using a programmatically
generated text PDF, temporary SQLite persistence, and accurate partial-page
warning behavior. Run a few isolated, reversible fault-injection experiments for
database retrieval, OpenAlex normalization, partial extraction warnings, and LLM
full-text grounding. Preserve final execution, coverage, mutations, and evaluation
without modifying production behavior or earlier evidence.
