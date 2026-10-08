"""Search and normalize research papers from the OpenAlex API."""

from __future__ import annotations

import os
from typing import Any

import requests

from models.paper import Paper


OPENALEX_WORKS_URL = "https://api.openalex.org/works"
RESULT_FIELDS = ",".join(
    [
        "id",
        "doi",
        "title",
        "authorships",
        "publication_year",
        "abstract_inverted_index",
        "primary_location",
        "best_oa_location",
    ]
)


class OpenAlexError(RuntimeError):
    """Raised when a paper search cannot be completed."""


def search_papers(query: str, limit: int = 10) -> list[Paper]:
    """Search OpenAlex and return results in the application's Paper format."""
    cleaned_query = query.strip()
    if not cleaned_query:
        return []

    params: dict[str, str | int] = {
        "search": cleaned_query,
        "per_page": max(1, min(limit, 25)),
        "select": RESULT_FIELDS,
    }
    api_key = os.getenv("OPENALEX_API_KEY")
    if api_key:
        params["api_key"] = api_key

    try:
        response = requests.get(OPENALEX_WORKS_URL, params=params, timeout=15)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as error:
        raise OpenAlexError("OpenAlex could not be reached. Please try again.") from error
    except ValueError as error:
        raise OpenAlexError("OpenAlex returned an unreadable response.") from error

    results = payload.get("results")
    if not isinstance(results, list):
        raise OpenAlexError("OpenAlex returned an unexpected response.")

    return [_paper_from_work(work) for work in results if isinstance(work, dict)]


def reconstruct_abstract(inverted_index: Any) -> str | None:
    """Convert an OpenAlex abstract inverted index into readable text."""
    if not isinstance(inverted_index, dict) or not inverted_index:
        return None

    positioned_words: list[tuple[int, str]] = []
    for word, positions in inverted_index.items():
        if not isinstance(word, str) or not isinstance(positions, list):
            continue
        for position in positions:
            if isinstance(position, int):
                positioned_words.append((position, word))

    if not positioned_words:
        return None
    positioned_words.sort(key=lambda item: item[0])
    return " ".join(word for _, word in positioned_words)


def _paper_from_work(work: dict[str, Any]) -> Paper:
    authors = []
    for authorship in work.get("authorships") or []:
        author = authorship.get("author") if isinstance(authorship, dict) else None
        name = author.get("display_name") if isinstance(author, dict) else None
        if name:
            authors.append(str(name))

    primary_location = work.get("primary_location") or {}
    best_oa_location = work.get("best_oa_location") or {}

    paper_url = (
        work.get("doi")
        or _location_value(primary_location, "landing_page_url")
        or _location_value(best_oa_location, "landing_page_url")
        or work.get("id")
    )
    pdf_url = _location_value(best_oa_location, "pdf_url") or _location_value(
        primary_location, "pdf_url"
    )

    return Paper(
        source_type="openalex",
        external_id=_string_or_none(work.get("id")),
        title=_string_or_none(work.get("title")) or "Untitled paper",
        authors=authors,
        publication_year=(
            work.get("publication_year")
            if isinstance(work.get("publication_year"), int)
            else None
        ),
        abstract=reconstruct_abstract(work.get("abstract_inverted_index")),
        paper_url=_string_or_none(paper_url),
        pdf_url=_string_or_none(pdf_url),
    )


def _location_value(location: Any, field: str) -> Any:
    return location.get(field) if isinstance(location, dict) else None


def _string_or_none(value: Any) -> str | None:
    return str(value) if value else None

