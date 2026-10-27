# AI Research Assistant

AI Research Assistant is a small Streamlit web application for finding, saving,
uploading, and analyzing research papers. It was built for a graduate
AI-Assisted Software Engineering course assignment and intentionally favors a
simple, understandable architecture over production-level complexity.

## Features

1. **Search for papers** by keyword or research topic using OpenAlex. Results
   include the title, authors, publication year, abstract, and paper link when
   available.
2. **Save papers to a local library** backed by SQLite. Saved records remain
   available after browser refreshes and application restarts.
3. **Upload PDF papers** and extract their text and available metadata with
   `pypdf`. Users review and correct the title, authors, publication year, and
   abstract before saving.
4. **Generate paper summaries** with the OpenAI Responses API. Summaries use
   extracted full paper text and are cached in SQLite.
5. **Ask questions about a paper** in natural language. Answers are grounded in
   the selected paper's extracted text and acknowledge when information is not
   present.

For OpenAlex papers that do not initially have full text, the application can
try to download an available open-access PDF or let the user attach the correct
PDF to the existing library record.

## Technology stack

- Python 3.11 or newer
- Streamlit for the web interface and server-side application logic
- SQLite through Python's built-in `sqlite3` module
- OpenAlex REST API for scholarly paper search
- `pypdf` for PDF text and metadata extraction
- Official OpenAI Python SDK and Responses API for summaries and questions

## Setup

Clone or download the project, open a terminal in its root directory, and create
a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell, activate it with:

```powershell
.venv\Scripts\Activate.ps1
```

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

Create a local environment file from the provided template:

```bash
cp .env.example .env
```

On Windows PowerShell, use:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and add your OpenAI API key:

```dotenv
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

`OPENAI_MODEL` is optional and defaults to `gpt-4o-mini`. An OpenAlex API key
is also optional for light use:

```dotenv
OPENALEX_API_KEY=
```

Do not commit `.env` or place credentials directly in source files. The supplied
`.gitignore` excludes `.env`, local databases, uploaded PDFs, virtual
environments, private-key files, and generated Python files.

## Run the application

With the virtual environment active, launch the application with:

```bash
streamlit run app.py
```

Streamlit normally opens `http://localhost:8501` automatically.

The application creates `data/research_assistant.db` when first started and
stores uploaded or downloaded PDFs under `data/uploads/`. Both are local,
generated data and are excluded from Git.

## Project structure

```text
.
├── app.py                       # Streamlit interface and user workflows
├── models/
│   └── paper.py                 # Shared Paper data model
├── services/
│   ├── database.py              # SQLite schema and paper persistence
│   ├── paper_search.py          # OpenAlex search and response normalization
│   ├── pdf_processor.py         # PDF validation, extraction, and local storage
│   ├── paper_content.py         # Open-access download and PDF attachment
│   └── llm_service.py           # OpenAI summaries and paper questions
├── data/
│   └── uploads/                 # Generated local PDF storage
├── tests/                       # Automated unit, workflow, and integration tests
├── test_evidence/               # Preserved Homework 2 results and evaluations
├── pytest.ini                   # Pytest configuration
├── requirements.txt             # Python dependencies
└── .env.example                 # Safe environment-variable template
```

## Homework 2: automated testing

The Homework 2 suite contains 81 automated tests covering SQLite persistence,
OpenAlex response normalization, PDF processing and attachment, OpenAI request
validation and error handling, and important Streamlit workflows. It also
includes integration tests that generate a real text-based PDF, extract its
content, persist the result to SQLite, and verify the partial-extraction warning.

The suite uses:

- `pytest` as the test runner
- `pytest-cov` and Coverage.py for statement and branch coverage
- Streamlit `AppTest` for simulated application workflows
- `unittest.mock` and pytest fixtures to isolate external services and local data

### Install testing dependencies

The testing tools are included in `requirements.txt`. From the project root,
create and activate a virtual environment as described in Setup, then run:

```bash
python -m pip install -r requirements.txt
```

No `.env` file or API key is needed to execute the tests.

### Run the final test suite

With the virtual environment activated, run exactly:

```bash
python -m pytest
```

To reproduce the final statement and branch coverage measurement, run exactly:

```bash
python -m pytest --cov=app --cov=models --cov=services --cov-branch --cov-report=term-missing --cov-report=json:test_evidence/final/coverage.json --junitxml=test_evidence/final/junit.xml
```

That coverage command writes the machine-readable final reports again. The
committed versions record the submission run: 81 passed, 88.54% complete-app
statement coverage, and 88.73% complete-app branch coverage.

### Test and evidence layout

The `tests/` directory contains shared isolation fixtures plus focused tests for
the Streamlit interface, database, OpenAlex search, PDF processing and content
acquisition, LLM service, and cross-component integration. Tests use temporary
SQLite databases and temporary directories. OpenAlex, OpenAI, and PDF-download
requests are mocked, so tests never use the real application database, uploaded
files, API credentials, or live OpenAI/OpenAlex access.

The `test_evidence/` directory preserves the Homework 2 progression:

- `test_evidence/initial/` contains the original generated baseline, including
  its two failing Streamlit tests and initial coverage.
- `test_evidence/round1/` contains the first improvement results after correcting
  those failures and expanding requirement-focused coverage.
- `test_evidence/final/` contains the final Round 2 execution, coverage,
  evaluation, and controlled fault-injection results.

Each evidence directory includes its exact reproduction command, execution
results, machine-readable coverage and JUnit data, and an evaluation summary.

## Important limitations

- Scanned or image-only PDFs are not supported because the application does not
  perform OCR.
- PDF metadata and local extraction heuristics can be inaccurate, so users must
  review and complete the extracted fields before saving.
- Some publisher websites prevent automated PDF downloads. The PDF can be
  attached manually to the existing OpenAlex record in that case.
- Papers over 250,000 extracted characters are rejected for LLM analysis rather
  than silently truncated.
- Generated answers are shown for the current Streamlit session but are not
  stored in the database. Generated summaries are stored.
- LLM output can be imperfect even with full-text grounding and should be
  checked against the original paper.

## Assignment submission reminder

In addition to the GitHub repository, the assignment requires a short demo video
showing search, save, PDF upload, summary generation, and paper question
answering. It also requires a reflection report about the coding-agent experience,
including screenshots of relevant interactions and corrections.
