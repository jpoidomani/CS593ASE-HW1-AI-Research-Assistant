"""Streamlit workflow tests using Streamlit's AppTest harness."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from streamlit.testing.v1 import AppTest

from models.paper import Paper
from services.database import get_paper, list_papers, save_paper
from services.paper_search import OpenAlexError


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def run_app() -> AppTest:
    return AppTest.from_file(APP_PATH, default_timeout=10).run()


def test_app_starts_with_expected_navigation_and_empty_library():
    app = run_app()
    assert not app.exception
    assert app.title[0].value == "AI Research Assistant"
    assert [tab.label for tab in app.tabs] == [
        "Search Papers", "Upload PDF", "Saved Library"
    ]
    assert any("library is empty" in info.value for info in app.info)


def test_empty_search_shows_validation_warning():
    app = run_app()
    app.text_input[0].set_value("   ")
    app.button(key="FormSubmitter:paper_search_form-Search").click().run()
    assert not app.exception
    assert any("Enter keywords" in warning.value for warning in app.warning)


def test_search_displays_result_and_saves_it_to_library(monkeypatch):
    result = Paper(
        title="Generated Tests for AI Systems", source_type="openalex",
        external_id="W123", authors=["Ada Lovelace"], publication_year=2026,
        abstract="An abstract about generated tests.",
        paper_url="https://example.test/paper",
    )
    search = Mock(return_value=[result])
    monkeypatch.setattr("services.paper_search.search_papers", search)
    app = run_app()
    app.text_input[0].set_value("agent testing")
    app.button(key="FormSubmitter:paper_search_form-Search").click().run()

    assert not app.exception
    assert any(result.title == heading.value for heading in app.subheader)
    assert any("Ada Lovelace" in text.value for text in app.markdown)
    assert any("2026" in text.value for text in app.markdown)
    assert any("generated tests" in text.value for text in app.markdown)
    search.assert_called_once_with("agent testing")

    app.button(key="save_W123").click().run()
    assert any("saved to your library" in success.value for success in app.success)
    stored = list_papers()
    assert len(stored) == 1
    assert stored[0].title == result.title
    assert stored[0].authors == result.authors
    assert stored[0].publication_year == result.publication_year
    assert stored[0].abstract == result.abstract
    assert stored[0].external_id == result.external_id


def test_search_reports_no_results(monkeypatch):
    monkeypatch.setattr("services.paper_search.search_papers", Mock(return_value=[]))
    app = run_app()
    app.text_input[0].set_value("unknown topic")
    app.button(key="FormSubmitter:paper_search_form-Search").click().run()
    assert not app.exception
    assert any("No papers were found" in info.value for info in app.info)


def test_search_displays_openalex_failure(monkeypatch):
    monkeypatch.setattr(
        "services.paper_search.search_papers",
        Mock(side_effect=OpenAlexError("OpenAlex unavailable for testing")),
    )
    app = run_app()
    app.text_input[0].set_value("topic")
    app.button(key="FormSubmitter:paper_search_form-Search").click().run()
    assert not app.exception
    assert any("OpenAlex unavailable" in error.value for error in app.error)


def test_library_explains_that_full_text_is_required():
    save_paper(Paper(
        title="Metadata-only paper", source_type="openalex",
        external_id="W-META", authors=["Researcher"],
    ))
    app = run_app()
    assert not app.exception
    assert any("Full paper text is not available" in w.value for w in app.warning)
    assert any("Upload the corresponding PDF" in i.value for i in app.info)
    assert not any(button.label == "Generate Summary" for button in app.button)


def test_library_shows_partial_extraction_warning_and_cached_summary():
    save_paper(Paper(
        title="Partially readable paper", source_type="upload",
        external_id="upload:partial", authors=["Researcher"],
        extracted_text="Readable paper text", page_count=5,
        unreadable_page_count=2, summary="Previously generated summary.",
    ))
    app = run_app()
    assert not app.exception
    assert any("2 of 5 page(s)" in w.value for w in app.warning)
    assert any("Previously generated summary" in m.value for m in app.markdown)
    assert any("no new API request" in c.value for c in app.caption)


def test_library_generates_and_persists_summary(monkeypatch):
    saved = save_paper(Paper(
        title="Full-text paper", source_type="upload", external_id="upload:full",
        authors=["Researcher"], extracted_text="Complete extracted text",
        page_count=1,
    ))
    generate = Mock(return_value="A grounded generated summary.")
    monkeypatch.setattr("services.llm_service.generate_summary", generate)
    app = run_app()
    app.button(key=f"summary_{saved.id}").click().run()
    assert not app.exception
    assert any("grounded generated summary" in m.value for m in app.markdown)
    assert any("generated and saved" in s.value for s in app.success)
    generate.assert_called_once_with("Complete extracted text")
    assert get_paper(saved.id).summary == "A grounded generated summary."


def test_library_answers_question_from_selected_paper(monkeypatch):
    saved = save_paper(Paper(
        title="Questionable paper", source_type="upload",
        external_id="upload:question", authors=["Researcher"],
        extracted_text="The paper says testing improved reliability.",
        page_count=1, summary="Existing summary",
    ))
    answer = Mock(return_value="Testing improved reliability.")
    monkeypatch.setattr("services.llm_service.answer_question", answer)
    app = run_app()
    question_input = next(
        item for item in app.text_input if item.label == "Question about this paper"
    )
    question_input.set_value("What improved?")
    app.button(key=f"FormSubmitter:question_form_{saved.id}-Ask Question").click().run()
    assert not app.exception
    assert any("Testing improved reliability" in m.value for m in app.markdown)
    answer.assert_called_once_with(
        "The paper says testing improved reliability.", "What improved?"
    )


def test_library_displays_question_validation_error():
    saved = save_paper(Paper(
        title="Question validation paper", source_type="upload",
        external_id="upload:question-empty", authors=["Researcher"],
        extracted_text="Paper text", page_count=1, summary="Existing summary",
    ))
    app = run_app()
    app.button(key=f"FormSubmitter:question_form_{saved.id}-Ask Question").click().run()
    assert not app.exception
    assert any("Enter a question" in error.value for error in app.error)
