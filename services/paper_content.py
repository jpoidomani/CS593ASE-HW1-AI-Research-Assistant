"""Acquire full text for saved OpenAlex papers."""

from __future__ import annotations

import requests

from models.paper import Paper
from services.database import update_paper
from services.pdf_processor import PDFProcessingError, process_pdf, save_pdf_file


MAX_PDF_BYTES = 25 * 1024 * 1024


class PaperContentError(RuntimeError):
    """Raised when full paper content cannot be obtained or attached."""


def download_open_access_pdf(paper: Paper) -> Paper:
    """Download, extract, and attach an OpenAlex paper's available PDF."""
    if paper.id is None:
        raise PaperContentError("The paper must be saved before adding full text.")
    if not paper.pdf_url:
        raise PaperContentError("No open-access PDF URL is available for this paper.")

    try:
        with requests.get(
            paper.pdf_url,
            timeout=(5, 30),
            stream=True,
            allow_redirects=True,
        ) as response:
            response.raise_for_status()
            chunks = []
            total_size = 0
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                total_size += len(chunk)
                if total_size > MAX_PDF_BYTES:
                    raise PaperContentError("The PDF exceeds the 25 MB download limit.")
                chunks.append(chunk)
    except PaperContentError:
        raise
    except requests.RequestException as error:
        raise PaperContentError(
            "The open-access PDF could not be downloaded. Upload it manually instead."
        ) from error

    return attach_pdf_to_paper(paper, b"".join(chunks), "openalex-paper.pdf")


def attach_pdf_to_paper(paper: Paper, file_bytes: bytes, filename: str) -> Paper:
    """Extract a user-provided PDF and attach it to an existing library record."""
    if paper.id is None:
        raise PaperContentError("The paper must be saved before attaching a PDF.")

    try:
        extracted = process_pdf(file_bytes, filename)
        pdf_path = save_pdf_file(file_bytes, extracted.file_hash)
    except (PDFProcessingError, OSError) as error:
        raise PaperContentError(str(error)) from error

    updated = update_paper(
        paper.id,
        pdf_path=pdf_path,
        extracted_text=extracted.extracted_text,
    )
    if updated is None:
        raise PaperContentError("The selected paper no longer exists in the library.")
    return updated
