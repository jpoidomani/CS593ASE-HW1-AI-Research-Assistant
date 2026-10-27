"""Tests for SQLite paper persistence."""

from __future__ import annotations

import sqlite3
from unittest.mock import Mock

import pytest

from models.paper import Paper
from services.database import (
    DEFAULT_DATABASE_PATH,
    get_database_path,
    get_paper,
    initialize_database,
    list_papers,
    save_paper,
    update_paper,
)


def make_paper(**changes) -> Paper:
    values = {
        "title": "Agent-Assisted Testing",
        "source_type": "openalex",
        "authors": ["Ada Lovelace", "Grace Hopper"],
        "publication_year": 2026,
        "abstract": "A study of generated software tests.",
        "external_id": "https://openalex.org/W123",
        "paper_url": "https://doi.org/10.1000/example",
    }
    values.update(changes)
    return Paper(**values)


def test_save_and_get_paper_round_trip(tmp_path):
    database_path = tmp_path / "nested" / "papers.db"

    saved = save_paper(make_paper(), database_path)
    loaded = get_paper(saved.id, database_path)

    assert database_path.exists()
    assert loaded == saved
    assert loaded.authors == ["Ada Lovelace", "Grace Hopper"]
    assert loaded.created_at is not None
    assert loaded.updated_at is not None


def test_list_papers_returns_newest_id_first(tmp_path):
    database_path = tmp_path / "papers.db"
    first = save_paper(make_paper(external_id="W1", title="First"), database_path)
    second = save_paper(make_paper(external_id="W2", title="Second"), database_path)

    papers = list_papers(database_path)

    assert [paper.id for paper in papers] == [second.id, first.id]
    assert [paper.title for paper in papers] == ["Second", "First"]


def test_update_paper_updates_fields_and_serializes_authors(tmp_path):
    database_path = tmp_path / "papers.db"
    saved = save_paper(make_paper(), database_path)

    updated = update_paper(
        saved.id,
        database_path,
        title="  Improved title  ",
        authors=["New Author"],
        summary="Useful summary",
    )

    assert updated.title == "  Improved title  "
    assert updated.authors == ["New Author"]
    assert updated.summary == "Useful summary"


def test_update_with_no_changes_returns_existing_paper(tmp_path):
    database_path = tmp_path / "papers.db"
    saved = save_paper(make_paper(), database_path)

    assert update_paper(saved.id, database_path) == saved


def test_missing_paper_returns_none_for_get_and_update(tmp_path):
    database_path = tmp_path / "papers.db"

    assert get_paper(999, database_path) is None
    assert update_paper(999, database_path, summary="missing") is None


@pytest.mark.parametrize(
    ("paper", "message"),
    [
        (make_paper(title="   "), "title cannot be empty"),
        (make_paper(source_type="manual"), "source_type must be"),
    ],
)
def test_save_rejects_invalid_papers(tmp_path, paper, message):
    with pytest.raises(ValueError, match=message):
        save_paper(paper, tmp_path / "papers.db")


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"title": ""}, "title cannot be empty"),
        ({"source_type": "manual"}, "source_type must be"),
        ({"created_at": "tomorrow"}, "Unsupported paper field"),
    ],
)
def test_update_rejects_invalid_changes(tmp_path, changes, message):
    database_path = tmp_path / "papers.db"
    saved = save_paper(make_paper(), database_path)

    with pytest.raises(ValueError, match=message):
        update_paper(saved.id, database_path, **changes)


def test_duplicate_external_id_raises_integrity_error(tmp_path):
    database_path = tmp_path / "papers.db"
    save_paper(make_paper(), database_path)

    with pytest.raises(sqlite3.IntegrityError):
        save_paper(make_paper(title="Duplicate"), database_path)


def test_initialize_database_migrates_missing_page_columns(tmp_path):
    database_path = tmp_path / "old.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE papers (
                id INTEGER PRIMARY KEY,
                source_type TEXT NOT NULL,
                external_id TEXT UNIQUE,
                title TEXT NOT NULL,
                authors TEXT NOT NULL DEFAULT '[]',
                publication_year INTEGER,
                abstract TEXT,
                paper_url TEXT,
                pdf_url TEXT,
                pdf_path TEXT,
                extracted_text TEXT,
                summary TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    initialize_database(database_path)

    with sqlite3.connect(database_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(papers)")}
    assert {"page_count", "unreadable_page_count"} <= columns


def test_database_path_honors_environment_override(tmp_path, monkeypatch):
    configured = tmp_path / "configured.db"
    monkeypatch.setenv("DATABASE_PATH", str(configured))
    assert get_database_path() == configured


def test_database_path_uses_default_when_not_configured(monkeypatch):
    monkeypatch.delenv("DATABASE_PATH", raising=False)
    assert get_database_path() == DEFAULT_DATABASE_PATH


def test_save_reports_defensive_retrieval_failure(tmp_path, monkeypatch):
    monkeypatch.setattr("services.database.get_paper", Mock(return_value=None))
    with pytest.raises(RuntimeError, match="inserted but could not be retrieved"):
        save_paper(make_paper(), tmp_path / "papers.db")
