"""The optional Go header follows the request's conversation, not a pooled client."""
from __future__ import annotations

import asyncio

import httpx
import pytest

from deeptutor.services.llm.metrics import TurnUsage, current_usage
from deeptutor.services.llm.openai_http_client import (
    CONVERSATION_SESSION_HEADER,
    _set_conversation_session_header,
    openai_sdk_client_kwargs,
)


async def _header(session_id: str) -> str:
    token = current_usage.set(TurnUsage(session_id=session_id))
    try:
        request = httpx.Request("POST", "http://127.0.0.1:4000/v1/chat/completions")
        await _set_conversation_session_header(request)
        return request.headers["x-opencode-session"]
    finally:
        current_usage.reset(token)


@pytest.mark.asyncio
async def test_stable_across_turns_but_not_conversations():
    first, other, repeated = await asyncio.gather(_header("one"), _header("two"), _header("one"))
    assert first == repeated
    assert first != other
    assert first.startswith("dt_")
    assert "one" not in first


@pytest.mark.asyncio
async def test_unscoped_calls_never_share_a_global_identifier():
    assert await _header("") != await _header("")


@pytest.mark.asyncio
async def test_owner_and_workspace_are_part_of_identity(monkeypatch):
    from deeptutor.services.session import scope
    from deeptutor.services.workspace import context

    monkeypatch.setattr(scope, "current_owner_id", lambda: "owner-a")
    monkeypatch.setattr(context, "current_workspace_id", lambda: "workspace-a")
    first = await _header("same")
    monkeypatch.setattr(scope, "current_owner_id", lambda: "owner-b")
    assert await _header("same") != first
    monkeypatch.setattr(scope, "current_owner_id", lambda: "owner-a")
    monkeypatch.setattr(context, "current_workspace_id", lambda: "workspace-b")
    assert await _header("same") != first


@pytest.mark.asyncio
async def test_only_explicit_opt_in_changes_client_construction():
    normal = openai_sdk_client_kwargs(api_key="local-test", base_url="http://127.0.0.1:4000/v1")
    assert "http_client" not in normal
    assert "x-opencode-session" not in normal["default_headers"]
    special = openai_sdk_client_kwargs(
        api_key="local-test", base_url="http://127.0.0.1:4000/v1",
        extra_headers={"x-opencode-session": CONVERSATION_SESSION_HEADER},
    )
    try:
        assert _set_conversation_session_header in special["http_client"].event_hooks["request"]
        assert special["max_retries"] == 0
        assert special["http_client"].timeout.read == 600
    finally:
        await special["http_client"].aclose()
