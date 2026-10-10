"""SQLite persistence for saved research papers."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from models.paper import Paper


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "research_assistant.db"

EDITABLE_FIELDS = {
    "title",
    "source_type",
    "authors",
    "publication_year",
    "abstract",
    "external_id",
    "paper_url",
    "pdf_url",
    "pdf_path",
    "extracted_text",
    "page_count",
    "unreadable_page_count",
    "summary",
}


def get_database_path() -> Path:
    """Return the configured database path or the project-local default."""
    configured_path = os.getenv("DATABASE_PATH")
    return Path(configured_path).expanduser() if configured_path else DEFAULT_DATABASE_PATH


def _connect(database_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(database_path) if database_path is not None else get_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path: str | Path | None = None) -> None:
    """Create the database schema if it does not already exist."""
    with _connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL
                    CHECK (source_type IN ('openalex', 'upload')),
                external_id TEXT UNIQUE,
                title TEXT NOT NULL,
                authors TEXT NOT NULL DEFAULT '[]',
                publication_year INTEGER,
                abstract TEXT,
                paper_url TEXT,
                pdf_url TEXT,
                pdf_path TEXT,
                extracted_text TEXT,
                page_count INTEGER,
                unreadable_page_count INTEGER NOT NULL DEFAULT 0,
                summary TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        existing_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(papers)")
        }
        if "page_count" not in existing_columns:
            connection.execute("ALTER TABLE papers ADD COLUMN page_count INTEGER")
        if "unreadable_page_count" not in existing_columns:
            connection.execute(
                "ALTER TABLE papers ADD COLUMN unreadable_page_count INTEGER NOT NULL DEFAULT 0"
            )


def save_paper(paper: Paper, database_path: str | Path | None = None) -> Paper:
    """Insert a paper and return it with its generated ID and timestamps."""
    _validate_paper(paper)
    initialize_database(database_path)

    with _connect(database_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO papers (
                source_type, external_id, title, authors, publication_year,
                abstract, paper_url, pdf_url, pdf_path, extracted_text,
                page_count, unreadable_page_count, summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                paper.source_type,
                paper.external_id,
                paper.title.strip(),
                json.dumps(paper.authors),
                paper.publication_year,
                paper.abstract,
                paper.paper_url,
                paper.pdf_url,
                paper.pdf_path,
                paper.extracted_text,
                paper.page_count,
                paper.unreadable_page_count,
                paper.summary,
            ),
        )
        paper_id = cursor.lastrowid

    saved_paper = get_paper(paper_id, database_path)
    if saved_paper is None:  # Defensive: the inserted row should always exist.
        raise RuntimeError("The paper was inserted but could not be retrieved.")
    return saved_paper


def get_paper(
    paper_id: int, database_path: str | Path | None = None
) -> Paper | None:
    """Return one paper by ID, or None when no such paper exists."""
    initialize_database(database_path)
    with _connect(database_path) as connection:
        row = connection.execute(
            "SELECT * FROM papers WHERE id = ?", (paper_id,)
        ).fetchone()
    return _row_to_paper(row) if row else None


def list_papers(database_path: str | Path | None = None) -> list[Paper]:
    """Return all papers, newest first."""
    initialize_database(database_path)
    with _connect(database_path) as connection:
        rows = connection.execute(
            "SELECT * FROM papers ORDER BY created_at DESC, id DESC"
        ).fetchall()
    return [_row_to_paper(row) for row in rows]


def update_paper(
    paper_id: int,
    database_path: str | Path | None = None,
    **changes: Any,
) -> Paper | None:
    """Update allowed paper fields and return the updated paper.

    Returns None if the requested paper does not exist.
    """
    if not changes:
        return get_paper(paper_id, database_path)

    unknown_fields = set(changes) - EDITABLE_FIELDS
    if unknown_fields:
        fields = ", ".join(sorted(unknown_fields))
        raise ValueError(f"Unsupported paper field(s): {fields}")

    if "title" in changes and not str(changes["title"]).strip():
        raise ValueError("Paper title cannot be empty.")
    if "source_type" in changes and changes["source_type"] not in {"openalex", "upload"}:
        raise ValueError("source_type must be 'openalex' or 'upload'.")
    if "authors" in changes:
        changes["authors"] = json.dumps(changes["authors"])

    assignments = ", ".join(f"{field} = ?" for field in changes)
    values = list(changes.values())
    values.append(paper_id)

    initialize_database(database_path)
    with _connect(database_path) as connection:
        cursor = connection.execute(
            f"""
            UPDATE papers
            SET {assignments}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            values,
        )
        if cursor.rowcount == 0:
            return None

    return get_paper(paper_id, database_path)


def _validate_paper(paper: Paper) -> None:
    if not paper.title.strip():
        raise ValueError("Paper title cannot be empty.")
    if paper.source_type not in {"openalex", "upload"}:
        raise ValueError("source_type must be 'openalex' or 'upload'.")


def _row_to_paper(row: sqlite3.Row) -> Paper:
    return Paper(
        id=row["id"],
        source_type=row["source_type"],
        external_id=row["external_id"],
        title=row["title"],
        authors=json.loads(row["authors"]),
        publication_year=row["publication_year"],
        abstract=row["abstract"],
        paper_url=row["paper_url"],
        pdf_url=row["pdf_url"],
        pdf_path=row["pdf_path"],
        extracted_text=row["extracted_text"],
        page_count=row["page_count"],
        unreadable_page_count=row["unreadable_page_count"],
        summary=row["summary"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
