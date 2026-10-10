"""Streamlit interface for the AI Research Assistant."""

import re
import sqlite3

import streamlit as st
from dotenv import load_dotenv

from models.paper import Paper
from services.database import initialize_database, list_papers, save_paper, update_paper
from services.llm_service import LLMServiceError, answer_question, generate_summary
from services.paper_content import (
    PaperContentError,
    attach_pdf_to_paper,
    download_open_access_pdf,
)
from services.paper_search import OpenAlexError, search_papers
from services.pdf_processor import PDFProcessingError, process_pdf, save_pdf_file


load_dotenv()
st.set_page_config(page_title="AI Research Assistant", page_icon="📚")
initialize_database()


def display_paper(paper: Paper, heading: bool = True) -> None:
    """Render the metadata shared by search results and saved papers."""
    if heading:
        st.subheader(paper.title)

    authors = ", ".join(paper.authors) if paper.authors else "Authors unavailable"
    year = str(paper.publication_year) if paper.publication_year else "Year unavailable"
    st.write(f"**Authors:** {authors}")
    st.write(f"**Publication year:** {year}")
    st.write(f"**Abstract:** {paper.abstract or 'Abstract unavailable.'}")
    if paper.paper_url:
        st.link_button("View paper", paper.paper_url)


def display_extraction_warning(
    unreadable_page_count: int, page_count: int | None
) -> None:
    """Warn when only part of a PDF produced extractable text."""
    if unreadable_page_count <= 0:
        return
    total = f" of {page_count}" if page_count else ""
    st.warning(
        f"Text could not be extracted from {unreadable_page_count}{total} page(s). "
        "Some paper content may be missing from summaries and question answers."
    )


def render_search() -> None:
    st.header("Search Papers")
    st.write("Search OpenAlex by keywords or research topic.")

    with st.form("paper_search_form"):
        query = st.text_input(
            "Keywords or topic",
            placeholder="Example: AI-assisted software engineering",
        )
        submitted = st.form_submit_button("Search")

    if submitted:
        if not query.strip():
            st.warning("Enter keywords or a research topic.")
        else:
            try:
                with st.spinner("Searching OpenAlex..."):
                    st.session_state.search_results = search_papers(query)
                if not st.session_state.search_results:
                    st.info("No papers were found. Try a different search.")
            except OpenAlexError as error:
                st.session_state.search_results = []
                st.error(str(error))

    for index, paper in enumerate(st.session_state.get("search_results", [])):
        with st.container(border=True):
            display_paper(paper)
            if st.button("Save to library", key=f"save_{paper.external_id or index}"):
                try:
                    save_paper(paper)
                    st.success("Paper saved to your library.")
                except sqlite3.IntegrityError:
                    st.info("This paper is already in your library.")
                except (ValueError, RuntimeError) as error:
                    st.error(f"The paper could not be saved: {error}")


def render_upload() -> None:
    st.header("Upload PDF")
    st.write(
        "Upload a text-based research paper, review the locally extracted metadata, "
        "and correct it before saving."
    )
    uploaded_file = st.file_uploader(
        "Research paper PDF",
        type=["pdf"],
        accept_multiple_files=False,
    )
    if uploaded_file is None:
        return

    file_bytes = uploaded_file.getvalue()
    if st.button("Extract text and metadata"):
        try:
            with st.spinner("Reading PDF..."):
                st.session_state.processed_pdf = process_pdf(
                    file_bytes, uploaded_file.name
                )
                st.session_state.processed_pdf_bytes = file_bytes
        except PDFProcessingError as error:
            st.session_state.pop("processed_pdf", None)
            st.session_state.pop("processed_pdf_bytes", None)
            st.error(str(error))

    extracted = st.session_state.get("processed_pdf")
    stored_bytes = st.session_state.get("processed_pdf_bytes")
    if extracted is None or stored_bytes != file_bytes:
        return

    readable_page_count = extracted.page_count - extracted.unreadable_page_count
    st.success(
        f"Processed {extracted.page_count} page(s) and found readable text on "
        f"{readable_page_count}. Review every field below before saving."
    )
    display_extraction_warning(
        extracted.unreadable_page_count, extracted.page_count
    )
    with st.form("pdf_metadata_form"):
        title = st.text_input("Title", value=extracted.title)
        authors = st.text_input(
            "Authors (separate multiple authors with semicolons)",
            value="; ".join(extracted.authors),
        )
        year = st.text_input(
            "Publication year",
            value=str(extracted.publication_year or ""),
        )
        abstract = st.text_area(
            "Abstract",
            value=extracted.abstract or "",
            height=180,
        )
        save_submitted = st.form_submit_button("Save uploaded paper")

    if save_submitted:
        cleaned_authors = [
            author.strip()
            for author in re.split(r"[;\n]+", authors)
            if author.strip()
        ]
        if not title.strip() or not cleaned_authors or not year.strip() or not abstract.strip():
            st.error("Title, authors, publication year, and abstract are required.")
            return
        if not re.fullmatch(r"(?:19|20)\d{2}", year.strip()):
            st.error("Enter a four-digit publication year between 1900 and 2099.")
            return

        try:
            pdf_path = save_pdf_file(file_bytes, extracted.file_hash)
            paper = Paper(
                source_type="upload",
                external_id=f"upload:{extracted.file_hash}",
                title=title.strip(),
                authors=cleaned_authors,
                publication_year=int(year),
                abstract=abstract.strip(),
                pdf_path=pdf_path,
                extracted_text=extracted.extracted_text,
                page_count=extracted.page_count,
                unreadable_page_count=extracted.unreadable_page_count,
            )
            save_paper(paper)
            st.success("Uploaded paper saved to your library.")
        except sqlite3.IntegrityError:
            st.info("This PDF is already in your library.")
        except (OSError, ValueError, RuntimeError) as error:
            st.error(f"The uploaded paper could not be saved: {error}")


def render_library() -> None:
    st.header("Saved Library")
    papers = list_papers()
    if not papers:
        st.info("Your library is empty. Save a paper from the Search Papers section.")
        return

    papers_by_id = {paper.id: paper for paper in papers if paper.id is not None}
    selected_id = st.selectbox(
        "Select a saved paper",
        options=list(papers_by_id),
        format_func=lambda paper_id: papers_by_id[paper_id].title,
    )
    selected_paper = papers_by_id[selected_id]
    with st.container(border=True):
        display_paper(selected_paper)
        st.caption(f"Source: {selected_paper.source_type}")

    if not selected_paper.extracted_text:
        st.warning(
            "Full paper text is not available. Summaries and answers cannot be "
            "generated from metadata or the abstract alone."
        )
        if selected_paper.pdf_url and st.button(
            "Download available open-access PDF",
            key=f"download_pdf_{selected_paper.id}",
        ):
            try:
                with st.spinner("Downloading and extracting the paper..."):
                    selected_paper = download_open_access_pdf(selected_paper)
                st.success("Full paper text was downloaded and saved.")
            except PaperContentError as error:
                st.error(str(error))

        attachment = st.file_uploader(
            "Or attach the corresponding PDF to this saved paper",
            type=["pdf"],
            key=f"library_pdf_{selected_paper.id}",
        )
        if attachment is not None and st.button(
            "Attach PDF to selected paper",
            key=f"attach_pdf_{selected_paper.id}",
        ):
            try:
                with st.spinner("Extracting and attaching the PDF..."):
                    selected_paper = attach_pdf_to_paper(
                        selected_paper,
                        attachment.getvalue(),
                        attachment.name,
                    )
                st.success("PDF attached. Full-text analysis is now available.")
            except PaperContentError as error:
                st.error(str(error))

    display_extraction_warning(
        selected_paper.unreadable_page_count, selected_paper.page_count
    )

    if not selected_paper.extracted_text:
        st.info("Upload the corresponding PDF above to enable analysis.")
        return

    st.divider()
    st.subheader("Paper Summary")
    if selected_paper.summary:
        st.markdown(selected_paper.summary)
        st.caption("Saved summary — no new API request was made.")
    elif st.button("Generate Summary", key=f"summary_{selected_paper.id}"):
        try:
            with st.spinner("Generating a summary from the full paper text..."):
                summary = generate_summary(selected_paper.extracted_text)
                updated = update_paper(selected_paper.id, summary=summary)
                if updated is None:
                    raise RuntimeError("The selected paper no longer exists.")
                selected_paper = updated
            st.markdown(summary)
            st.success("Summary generated and saved.")
        except (LLMServiceError, RuntimeError) as error:
            st.error(str(error))

    st.subheader("Ask a Question")
    with st.form(f"question_form_{selected_paper.id}"):
        question = st.text_input(
            "Question about this paper",
            placeholder="What limitations did the authors identify?",
        )
        ask_submitted = st.form_submit_button("Ask Question")

    answer_key = f"paper_answer_{selected_paper.id}"
    if ask_submitted:
        try:
            with st.spinner("Answering from the full paper text..."):
                st.session_state[answer_key] = answer_question(
                    selected_paper.extracted_text, question
                )
        except LLMServiceError as error:
            st.error(str(error))

    if st.session_state.get(answer_key):
        st.markdown("**Answer:**")
        st.markdown(st.session_state[answer_key])


st.title("AI Research Assistant")
search_tab, upload_tab, library_tab = st.tabs(
    ["Search Papers", "Upload PDF", "Saved Library"]
)

with search_tab:
    render_search()

with upload_tab:
    render_upload()

with library_tab:
    render_library()
