"""Shared isolation fixtures for the Homework 2 test suite."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolated_environment(tmp_path, monkeypatch):
    """Keep every test away from real data files and API credentials."""
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "research_assistant.db"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)
