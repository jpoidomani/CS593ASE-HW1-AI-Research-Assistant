"""Streamlit interface for the AI Research Assistant."""

import sqlite3

import streamlit as st
from dotenv import load_dotenv

from models.paper import Paper
from services.database import initialize_database, list_papers, save_paper
from services.paper_search import OpenAlexError, search_papers


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


def render_upload_placeholder() -> None:
    st.header("Upload PDF")
    st.info("PDF upload and metadata extraction will be added in the next phase.")


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


st.title("AI Research Assistant")
search_tab, upload_tab, library_tab = st.tabs(
    ["Search Papers", "Upload PDF", "Saved Library"]
)

with search_tab:
    render_search()

with upload_tab:
    render_upload_placeholder()

with library_tab:
    render_library()

