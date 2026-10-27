"""Tests for grounded OpenAI summary and question requests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import openai
import pytest

from services.llm_service import (
    DEFAULT_MODEL,
    MAX_PAPER_CHARACTERS,
    LLMServiceError,
    answer_question,
    generate_summary,
)


def install_fake_client(monkeypatch, output="Generated response"):
    create = Mock(return_value=SimpleNamespace(output_text=output))
    client = SimpleNamespace(responses=SimpleNamespace(create=create))
    constructor = Mock(return_value=client)
    monkeypatch.setattr("services.llm_service.OpenAI", constructor)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    return constructor, create


def test_generate_summary_builds_grounded_request(monkeypatch):
    constructor, create = install_fake_client(monkeypatch, "  A useful summary.  ")

    result = generate_summary("  Full paper text  ")

    assert result == "A useful summary."
    constructor.assert_called_once_with(api_key="test-key", timeout=90.0, max_retries=1)
    request = create.call_args.kwargs
    assert request["model"] == DEFAULT_MODEL
    assert "<paper_text>\nFull paper text\n</paper_text>" in request["input"]
    assert "Do not invent facts" in request["instructions"]
    assert request["max_output_tokens"] == 900
    assert request["store"] is False


def test_answer_question_uses_configured_model_and_question(monkeypatch):
    _, create = install_fake_client(monkeypatch, "Answer")
    monkeypatch.setenv("OPENAI_MODEL", "custom-model")

    assert answer_question("Paper text", " What was found? ") == "Answer"
    request = create.call_args.kwargs
    assert request["model"] == "custom-model"
    assert request["input"].startswith("Question: What was found?")
    assert "<paper_text>\nPaper text\n</paper_text>" in request["input"]
    assert request["max_output_tokens"] == 700


@pytest.mark.parametrize("text", ["", "   ", None])
def test_actions_require_paper_text(text):
    with pytest.raises(LLMServiceError, match="Full paper text is required"):
        generate_summary(text)


def test_actions_reject_excessively_long_paper():
    with pytest.raises(LLMServiceError, match="too long"):
        generate_summary("x" * (MAX_PAPER_CHARACTERS + 1))


@pytest.mark.parametrize(
    ("question", "message"),
    [("", "Enter a question"), ("x" * 2001, "question is too long")],
)
def test_answer_question_validates_question(question, message):
    with pytest.raises(LLMServiceError, match=message):
        answer_question("Paper text", question)


def test_request_requires_api_key():
    with pytest.raises(LLMServiceError, match="OPENAI_API_KEY is not configured"):
        generate_summary("Paper text")


def test_empty_model_output_is_rejected(monkeypatch):
    install_fake_client(monkeypatch, "   ")

    with pytest.raises(LLMServiceError, match="empty response"):
        generate_summary("Paper text")


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (openai.AuthenticationError("bad key", response=Mock(), body=None), "key was rejected"),
        (openai.RateLimitError("limited", response=Mock(), body=None), "rate limit"),
        (openai.APIConnectionError(request=Mock()), "could not be reached"),
    ],
)
def test_known_openai_errors_are_translated(monkeypatch, error, message):
    _, create = install_fake_client(monkeypatch)
    create.side_effect = error

    with pytest.raises(LLMServiceError, match=message):
        generate_summary("Paper text")


@pytest.mark.parametrize(
    ("error_factory", "message"),
    [
        (
            lambda: openai.NotFoundError(
                "missing",
                response=httpx.Response(
                    404, request=httpx.Request("POST", "https://api.test")
                ),
                body=None,
            ),
            "configured OpenAI model 'custom-model' is unavailable",
        ),
        (
            lambda: openai.BadRequestError(
                "bad request",
                response=httpx.Response(
                    400, request=httpx.Request("POST", "https://api.test")
                ),
                body=None,
            ),
            "Verify that 'custom-model' is available",
        ),
        (
            lambda: openai.APIStatusError(
                "server error",
                response=httpx.Response(
                    503, request=httpx.Request("POST", "https://api.test")
                ),
                body=None,
            ),
            "status 503",
        ),
        (
            lambda: openai.APIError(
                "generic", httpx.Request("POST", "https://api.test"), body=None
            ),
            "OpenAI request failed",
        ),
    ],
)
def test_remaining_openai_errors_are_translated(
    monkeypatch, error_factory, message
):
    _, create = install_fake_client(monkeypatch)
    monkeypatch.setenv("OPENAI_MODEL", "custom-model")
    create.side_effect = error_factory()
    with pytest.raises(LLMServiceError, match=message):
        generate_summary("Paper text")
