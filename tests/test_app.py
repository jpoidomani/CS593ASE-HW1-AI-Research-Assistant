"""Basic Streamlit workflow tests using Streamlit's AppTest harness."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest


def test_app_starts_with_expected_navigation_and_empty_library():
    app = AppTest.from_file("app.py", default_timeout=10).run()

    assert not app.exception
    assert app.title[0].value == "AI Research Assistant"
    assert [tab.label for tab in app.tabs] == [
        "Search Papers",
        "Upload PDF",
        "Saved Library",
    ]
    assert any("library is empty" in info.value for info in app.info)


def test_empty_search_shows_validation_warning():
    app = AppTest.from_file("app.py", default_timeout=10).run()

    app.text_input(key="Keywords or topic").set_value("   ")
    app.button(key="FormSubmitter:paper_search_form-Search").click().run()

    assert not app.exception
    assert any("Enter keywords" in warning.value for warning in app.warning)
