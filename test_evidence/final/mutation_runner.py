"""Run one reversible runtime mutation against an existing behavioral test."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import services.database as database
import services.llm_service as llm_service


def corrupt_loaded_authors():
    original = database._row_to_paper

    def mutant(row):
        paper = original(row)
        paper.authors = []
        return paper

    return patch("services.database._row_to_paper", mutant)


def discard_openalex_abstract():
    return patch("services.paper_search.reconstruct_abstract", lambda value: None)


def erase_partial_extraction_count():
    original = database._row_to_paper

    def mutant(row):
        paper = original(row)
        paper.unreadable_page_count = 0
        return paper

    return patch("services.database._row_to_paper", mutant)


def remove_paper_text_from_llm_prompt():
    original = llm_service._create_response

    def mutant(instructions, prompt, max_output_tokens):
        altered = re.sub(
            r"<paper_text>.*?</paper_text>",
            "<paper_text>\n</paper_text>",
            prompt,
            flags=re.DOTALL,
        )
        return original(instructions, altered, max_output_tokens)

    return patch("services.llm_service._create_response", mutant)


EXPERIMENTS = {
    "database": (
        corrupt_loaded_authors,
        "tests/test_database.py::test_save_and_get_paper_round_trip",
    ),
    "openalex": (
        discard_openalex_abstract,
        "tests/test_paper_search.py::test_search_normalizes_openalex_result",
    ),
    "warning": (
        erase_partial_extraction_count,
        "tests/test_integration.py::test_persisted_real_pdf_counts_drive_partial_extraction_warning",
    ),
    "llm": (
        remove_paper_text_from_llm_prompt,
        "tests/test_llm_service.py::test_generate_summary_builds_grounded_request",
    ),
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in EXPERIMENTS:
        choices = ", ".join(EXPERIMENTS)
        print(f"Usage: mutation_runner.py <{choices}>")
        return 2

    patch_factory, test_node = EXPERIMENTS[sys.argv[1]]
    with patch_factory():
        return int(pytest.main(["-q", test_node]))


if __name__ == "__main__":
    raise SystemExit(main())
