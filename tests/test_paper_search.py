"""Tests for OpenAlex searching and normalization."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
import requests

from services.paper_search import OpenAlexError, reconstruct_abstract, search_papers


def test_reconstruct_abstract_orders_words_by_position():
    inverted = {"testing": [2], "AI": [0], "assisted": [1, 3]}

    assert reconstruct_abstract(inverted) == "AI assisted testing assisted"


@pytest.mark.parametrize("value", [None, {}, [], {"word": "not-a-list"}])
def test_reconstruct_abstract_returns_none_for_unusable_input(value):
    assert reconstruct_abstract(value) is None


def test_search_empty_query_does_not_make_request(monkeypatch):
    request = Mock()
    monkeypatch.setattr("services.paper_search.requests.get", request)

    assert search_papers("   ") == []
    request.assert_not_called()


def test_search_normalizes_openalex_result(monkeypatch):
    response = Mock()
    response.json.return_value = {
        "results": [
            {
                "id": "https://openalex.org/W1",
                "doi": "https://doi.org/10.1/test",
                "title": "Testing with Agents",
                "authorships": [
                    {"author": {"display_name": "Ada Lovelace"}},
                    {"author": None},
                ],
                "publication_year": 2025,
                "abstract_inverted_index": {"Useful": [0], "work": [1]},
                "primary_location": {"landing_page_url": "https://primary"},
                "best_oa_location": {"pdf_url": "https://example/paper.pdf"},
            }
        ]
    }
    monkeypatch.setattr("services.paper_search.requests.get", Mock(return_value=response))
    monkeypatch.setenv("OPENALEX_API_KEY", "test-key")

    papers = search_papers(" agent testing ", limit=100)

    assert len(papers) == 1
    assert papers[0].title == "Testing with Agents"
    assert papers[0].authors == ["Ada Lovelace"]
    assert papers[0].abstract == "Useful work"
    assert papers[0].paper_url == "https://doi.org/10.1/test"
    assert papers[0].pdf_url == "https://example/paper.pdf"
    requests.get.assert_called_once_with(
        "https://api.openalex.org/works",
        params=pytest.approx({}) if False else {
            "search": "agent testing",
            "per_page": 25,
            "select": pytest.importorskip("services.paper_search").RESULT_FIELDS,
            "api_key": "test-key",
        },
        timeout=15,
    )
    response.raise_for_status.assert_called_once()


def test_search_uses_fallbacks_for_sparse_result(monkeypatch):
    response = Mock()
    response.json.return_value = {
        "results": [
            {
                "id": "W2",
                "title": None,
                "authorships": "invalid",
                "publication_year": "2024",
                "primary_location": None,
                "best_oa_location": {"landing_page_url": "https://landing"},
            },
            "not-a-dictionary",
        ]
    }
    monkeypatch.setattr("services.paper_search.requests.get", Mock(return_value=response))

    papers = search_papers("topic", limit=0)

    assert len(papers) == 1
    assert papers[0].title == "Untitled paper"
    assert papers[0].authors == []
    assert papers[0].publication_year is None
    assert papers[0].paper_url == "https://landing"


@pytest.mark.parametrize(
    ("side_effect", "json_value", "message"),
    [
        (requests.Timeout("late"), None, "could not be reached"),
        (None, ValueError("bad json"), "unreadable response"),
    ],
)
def test_search_translates_request_and_json_errors(
    monkeypatch, side_effect, json_value, message
):
    if side_effect:
        request = Mock(side_effect=side_effect)
    else:
        response = Mock()
        response.json.side_effect = json_value
        request = Mock(return_value=response)
    monkeypatch.setattr("services.paper_search.requests.get", request)

    with pytest.raises(OpenAlexError, match=message):
        search_papers("topic")


@pytest.mark.parametrize("payload", [{}, {"results": {}}, {"results": None}])
def test_search_rejects_unexpected_payload(monkeypatch, payload):
    response = Mock()
    response.json.return_value = payload
    monkeypatch.setattr("services.paper_search.requests.get", Mock(return_value=response))

    with pytest.raises(OpenAlexError, match="unexpected response"):
        search_papers("topic")


def test_reconstruct_abstract_ignores_invalid_words_and_positions():
    inverted = {
        123: [0],
        "valid": ["zero", 1],
        "also": [0],
        "invalid-list": "not a list",
    }
    assert reconstruct_abstract(inverted) == "also valid"


def test_search_falls_back_to_primary_pdf_and_openalex_page(monkeypatch):
    response = Mock()
    response.json.return_value = {
        "results": [{
            "id": "https://openalex.org/W9",
            "title": "Fallback locations",
            "authorships": [],
            "primary_location": {"pdf_url": "https://primary.test/paper.pdf"},
            "best_oa_location": None,
        }]
    }
    monkeypatch.setattr("services.paper_search.requests.get", Mock(return_value=response))
    paper = search_papers("fallback")[0]
    assert paper.paper_url == "https://openalex.org/W9"
    assert paper.pdf_url == "https://primary.test/paper.pdf"
