"""Data model shared by the database and future application services."""

from dataclasses import dataclass, field


@dataclass(slots=True)
class Paper:
    """A research paper saved from OpenAlex or uploaded by the user."""

    title: str
    source_type: str
    authors: list[str] = field(default_factory=list)
    publication_year: int | None = None
    abstract: str | None = None
    external_id: str | None = None
    paper_url: str | None = None
    pdf_url: str | None = None
    pdf_path: str | None = None
    extracted_text: str | None = None
    page_count: int | None = None
    unreadable_page_count: int = 0
    summary: str | None = None
    id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None
