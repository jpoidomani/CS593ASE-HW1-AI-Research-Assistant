"""Local PDF validation, text extraction, and basic metadata estimation."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError


PROJECT_ROOT = Path(__file__).resolve().parent.parent
UPLOAD_DIRECTORY = PROJECT_ROOT / "data" / "uploads"


class PDFProcessingError(ValueError):
    """Raised when an uploaded file cannot be used as a text PDF."""


@dataclass(slots=True)
class ExtractedPDF:
    filename: str
    file_hash: str
    title: str
    authors: list[str] = field(default_factory=list)
    publication_year: int | None = None
    abstract: str | None = None
    extracted_text: str = ""
    page_count: int = 0


def process_pdf(file_bytes: bytes, filename: str) -> ExtractedPDF:
    """Validate a PDF and extract its text and best-effort local metadata."""
    if not file_bytes or not file_bytes.lstrip().startswith(b"%PDF-"):
        raise PDFProcessingError("The uploaded file is not a valid PDF.")

    try:
        reader = PdfReader(BytesIO(file_bytes), strict=False)
        if reader.is_encrypted and reader.decrypt("") == 0:
            raise PDFProcessingError("Password-protected PDFs are not supported.")
        if not reader.pages:
            raise PDFProcessingError("The PDF does not contain any pages.")

        page_text = [(page.extract_text() or "").strip() for page in reader.pages]
        metadata = reader.metadata
    except PDFProcessingError:
        raise
    except (PdfReadError, OSError, ValueError, TypeError) as error:
        raise PDFProcessingError("The PDF is damaged or could not be read.") from error
    except Exception as error:
        raise PDFProcessingError("Text could not be extracted from this PDF.") from error

    extracted_text = "\n\n".join(text for text in page_text if text).strip()
    if not extracted_text:
        raise PDFProcessingError(
            "No readable text was found. The PDF may contain only scanned images."
        )

    try:
        metadata_title = _clean_metadata_value(getattr(metadata, "title", None))
        metadata_author = _clean_metadata_value(getattr(metadata, "author", None))
        creation_date = getattr(metadata, "creation_date", None)
    except (ValueError, TypeError):
        metadata_title = None
        metadata_author = None
        creation_date = None

    title = metadata_title or _estimate_title(page_text[0], filename)
    authors = _split_authors(metadata_author)
    publication_year = _extract_year(creation_date, page_text[0])
    abstract = _extract_abstract(extracted_text)

    return ExtractedPDF(
        filename=filename,
        file_hash=hashlib.sha256(file_bytes).hexdigest(),
        title=title,
        authors=authors,
        publication_year=publication_year,
        abstract=abstract,
        extracted_text=extracted_text,
        page_count=len(reader.pages),
    )


def save_pdf_file(file_bytes: bytes, file_hash: str) -> str:
    """Persist validated PDF bytes and return a project-relative path."""
    UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    destination = UPLOAD_DIRECTORY / f"{file_hash[:20]}.pdf"
    if not destination.exists():
        destination.write_bytes(file_bytes)
    return str(destination.relative_to(PROJECT_ROOT))


def _estimate_title(first_page_text: str, filename: str) -> str:
    for line in first_page_text.splitlines()[:20]:
        cleaned = " ".join(line.split()).strip()
        if len(cleaned) >= 8 and not re.fullmatch(r"\d+", cleaned):
            return cleaned[:500]
    return Path(filename).stem.replace("_", " ").replace("-", " ").strip()


def _split_authors(raw_authors: str | None) -> list[str]:
    if not raw_authors:
        return []
    return [
        author.strip()
        for author in re.split(r"\s*(?:;|\band\b|\n)\s*", raw_authors)
        if author.strip()
    ]


def _extract_year(creation_date: object, first_page_text: str) -> int | None:
    if hasattr(creation_date, "year"):
        year = int(creation_date.year)
        if 1900 <= year <= 2100:
            return year

    match = re.search(r"\b(?:19|20)\d{2}\b", first_page_text[:6000])
    return int(match.group()) if match else None


def _extract_abstract(text: str) -> str | None:
    match = re.search(
        r"(?is)\babstract\b\s*[:—-]?\s*(.+?)(?=\n\s*(?:keywords?|index terms|1\.?\s+introduction|introduction)\b)",
        text[:20000],
    )
    if not match:
        return None
    abstract = " ".join(match.group(1).split()).strip()
    return abstract[:5000] or None


def _clean_metadata_value(value: object) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(str(value).split()).strip()
    return cleaned or None
