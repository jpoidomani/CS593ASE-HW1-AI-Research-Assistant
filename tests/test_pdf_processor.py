"""Tests for local PDF validation and extraction."""

from __future__ import annotations

from datetime import datetime
import hashlib
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from pypdf.errors import PdfReadError

from services.pdf_processor import PDFProcessingError, process_pdf, save_pdf_file


class FakePage:
    def __init__(self, text):
        self.text = text

    def extract_text(self):
        return self.text


def fake_reader(*texts, metadata=None, encrypted=False, decrypt_result=1):
    reader = Mock()
    reader.pages = [FakePage(text) for text in texts]
    reader.metadata = metadata or SimpleNamespace(
        title=None, author=None, creation_date=None
    )
    reader.is_encrypted = encrypted
    reader.decrypt.return_value = decrypt_result
    return reader


def test_process_pdf_extracts_text_metadata_and_page_status(monkeypatch):
    metadata = SimpleNamespace(
        title="  Metadata   Title ",
        author="Ada Lovelace and Grace Hopper",
        creation_date=datetime(2024, 1, 1),
    )
    reader = fake_reader(
        "Abstract: This is the abstract.\n1 Introduction\nBody",
        "   ",
        "Results",
        metadata=metadata,
    )
    monkeypatch.setattr("services.pdf_processor.PdfReader", Mock(return_value=reader))

    result = process_pdf(b"%PDF-fake", "paper.pdf")

    assert result.title == "Metadata Title"
    assert result.authors == ["Ada Lovelace", "Grace Hopper"]
    assert result.publication_year == 2024
    assert result.abstract == "This is the abstract."
    assert result.extracted_text.endswith("Results")
    assert result.page_count == 3
    assert result.pages_with_text == [True, False, True]
    assert result.unreadable_page_count == 1
    assert result.file_hash == hashlib.sha256(b"%PDF-fake").hexdigest()


def test_process_pdf_estimates_missing_metadata(monkeypatch):
    reader = fake_reader(
        "Generated Testing for Research\nAuthors here\nPublished 2023\nBody"
    )
    monkeypatch.setattr("services.pdf_processor.PdfReader", Mock(return_value=reader))

    result = process_pdf(b"%PDF-content", "fallback_name.pdf")

    assert result.title == "Generated Testing for Research"
    assert result.authors == []
    assert result.publication_year == 2023
    assert result.abstract is None


@pytest.mark.parametrize("content", [b"", b"plain text", b"  not a pdf"])
def test_process_pdf_rejects_non_pdf_content(content):
    with pytest.raises(PDFProcessingError, match="not a valid PDF"):
        process_pdf(content, "paper.pdf")


def test_process_pdf_rejects_password_protected_pdf(monkeypatch):
    reader = fake_reader("text", encrypted=True, decrypt_result=0)
    monkeypatch.setattr("services.pdf_processor.PdfReader", Mock(return_value=reader))

    with pytest.raises(PDFProcessingError, match="Password-protected"):
        process_pdf(b"%PDF-fake", "paper.pdf")


def test_process_pdf_rejects_pdf_without_pages(monkeypatch):
    monkeypatch.setattr(
        "services.pdf_processor.PdfReader", Mock(return_value=fake_reader())
    )

    with pytest.raises(PDFProcessingError, match="does not contain any pages"):
        process_pdf(b"%PDF-fake", "paper.pdf")


def test_process_pdf_rejects_image_only_pdf(monkeypatch):
    monkeypatch.setattr(
        "services.pdf_processor.PdfReader",
        Mock(return_value=fake_reader(None, "  ")),
    )

    with pytest.raises(PDFProcessingError, match="No readable text"):
        process_pdf(b"%PDF-fake", "paper.pdf")


def test_process_pdf_translates_unexpected_extraction_error(monkeypatch):
    monkeypatch.setattr(
        "services.pdf_processor.PdfReader",
        Mock(side_effect=RuntimeError("parser exploded")),
    )

    with pytest.raises(PDFProcessingError, match="Text could not be extracted"):
        process_pdf(b"%PDF-fake", "paper.pdf")


def test_process_pdf_translates_known_parser_error(monkeypatch):
    monkeypatch.setattr(
        "services.pdf_processor.PdfReader",
        Mock(side_effect=PdfReadError("broken xref")),
    )
    with pytest.raises(PDFProcessingError, match="damaged or could not be read"):
        process_pdf(b"%PDF-fake", "paper.pdf")


def test_process_pdf_handles_unreadable_metadata_properties(monkeypatch):
    class BrokenMetadata:
        @property
        def title(self):
            raise ValueError("invalid metadata")

    reader = fake_reader("Fallback Title From Page\nPublished 2022")
    reader.metadata = BrokenMetadata()
    monkeypatch.setattr("services.pdf_processor.PdfReader", Mock(return_value=reader))

    result = process_pdf(b"%PDF-fake", "fallback.pdf")

    assert result.title == "Fallback Title From Page"
    assert result.authors == []
    assert result.publication_year == 2022


def test_process_pdf_uses_filename_and_splits_author_delimiters(monkeypatch):
    metadata = SimpleNamespace(
        title=None,
        author="Ada Lovelace; Grace Hopper; Katherine Johnson",
        creation_date=None,
    )
    reader = fake_reader("12345", metadata=metadata)
    monkeypatch.setattr("services.pdf_processor.PdfReader", Mock(return_value=reader))

    result = process_pdf(b"%PDF-fake", "agent_testing-paper.pdf")

    assert result.title == "agent testing paper"
    assert result.authors == ["Ada Lovelace", "Grace Hopper", "Katherine Johnson"]
    assert result.publication_year is None


def test_save_pdf_file_writes_once_to_configured_upload_directory(
    tmp_path, monkeypatch
):
    upload_directory = tmp_path / "uploads"
    monkeypatch.setattr("services.pdf_processor.UPLOAD_DIRECTORY", upload_directory)
    monkeypatch.setattr("services.pdf_processor.PROJECT_ROOT", tmp_path)

    relative_path = save_pdf_file(b"first", "a" * 64)
    destination = tmp_path / relative_path
    second_path = save_pdf_file(b"replacement", "a" * 64)

    assert relative_path == second_path == "uploads/aaaaaaaaaaaaaaaaaaaa.pdf"
    assert destination.read_bytes() == b"first"
