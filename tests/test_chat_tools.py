"""Tests for chat assistant tool filtering and execution.

Covers:
- get_tools_for_context() — page-context filtering logic
- execute_tool() — dispatch + result for each tool handler
- Mutating tools cache invalidation
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.chains.chat_tools import (
    COMMUNICATION_TOOLS,
    CORE_TOOLS,
    DOCUMENT_TOOLS,
    FALLBACK_EXTRAS,
    PAGE_TOOLS,
    _MUTATING_TOOLS,
    execute_tool,
    get_tool_definitions,
    get_tools_for_context,
)

PROJECT_ID = UUID("00000000-0000-0000-0000-000000000001")


# ──────────────────────────────────────────────────────────────────────
# TestGetToolsForContext — pure logic, no mocks
# ──────────────────────────────────────────────────────────────────────


class TestGetToolsForContext:
    """Test page-context based tool filtering."""

    def _tool_names(self, page_context: str | None = None) -> set[str]:
        return {t["name"] for t in get_tools_for_context(page_context)}

    def test_no_context_returns_core_plus_fallback(self):
        names = self._tool_names(None)
        expected = CORE_TOOLS | FALLBACK_EXTRAS
        assert names == expected

    def test_brd_features_includes_evidence_history(self):
        names = self._tool_names("brd:features")
        # Page-specific tools
        assert "attach_evidence" in names
        assert "query_entity_history" in names
        # Communication + document tools added for brd: pages
        for t in COMMUNICATION_TOOLS | DOCUMENT_TOOLS:
            assert t in names

    def test_brd_business_context_includes_strategic(self):
        names = self._tool_names("brd:business_context")
        assert "generate_strategic_context" in names
        assert "update_strategic_context" in names
        assert "update_project_type" in names

    def test_brd_questions_includes_confirmations_email(self):
        names = self._tool_names("brd:questions")
        assert "list_pending_confirmations" in names
        assert "generate_client_email" in names

    def test_overview_includes_strategic_stakeholder(self):
        names = self._tool_names("overview")
        for tool in PAGE_TOOLS["overview"]:
            assert tool in names

    def test_generic_brd_unions_all_brd_tools(self):
        """The 'brd' page (no subsection) includes all brd:* subsets."""
        names = self._tool_names("brd")
        all_brd = set()
        for key, tools in PAGE_TOOLS.items():
            if key.startswith("brd:"):
                all_brd |= tools
        all_brd |= COMMUNICATION_TOOLS | DOCUMENT_TOOLS
        expected = CORE_TOOLS | all_brd
        assert names == expected

    def test_unknown_page_core_only(self):
        names = self._tool_names("some_random_page")
        assert names == CORE_TOOLS

    def test_all_tools_have_valid_schema(self):
        """Every tool definition has name, description, and input_schema."""
        for tool in get_tool_definitions():
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool
            schema = tool["input_schema"]
            assert schema.get("type") == "object"
            assert "properties" in schema


# ──────────────────────────────────────────────────────────────────────
# TestExecuteTool — mock Supabase per test
# ──────────────────────────────────────────────────────────────────────


def _mock_supabase():
    """Build a chained MagicMock mimicking supabase.table(...).select(...)..."""
    sb = MagicMock()

    # Make every chained method return itself so .eq().order() etc. work
    chain = MagicMock()
    chain.execute.return_value = MagicMock(data=[], count=0)
    chain.eq.return_value = chain
    chain.in_.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.single.return_value = chain
    chain.select.return_value = chain
    chain.insert.return_value = chain
    chain.update.return_value = chain
    chain.rpc.return_value = chain
    chain.desc.return_value = chain

    sb.table.return_value = chain
    sb.rpc.return_value = chain
    return sb


class TestExecuteTool:
    """Test execute_tool dispatch for each tool handler."""

    @pytest.mark.asyncio
    @patch("app.chains.chat_tools.get_supabase")
    async def test_get_project_status(self, mock_get_sb):
        sb = _mock_supabase()
        mock_get_sb.return_value = sb
        result = await execute_tool(PROJECT_ID, "get_project_status", {})
        assert "counts" in result
        assert "message" in result

    @pytest.mark.asyncio
    @patch("app.chains.chat_tools.get_supabase")
    async def test_list_entities_features(self, mock_get_sb):
        sb = _mock_supabase()
        mock_get_sb.return_value = sb
        result = await execute_tool(PROJECT_ID, "list_entities", {"entity_type": "feature"})
        assert result["entity_type"] == "feature"
        assert "items" in result

    @pytest.mark.asyncio
    @patch("app.chains.chat_tools.get_supabase")
    async def test_list_entities_missing_type(self, mock_get_sb):
        sb = _mock_supabase()
        mock_get_sb.return_value = sb
        result = await execute_tool(PROJECT_ID, "list_entities", {})
        assert "error" in result

    @pytest.mark.asyncio
    @patch("app.chains.chat_tools.get_supabase")
    async def test_create_entity(self, mock_get_sb):
        sb = _mock_supabase()
        # insert returns a row
        sb.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid4()), "name": "New Feature"}]
        )
        mock_get_sb.return_value = sb
        result = await execute_tool(
            PROJECT_ID, "create_entity", {"entity_type": "feature", "name": "New Feature"}
        )
        assert "error" not in result or result.get("success")

    @pytest.mark.asyncio
    @patch("app.chains.chat_tools.get_supabase")
    async def test_update_entity(self, mock_get_sb):
        sb = _mock_supabase()
        entity_id = str(uuid4())
        sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": entity_id, "name": "Updated"}]
        )
        mock_get_sb.return_value = sb
        result = await execute_tool(
            PROJECT_ID,
            "update_entity",
            {"entity_type": "feature", "entity_id": entity_id, "fields": {"name": "Updated"}},
        )
        # Should not hard-error
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    @patch("app.chains.chat_tools.get_supabase")
    async def test_create_task(self, mock_get_sb):
        sb = _mock_supabase()
        sb.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid4()), "title": "Follow up"}]
        )
        mock_get_sb.return_value = sb
        result = await execute_tool(PROJECT_ID, "create_task", {"title": "Follow up"})
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_suggest_actions_passthrough(self):
        """suggest_actions returns its input directly (frontend renders)."""
        cards = [{"card_type": "gap_closer", "id": "g1", "data": {}}]
        result = await execute_tool(PROJECT_ID, "suggest_actions", {"cards": cards})
        assert result == {"cards": cards}

    @pytest.mark.asyncio
    @patch("app.chains.chat_tools.get_supabase")
    async def test_add_signal(self, mock_get_sb):
        sb = _mock_supabase()
        sb.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )
        mock_get_sb.return_value = sb
        result = await execute_tool(
            PROJECT_ID,
            "add_signal",
            {"signal_type": "note", "content": "Client prefers dark mode"},
        )
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    @patch("app.chains.chat_tools.get_supabase")
    async def test_create_confirmation(self, mock_get_sb):
        sb = _mock_supabase()
        sb.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid4()), "status": "open"}]
        )
        mock_get_sb.return_value = sb
        result = await execute_tool(
            PROJECT_ID, "create_confirmation", {"question": "Confirm auth flow?"}
        )
        assert result.get("success") is True

    @pytest.mark.asyncio
    @patch("app.chains.chat_tools.get_supabase")
    async def test_add_belief(self, mock_get_sb):
        sb = _mock_supabase()
        sb.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )
        mock_get_sb.return_value = sb
        result = await execute_tool(
            PROJECT_ID, "add_belief", {"content": "Client prefers React"}
        )
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    @patch("app.chains.chat_tools.get_supabase")
    async def test_add_company_reference(self, mock_get_sb):
        sb = _mock_supabase()
        sb.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid4())}]
        )
        mock_get_sb.return_value = sb
        result = await execute_tool(
            PROJECT_ID,
            "add_company_reference",
            {"name": "Figma", "url": "https://figma.com"},
        )
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    @patch("app.chains.chat_tools.get_supabase")
    @patch("app.chains.chat_tools._search")
    async def test_search(self, mock_search_fn, mock_get_sb):
        mock_search_fn.return_value = {
            "success": True,
            "results": [
                {"chunk_id": "c1", "text": "Real-time sync", "similarity": 0.92}
            ],
            "count": 1,
            "query": "sync",
            "message": "Found 1 relevant research chunks",
        }
        mock_get_sb.return_value = _mock_supabase()
        result = await execute_tool(PROJECT_ID, "search", {"query": "sync"})
        assert result["success"] is True
        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        result = await execute_tool(PROJECT_ID, "nonexistent_tool", {})
        assert "error" in result
        assert "Unknown tool" in result["error"]


# ──────────────────────────────────────────────────────────────────────
# TestMutatingToolsCacheInvalidation
# ──────────────────────────────────────────────────────────────────────


class TestMutatingToolsCacheInvalidation:
    """Verify mutating tools trigger invalidate_context_frame."""

    @pytest.mark.asyncio
    @patch("app.chains.chat_tools.get_supabase")
    async def test_mutating_tool_invalidates(self, mock_get_sb):
        sb = _mock_supabase()
        sb.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": str(uuid4()), "name": "Test"}]
        )
        mock_get_sb.return_value = sb

        with patch("app.core.action_engine.invalidate_context_frame") as mock_inv:
            await execute_tool(
                PROJECT_ID,
                "create_entity",
                {"entity_type": "feature", "name": "Test Feature"},
            )
            mock_inv.assert_called_once_with(PROJECT_ID)

    @pytest.mark.asyncio
    @patch("app.chains.chat_tools.get_supabase")
    async def test_read_tool_no_invalidation(self, mock_get_sb):
        mock_get_sb.return_value = _mock_supabase()

        with patch("app.core.action_engine.invalidate_context_frame") as mock_inv:
            await execute_tool(PROJECT_ID, "get_project_status", {})
            mock_inv.assert_not_called()

    def test_mutating_tools_set_matches_expectations(self):
        """Spot-check that key mutating tools are in the set."""
        expected = {
            "create_entity",
            "update_entity",
            "add_signal",
            "create_task",
            "add_belief",
            "add_company_reference",
        }
        assert expected.issubset(_MUTATING_TOOLS)

    def test_suggest_actions_not_mutating(self):
        assert "suggest_actions" not in _MUTATING_TOOLS
        assert "get_project_status" not in _MUTATING_TOOLS
        assert "list_entities" not in _MUTATING_TOOLS
        assert "search" not in _MUTATING_TOOLS
