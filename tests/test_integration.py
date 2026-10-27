"""Focused integration tests spanning real PDF parsing, SQLite, and Streamlit."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from streamlit.testing.v1 import AppTest

from models.paper import Paper
from services.database import get_paper, save_paper
from services.pdf_processor import ExtractedPDF, process_pdf


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def generated_text_pdf() -> bytes:
    """Build a two-page PDF with real text on page one and a blank page two."""
    writer = PdfWriter()
    text_page = writer.add_blank_page(width=612, height=792)
    blank_page = writer.add_blank_page(width=612, height=792)

    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_reference = writer._add_object(font)
    text_page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): font_reference}
            )
        }
    )
    content = DecodedStreamObject()
    content.set_data(
        b"BT /F1 12 Tf 72 720 Td 14 TL "
        b"(Reliable Agent-Assisted Testing) Tj T* "
        b"(Abstract: Tests detected important faults.) Tj T* "
        b"(1 Introduction) Tj T* "
        b"(The complete paper text is available.) Tj ET"
    )
    text_page[NameObject("/Contents")] = writer._add_object(content)
    blank_page[NameObject("/Resources")] = DictionaryObject()
    writer.add_metadata(
        {
            "/Title": "Reliable Agent-Assisted Testing",
            "/Author": "Ada Lovelace; Grace Hopper",
            "/CreationDate": "D:20240101000000",
        }
    )
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def extract_generated_pdf() -> ExtractedPDF:
    return process_pdf(generated_text_pdf(), "generated-paper.pdf")


def test_real_pdf_extraction_round_trips_through_sqlite():
    extracted = extract_generated_pdf()
    saved = save_paper(
        Paper(
            title=extracted.title,
            source_type="upload",
            external_id=f"upload:{extracted.file_hash}",
            authors=extracted.authors,
            publication_year=extracted.publication_year,
            abstract=extracted.abstract,
            extracted_text=extracted.extracted_text,
            page_count=extracted.page_count,
            unreadable_page_count=extracted.unreadable_page_count,
        )
    )

    loaded = get_paper(saved.id)

    assert loaded.title == "Reliable Agent-Assisted Testing"
    assert loaded.authors == ["Ada Lovelace", "Grace Hopper"]
    assert loaded.publication_year == 2024
    assert loaded.abstract == "Tests detected important faults."
    assert "The complete paper text is available." in loaded.extracted_text
    assert loaded.page_count == 2
    assert loaded.unreadable_page_count == 1
    assert loaded.external_id == f"upload:{extracted.file_hash}"


def test_persisted_real_pdf_counts_drive_partial_extraction_warning():
    extracted = extract_generated_pdf()
    saved = save_paper(
        Paper(
            title=extracted.title,
            source_type="upload",
            external_id=f"upload:{extracted.file_hash}",
            authors=extracted.authors,
            publication_year=extracted.publication_year,
            abstract=extracted.abstract,
            extracted_text=extracted.extracted_text,
            page_count=extracted.page_count,
            unreadable_page_count=extracted.unreadable_page_count,
            summary="Integration summary",
        )
    )

    app = AppTest.from_file(APP_PATH, default_timeout=10).run()
    reloaded = get_paper(saved.id)

    assert not app.exception
    assert reloaded.page_count == 2
    assert reloaded.unreadable_page_count == 1
    warnings = [warning.value for warning in app.warning]
    assert warnings == [
        "Text could not be extracted from 1 of 2 page(s). Some paper content may "
        "be missing from summaries and question answers."
    ]
