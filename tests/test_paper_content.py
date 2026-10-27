"""Tests for obtaining and attaching full paper content."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests

from models.paper import Paper
from services.paper_content import (
    MAX_PDF_BYTES,
    PaperContentError,
    attach_pdf_to_paper,
    download_open_access_pdf,
)
from services.pdf_processor import PDFProcessingError


def saved_paper(**changes):
    values = {
        "id": 7,
        "title": "Paper",
        "source_type": "openalex",
        "pdf_url": "https://example.test/paper.pdf",
    }
    values.update(changes)
    return Paper(**values)


def extracted_pdf():
    return SimpleNamespace(
        file_hash="b" * 64,
        extracted_text="complete paper text",
        page_count=4,
        unreadable_page_count=1,
    )


def test_attach_pdf_processes_saves_and_updates_paper(monkeypatch):
    paper = saved_paper()
    updated = saved_paper(extracted_text="complete paper text")
    process = Mock(return_value=extracted_pdf())
    save = Mock(return_value="data/uploads/paper.pdf")
    update = Mock(return_value=updated)
    monkeypatch.setattr("services.paper_content.process_pdf", process)
    monkeypatch.setattr("services.paper_content.save_pdf_file", save)
    monkeypatch.setattr("services.paper_content.update_paper", update)

    result = attach_pdf_to_paper(paper, b"%PDF-data", "paper.pdf")

    assert result is updated
    process.assert_called_once_with(b"%PDF-data", "paper.pdf")
    save.assert_called_once_with(b"%PDF-data", "b" * 64)
    update.assert_called_once_with(
        7,
        pdf_path="data/uploads/paper.pdf",
        extracted_text="complete paper text",
        page_count=4,
        unreadable_page_count=1,
    )


def test_download_streams_pdf_and_attaches_it(monkeypatch):
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.iter_content.return_value = [b"%PDF-", b"content", b""]
    request = Mock(return_value=response)
    attached = saved_paper(extracted_text="text")
    attach = Mock(return_value=attached)
    monkeypatch.setattr("services.paper_content.requests.get", request)
    monkeypatch.setattr("services.paper_content.attach_pdf_to_paper", attach)
    paper = saved_paper()

    result = download_open_access_pdf(paper)

    assert result is attached
    request.assert_called_once_with(
        paper.pdf_url, timeout=(5, 30), stream=True, allow_redirects=True
    )
    response.raise_for_status.assert_called_once()
    attach.assert_called_once_with(paper, b"%PDF-content", "openalex-paper.pdf")


@pytest.mark.parametrize(
    ("paper", "message"),
    [
        (saved_paper(id=None), "must be saved"),
        (saved_paper(pdf_url=None), "No open-access PDF URL"),
    ],
)
def test_download_requires_saved_paper_and_url(paper, message):
    with pytest.raises(PaperContentError, match=message):
        download_open_access_pdf(paper)


def test_download_rejects_oversized_pdf(monkeypatch):
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.iter_content.return_value = [b"x" * (MAX_PDF_BYTES + 1)]
    monkeypatch.setattr(
        "services.paper_content.requests.get", Mock(return_value=response)
    )

    with pytest.raises(PaperContentError, match="25 MB"):
        download_open_access_pdf(saved_paper())


def test_download_translates_request_failure(monkeypatch):
    monkeypatch.setattr(
        "services.paper_content.requests.get",
        Mock(side_effect=requests.Timeout("late")),
    )

    with pytest.raises(PaperContentError, match="could not be downloaded"):
        download_open_access_pdf(saved_paper())


def test_attach_requires_saved_paper():
    with pytest.raises(PaperContentError, match="must be saved"):
        attach_pdf_to_paper(saved_paper(id=None), b"data", "paper.pdf")


def test_attach_translates_pdf_processing_error(monkeypatch):
    monkeypatch.setattr(
        "services.paper_content.process_pdf",
        Mock(side_effect=PDFProcessingError("invalid PDF")),
    )

    with pytest.raises(PaperContentError, match="invalid PDF"):
        attach_pdf_to_paper(saved_paper(), b"data", "paper.pdf")


def test_attach_reports_missing_database_record(monkeypatch):
    monkeypatch.setattr(
        "services.paper_content.process_pdf", Mock(return_value=extracted_pdf())
    )
    monkeypatch.setattr(
        "services.paper_content.save_pdf_file", Mock(return_value="paper.pdf")
    )
    monkeypatch.setattr("services.paper_content.update_paper", Mock(return_value=None))

    with pytest.raises(PaperContentError, match="no longer exists"):
        attach_pdf_to_paper(saved_paper(), b"data", "paper.pdf")
