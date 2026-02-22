"""Tests for chat assistant API endpoints.

Covers all 7 chat endpoints via FastAPI TestClient with mocked Supabase + Anthropic.
"""

import json
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


class _AsyncIterator:
    """Async iterator wrapper for mocking ``async for`` loops."""

    def __init__(self, items):
        self._items = list(items)
        self._idx = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._idx >= len(self._items):
            raise StopAsyncIteration
        item = self._items[self._idx]
        self._idx += 1
        return item

PROJECT_ID = str(uuid4())
CONV_ID = str(uuid4())


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────


def parse_sse_events(text: str) -> List[dict]:
    """Parse SSE response body into a list of event dicts."""
    events = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return events


def _mock_supabase(execute_results=None):
    """Supabase mock with chained query builder.

    Args:
        execute_results: Optional list of return values for successive
            .execute() calls (uses side_effect).  When not provided,
            every .execute() returns ``MagicMock(data=[], count=0)``.
    """
    sb = MagicMock()
    chain = MagicMock()
    if execute_results is not None:
        chain.execute.side_effect = execute_results
    else:
        chain.execute.return_value = MagicMock(data=[], count=0)
    chain.eq.return_value = chain
    chain.in_.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.single.return_value = chain
    chain.select.return_value = chain
    chain.insert.return_value = chain
    chain.update.return_value = chain
    sb.table.return_value = chain
    return sb


def _mock_settings():
    """Settings mock with required API keys."""
    settings = MagicMock()
    settings.ANTHROPIC_API_KEY = "test-key-xxx"
    settings.CHAT_MODEL = "claude-3-5-haiku-20241022"
    settings.CHAT_RESPONSE_BUFFER = 4096
    return settings


def _mock_context_frame():
    """Minimal ProjectContextFrame for tests."""
    frame = MagicMock()
    frame.phase = MagicMock(value="seeding")
    frame.phase_progress = 0.3
    frame.total_gap_count = 2
    frame.state_snapshot = "Test project"
    frame.workflow_context = ""
    frame.memory_hints = []
    frame.actions = []
    frame.entity_counts = {}
    return frame


# ──────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def supabase_mock():
    sb = _mock_supabase()
    with patch("app.api.chat.get_supabase", return_value=sb):
        yield sb


@pytest.fixture
def settings_mock():
    with patch("app.api.chat.get_settings", return_value=_mock_settings()):
        yield


@pytest.fixture
def context_frame_mock():
    with patch(
        "app.core.chat_context.compute_context_frame",
        new_callable=AsyncMock,
        return_value=_mock_context_frame(),
    ):
        yield


@pytest.fixture
def rate_limit_mock():
    with patch("app.api.chat.check_chat_rate_limit"):
        yield


# ──────────────────────────────────────────────────────────────────────
# POST /v1/chat
# ──────────────────────────────────────────────────────────────────────


class TestChatEndpoint:
    """POST /v1/chat — SSE streaming chat."""

    def _chat_request(self, client, supabase, project_id=PROJECT_ID, conv_id=None, **overrides):
        """Helper to POST /v1/chat with common mocking."""
        # Default: create new conversation returns data
        supabase.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": conv_id or str(uuid4()), "project_id": project_id}]
        )
        # Project name lookup
        supabase.table.return_value.single.return_value.execute.return_value = MagicMock(
            data={"name": "Test Project"}
        )

        body = {"message": "Hello", **overrides}
        params = {"project_id": project_id}
        if conv_id:
            params["conversation_id"] = conv_id
        return client.post("/v1/chat", json=body, params=params)

    @patch("app.api.chat.check_chat_rate_limit")
    @patch("app.core.chat_context.compute_context_frame", new_callable=AsyncMock)
    @patch("app.api.chat.get_settings")
    @patch("app.api.chat.get_supabase")
    def test_chat_returns_sse_stream(self, mock_sb, mock_settings, mock_frame, mock_rate, client):
        """Chat endpoint returns text/event-stream with correct headers."""
        # Use side_effect to return different values for successive .execute() calls:
        #  1. conversations.insert → conv data
        #  2. messages.insert (user) → msg data  (parallel: runs before project name)
        #  3. projects.select.single → project name
        #  4. messages.insert (assistant) → msg data
        sb = _mock_supabase(execute_results=[
            MagicMock(data=[{"id": CONV_ID, "project_id": PROJECT_ID}]),
            MagicMock(data=[{"id": "msg-1"}]),
            MagicMock(data={"name": "Test Project"}),
            MagicMock(data=[{"id": "msg-2"}]),
        ])
        mock_sb.return_value = sb
        mock_settings.return_value = _mock_settings()
        mock_frame.return_value = _mock_context_frame()

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=False)

        text_event = MagicMock()
        text_event.type = "content_block_delta"
        text_event.delta = MagicMock(text="Hi there!")
        mock_stream.__aiter__ = lambda self: _AsyncIterator([text_event])

        final_msg = MagicMock()
        final_msg.content = [MagicMock(type="text", text="Hi there!")]
        final_msg.usage = MagicMock(input_tokens=100, output_tokens=20)
        mock_stream.get_final_message = AsyncMock(return_value=final_msg)

        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_stream

        with patch("anthropic.AsyncAnthropic", return_value=mock_client):
            resp = client.post(
                "/v1/chat",
                json={"message": "Hello"},
                params={"project_id": PROJECT_ID},
            )

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
        assert resp.headers.get("cache-control") == "no-cache"

        events = parse_sse_events(resp.text)
        assert len(events) >= 2  # at least conversation_id + done
        type_seq = [e["type"] for e in events]
        assert "conversation_id" in type_seq
        assert "done" in type_seq

    @patch("app.api.chat.check_chat_rate_limit")
    @patch("app.core.chat_context.compute_context_frame", new_callable=AsyncMock)
    @patch("app.api.chat.get_settings")
    @patch("app.api.chat.get_supabase")
    def test_chat_stream_events_sequence(self, mock_sb, mock_settings, mock_frame, mock_rate, client):
        """SSE events follow: conversation_id → text → done order."""
        sb = _mock_supabase(execute_results=[
            MagicMock(data=[{"id": CONV_ID, "project_id": PROJECT_ID}]),
            MagicMock(data=[{"id": "msg-1"}]),
            MagicMock(data={"name": "Test"}),
            MagicMock(data=[{"id": "msg-2"}]),
        ])
        mock_sb.return_value = sb
        mock_settings.return_value = _mock_settings()
        mock_frame.return_value = _mock_context_frame()

        mock_stream = AsyncMock()
        mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
        mock_stream.__aexit__ = AsyncMock(return_value=False)

        text_event = MagicMock()
        text_event.type = "content_block_delta"
        text_event.delta = MagicMock(text="Response text")
        mock_stream.__aiter__ = lambda self: _AsyncIterator([text_event])

        final_msg = MagicMock()
        final_msg.content = [MagicMock(type="text", text="Response text")]
        final_msg.usage = MagicMock(input_tokens=50, output_tokens=10)
        mock_stream.get_final_message = AsyncMock(return_value=final_msg)

        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_stream

        with patch("anthropic.AsyncAnthropic", return_value=mock_client):
            resp = client.post(
                "/v1/chat",
                json={"message": "Hi"},
                params={"project_id": PROJECT_ID},
            )

        events = parse_sse_events(resp.text)
        types = [e["type"] for e in events]

        # conversation_id must come first
        assert types[0] == "conversation_id"
        # done must come last
        assert types[-1] == "done"
        # text must appear between them
        assert "text" in types

    @patch("app.api.chat.check_chat_rate_limit")
    @patch("app.api.chat.get_settings")
    @patch("app.api.chat.get_supabase")
    def test_chat_500_no_api_key(self, mock_sb, mock_settings, mock_rate, client):
        """Missing ANTHROPIC_API_KEY returns 500."""
        mock_sb.return_value = _mock_supabase()
        no_key = _mock_settings()
        no_key.ANTHROPIC_API_KEY = None
        mock_settings.return_value = no_key

        resp = client.post(
            "/v1/chat",
            json={"message": "Hi"},
            params={"project_id": PROJECT_ID},
        )
        assert resp.status_code == 500
        assert "API key" in resp.json()["detail"]

    @patch("app.api.chat.check_chat_rate_limit")
    @patch("app.core.chat_context.compute_context_frame", new_callable=AsyncMock)
    @patch("app.api.chat.get_settings")
    @patch("app.api.chat.get_supabase")
    def test_chat_nonexistent_conversation_errors(self, mock_sb, mock_settings, mock_frame, mock_rate, client):
        """Non-existent conversation returns an error with 'not found' detail.

        Note: The outer except-Exception handler re-wraps HTTPException(404)
        as 500, so we assert 500 + message content here.
        """
        sb = _mock_supabase(execute_results=[
            MagicMock(data=None),  # conversations.select.single → not found
        ])
        mock_sb.return_value = sb
        mock_settings.return_value = _mock_settings()
        mock_frame.return_value = _mock_context_frame()

        resp = client.post(
            "/v1/chat",
            json={"message": "Hi"},
            params={"project_id": PROJECT_ID, "conversation_id": str(uuid4())},
        )
        assert resp.status_code == 500
        assert "Conversation not found" in resp.json()["detail"]

    @patch("app.api.chat.check_chat_rate_limit")
    @patch("app.core.chat_context.compute_context_frame", new_callable=AsyncMock)
    @patch("app.api.chat.get_settings")
    @patch("app.api.chat.get_supabase")
    def test_chat_page_context_filters_tools(self, mock_sb, mock_settings, mock_frame, mock_rate, client):
        """page_context parameter is passed to get_tools_for_context."""
        sb = _mock_supabase(execute_results=[
            MagicMock(data=[{"id": CONV_ID, "project_id": PROJECT_ID}]),
            MagicMock(data=[{"id": "msg-1"}]),
            MagicMock(data={"name": "Test"}),
            MagicMock(data=[{"id": "msg-2"}]),
        ])
        mock_sb.return_value = sb
        mock_settings.return_value = _mock_settings()
        mock_frame.return_value = _mock_context_frame()

        with patch("app.core.chat_stream.get_tools_for_context") as mock_tools:
            mock_tools.return_value = []

            mock_stream = AsyncMock()
            mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
            mock_stream.__aexit__ = AsyncMock(return_value=False)
            mock_stream.__aiter__ = lambda self: _AsyncIterator([])
            final_msg = MagicMock()
            final_msg.content = []
            final_msg.usage = MagicMock(input_tokens=0, output_tokens=0)
            mock_stream.get_final_message = AsyncMock(return_value=final_msg)
            mock_client = MagicMock()
            mock_client.messages.stream.return_value = mock_stream

            with patch("anthropic.AsyncAnthropic", return_value=mock_client):
                client.post(
                    "/v1/chat",
                    json={"message": "Hi", "page_context": "brd:features"},
                    params={"project_id": PROJECT_ID},
                )

            mock_tools.assert_called_once_with("brd:features")


# ──────────────────────────────────────────────────────────────────────
# GET /v1/conversations
# ──────────────────────────────────────────────────────────────────────


class TestListConversations:
    """GET /v1/conversations."""

    def test_list_conversations_shape(self, client, supabase_mock):
        supabase_mock.table.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": CONV_ID, "project_id": PROJECT_ID, "is_archived": False}]
        )
        resp = client.get("/v1/conversations", params={"project_id": PROJECT_ID})
        assert resp.status_code == 200
        body = resp.json()
        assert "conversations" in body
        assert "total" in body
        assert isinstance(body["conversations"], list)

    def test_list_conversations_filters_archived(self, client, supabase_mock):
        """Non-archived filter is applied by default."""
        resp = client.get("/v1/conversations", params={"project_id": PROJECT_ID})
        assert resp.status_code == 200
        # Verify .eq("is_archived", False) was called
        supabase_mock.table.return_value.eq.assert_called()


# ──────────────────────────────────────────────────────────────────────
# GET /v1/conversations/{id}/messages
# ──────────────────────────────────────────────────────────────────────


class TestGetMessages:
    """GET /v1/conversations/{id}/messages."""

    def test_get_messages_shape(self, client, supabase_mock):
        supabase_mock.table.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[
                {"id": str(uuid4()), "role": "user", "content": "Hello"},
                {"id": str(uuid4()), "role": "assistant", "content": "Hi!"},
            ]
        )
        resp = client.get(f"/v1/conversations/{CONV_ID}/messages")
        assert resp.status_code == 200
        body = resp.json()
        assert "messages" in body
        assert "total" in body
        assert body["total"] == 2


# ──────────────────────────────────────────────────────────────────────
# POST /v1/detect-entities
# ──────────────────────────────────────────────────────────────────────


class TestDetectEntities:
    """POST /v1/detect-entities."""

    def test_detect_entities_shape(self, client):
        mock_result = {
            "should_extract": True,
            "entity_count": 3,
            "entity_hints": [
                {"type": "feature", "name": "Dashboard"},
                {"type": "persona", "name": "Admin"},
                {"type": "constraint", "name": "GDPR"},
            ],
            "reason": "Multiple entities found.",
        }
        # The import is inside the endpoint function body:
        #   from app.chains.detect_chat_entities import detect_chat_entities
        with patch(
            "app.chains.detect_chat_entities.detect_chat_entities",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            resp = client.post(
                "/v1/detect-entities",
                json={
                    "messages": [
                        {"role": "user", "content": "We need a dashboard for admins, GDPR compliant"},
                    ]
                },
                params={"project_id": PROJECT_ID},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "should_extract" in body
        assert "entity_count" in body
        assert "entity_hints" in body


# ──────────────────────────────────────────────────────────────────────
# POST /v1/save-as-signal
# ──────────────────────────────────────────────────────────────────────


class TestSaveAsSignal:
    """POST /v1/save-as-signal."""

    @patch("app.api.chat_signals.get_supabase")
    def test_save_as_signal_success(self, mock_sb, client):
        sb = _mock_supabase()
        signal_id = str(uuid4())
        sb.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": signal_id}]
        )
        mock_sb.return_value = sb

        with patch(
            "app.graphs.unified_processor.process_signal_v2",
            new_callable=AsyncMock,
            return_value={
                "patches_applied": 5,
                "chat_summary": "Extracted 3 features and 2 personas.",
                "entity_types_affected": ["feature", "persona"],
            },
        ):
            resp = client.post(
                "/v1/save-as-signal",
                json={
                    "messages": [
                        {"role": "user", "content": "We need a dashboard"},
                        {"role": "assistant", "content": "Got it, let me add that."},
                    ]
                },
                params={"project_id": PROJECT_ID},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["patches_applied"] == 5
        assert "feature" in body["type_summary"]

    @patch("app.api.chat_signals.get_supabase")
    def test_save_as_signal_empty_messages(self, mock_sb, client):
        """Empty message content returns success=False."""
        mock_sb.return_value = _mock_supabase()
        resp = client.post(
            "/v1/save-as-signal",
            json={"messages": [{"role": "user", "content": "   "}]},
            params={"project_id": PROJECT_ID},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False


# ──────────────────────────────────────────────────────────────────────
# GET /v1/rate-limit-status
# ──────────────────────────────────────────────────────────────────────


class TestRateLimitStatus:
    """GET /v1/rate-limit-status."""

    def test_rate_limit_status_shape(self, client):
        with patch(
            "app.api.chat.get_chat_rate_limit_stats",
            return_value={
                "tokens_remaining": 8.5,
                "burst_size": 15,
                "requests_per_minute": 10,
                "total_requests": 42,
            },
        ):
            resp = client.get(
                "/v1/rate-limit-status",
                params={"project_id": PROJECT_ID},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "rate_limit" in body


# ──────────────────────────────────────────────────────────────────────
# POST /v1/chat/tools
# ──────────────────────────────────────────────────────────────────────


class TestExecuteToolEndpoint:
    """POST /v1/chat/tools — direct tool execution."""

    def test_execute_tool_directly(self, client):
        with patch(
            "app.api.chat.execute_tool",
            new_callable=AsyncMock,
            return_value={"counts": {"features": 5}},
        ):
            resp = client.post(
                "/v1/chat/tools",
                json={
                    "project_id": PROJECT_ID,
                    "tool_name": "get_project_status",
                    "tool_input": {},
                },
            )
        assert resp.status_code == 200
        assert "counts" in resp.json()

    def test_missing_project_id_errors(self, client):
        """Missing project_id in body returns error mentioning project_id.

        Note: The except-Exception handler re-wraps HTTPException(400) as 500.
        """
        resp = client.post(
            "/v1/chat/tools",
            json={"tool_name": "get_project_status", "tool_input": {}},
        )
        assert resp.status_code == 500
        assert "project_id" in resp.json()["detail"]

    def test_missing_tool_name_errors(self, client):
        """Missing tool_name in body returns error mentioning tool_name."""
        resp = client.post(
            "/v1/chat/tools",
            json={"project_id": PROJECT_ID, "tool_input": {}},
        )
        assert resp.status_code == 500
        assert "tool_name" in resp.json()["detail"]
