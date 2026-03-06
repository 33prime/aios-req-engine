"""Tests for prototype chat endpoints — epic discuss, session chat, verdicts, review summary.

Covers:
- epic_discuss — epic-scoped LLM chat + feedback saving
- session_chat_endpoint — verdict-aware feature chat
- submit_epic_verdict — verdict upsert + validation
- get_epic_verdicts — list confirmations
- get_review_summary — verdict tallies, touched gate, changes brief
- update_review_state — state machine transitions
- _generate_changes_brief — Haiku summary of refine items
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.core.schemas_prototypes import (
    ChatResponse,
    SessionChatRequest,
    SessionContext,
    SubmitEpicVerdictRequest,
)


# ── Shared fixtures ──────────────────────────────────────────────

FAKE_SESSION_ID = UUID("00000000-0000-0000-0000-000000000001")
FAKE_PROTO_ID = UUID("00000000-0000-0000-0000-000000000002")

FAKE_SESSION = {
    "id": str(FAKE_SESSION_ID),
    "prototype_id": str(FAKE_PROTO_ID),
    "session_number": 1,
    "status": "consultant_review",
    "review_state": "in_progress",
}

FAKE_EPIC_PLAN = {
    "vision_epics": [
        {
            "title": "Onboarding Journey",
            "theme": "First-time experience",
            "narrative": "Guide new users through account setup and personalization",
            "features": [
                {"name": "Welcome Wizard", "feature_id": "f1"},
                {"name": "Profile Setup", "feature_id": "f2"},
            ],
            "pain_points": ["Users drop off during setup"],
            "open_questions": ["How many steps should onboarding have?"],
        },
        {
            "title": "Analytics Dashboard",
            "theme": "Data-driven decisions",
            "narrative": "Provide real-time insights and KPI tracking",
            "features": [{"name": "KPI Cards", "feature_id": "f3"}],
            "pain_points": [],
            "open_questions": [],
        },
    ]
}

FAKE_PROTOTYPE = {
    "id": str(FAKE_PROTO_ID),
    "prebuild_intelligence": {"epic_plan": FAKE_EPIC_PLAN},
}

FAKE_OVERLAY = {
    "feature_id": "f1",
    "consultant_verdict": "needs_adjustment",
    "overlay_content": {
        "feature_name": "Welcome Wizard",
        "suggested_verdict": "aligned",
        "gaps": [{"question": "Missing MFA step?"}],
        "overview": {
            "spec_summary": "Multi-step onboarding wizard",
            "prototype_summary": "Single-page form",
            "delta": ["No step indicator", "Missing confirmation"],
            "implementation_status": "partial",
        },
        "confidence": 0.72,
    },
}


def _mock_anthropic_response(text: str):
    """Create a mock Anthropic response with .content[0].text."""
    block = MagicMock()
    block.text = text
    resp = MagicMock()
    resp.content = [block]
    return resp


# ══════════════════════════════════════════════════════════════════
# epic_discuss endpoint
# ══════════════════════════════════════════════════════════════════


class TestEpicDiscuss:

    @pytest.mark.asyncio
    async def test_returns_response_with_epic_context(self):
        """Epic discuss builds epic-scoped prompt and returns LLM response."""
        from app.api.prototype_sessions import epic_discuss

        mock_resp = _mock_anthropic_response("Great question about onboarding. What's the target user?")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_resp

        with (
            patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION),
            patch("app.api.prototype_sessions.get_prototype", return_value=FAKE_PROTOTYPE),
            patch("anthropic.Anthropic", return_value=mock_client),
            patch("app.api.prototype_sessions.create_feedback") as mock_fb,
        ):
            result = await epic_discuss(
                FAKE_SESSION_ID,
                {"message": "What about the onboarding flow?", "epic_index": 0},
            )

            assert result["response"] == "Great question about onboarding. What's the target user?"
            assert result["epic_index"] == 0

            # Verify LLM was called with epic context
            call_kwargs = mock_client.messages.create.call_args
            system_prompt = call_kwargs.kwargs.get("system") or call_kwargs[1].get("system", "")
            assert "Onboarding Journey" in system_prompt
            assert "Welcome Wizard" in system_prompt

            # Verify feedback saved
            mock_fb.assert_called_once()
            fb_kwargs = mock_fb.call_args.kwargs
            assert fb_kwargs["feedback_type"] == "discuss"
            assert fb_kwargs["context"]["epic_title"] == "Onboarding Journey"

    @pytest.mark.asyncio
    async def test_missing_session_returns_404(self):
        from app.api.prototype_sessions import epic_discuss

        with patch("app.api.prototype_sessions.get_session", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await epic_discuss(FAKE_SESSION_ID, {"message": "hello", "epic_index": 0})
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_empty_message_returns_400(self):
        from app.api.prototype_sessions import epic_discuss

        with patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION):
            with pytest.raises(HTTPException) as exc_info:
                await epic_discuss(FAKE_SESSION_ID, {"message": "  ", "epic_index": 0})
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_missing_prototype_returns_404(self):
        from app.api.prototype_sessions import epic_discuss

        with (
            patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION),
            patch("app.api.prototype_sessions.get_prototype", return_value=None),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await epic_discuss(FAKE_SESSION_ID, {"message": "hello", "epic_index": 0})
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_out_of_range_epic_index_uses_fallback(self):
        """When epic_index exceeds plan, still calls LLM with generic context."""
        from app.api.prototype_sessions import epic_discuss

        mock_resp = _mock_anthropic_response("I can help with that.")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_resp

        with (
            patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION),
            patch("app.api.prototype_sessions.get_prototype", return_value=FAKE_PROTOTYPE),
            patch("anthropic.Anthropic", return_value=mock_client),
            patch("app.api.prototype_sessions.create_feedback"),
        ):
            result = await epic_discuss(
                FAKE_SESSION_ID,
                {"message": "What's happening?", "epic_index": 99},
            )
            assert result["response"] == "I can help with that."
            # System prompt uses fallback "this epic" title
            call_kwargs = mock_client.messages.create.call_args
            system_prompt = call_kwargs.kwargs.get("system") or call_kwargs[1].get("system", "")
            assert "this epic" in system_prompt

    @pytest.mark.asyncio
    async def test_llm_failure_returns_500(self):
        from app.api.prototype_sessions import epic_discuss

        with (
            patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION),
            patch("app.api.prototype_sessions.get_prototype", return_value=FAKE_PROTOTYPE),
            patch("anthropic.Anthropic", side_effect=Exception("API down")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await epic_discuss(
                    FAKE_SESSION_ID,
                    {"message": "hello", "epic_index": 0},
                )
            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_system_prompt_rules(self):
        """System prompt should contain conciseness rules but NOT force questions."""
        from app.api.prototype_sessions import epic_discuss

        mock_resp = _mock_anthropic_response("ok")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_resp

        with (
            patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION),
            patch("app.api.prototype_sessions.get_prototype", return_value=FAKE_PROTOTYPE),
            patch("anthropic.Anthropic", return_value=mock_client),
            patch("app.api.prototype_sessions.create_feedback"),
        ):
            await epic_discuss(FAKE_SESSION_ID, {"message": "test", "epic_index": 0})

            call_kwargs = mock_client.messages.create.call_args
            system_prompt = call_kwargs.kwargs.get("system") or call_kwargs[1].get("system", "")
            assert "2-3 sentences" in system_prompt
            assert "requirements" in system_prompt.lower()
            # Should NOT force a follow-up question every time
            assert "ask ONE follow-up question" not in system_prompt
            assert "only ask when genuinely needed" in system_prompt.lower()

    @pytest.mark.asyncio
    async def test_first_review_stays_high_level(self):
        """First review (session_number=1) uses high-level, confirmatory tone."""
        from app.api.prototype_sessions import epic_discuss

        first_review_session = {**FAKE_SESSION, "session_number": 1, "review_state": "in_progress"}
        mock_resp = _mock_anthropic_response("ok")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_resp

        with (
            patch("app.api.prototype_sessions.get_session", return_value=first_review_session),
            patch("app.api.prototype_sessions.get_prototype", return_value=FAKE_PROTOTYPE),
            patch("anthropic.Anthropic", return_value=mock_client),
            patch("app.api.prototype_sessions.create_feedback"),
        ):
            await epic_discuss(FAKE_SESSION_ID, {"message": "test", "epic_index": 0})

            call_kwargs = mock_client.messages.create.call_args
            system_prompt = call_kwargs.kwargs.get("system") or call_kwargs[1].get("system", "")
            assert "FIRST look" in system_prompt or "First review" in system_prompt
            assert "high-level" in system_prompt.lower()
            assert "Do NOT drill" in system_prompt

    @pytest.mark.asyncio
    async def test_re_review_allows_deeper(self):
        """Re-review (session_number>1) allows deeper exploration."""
        from app.api.prototype_sessions import epic_discuss

        re_review_session = {**FAKE_SESSION, "session_number": 2, "review_state": "re_review"}
        mock_resp = _mock_anthropic_response("ok")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_resp

        with (
            patch("app.api.prototype_sessions.get_session", return_value=re_review_session),
            patch("app.api.prototype_sessions.get_prototype", return_value=FAKE_PROTOTYPE),
            patch("anthropic.Anthropic", return_value=mock_client),
            patch("app.api.prototype_sessions.create_feedback"),
        ):
            await epic_discuss(FAKE_SESSION_ID, {"message": "test", "epic_index": 0})

            call_kwargs = mock_client.messages.create.call_args
            system_prompt = call_kwargs.kwargs.get("system") or call_kwargs[1].get("system", "")
            assert "follow-up review" in system_prompt.lower()
            assert "deeper" in system_prompt.lower()


# ══════════════════════════════════════════════════════════════════
# session_chat_endpoint — verdict-aware feature chat
# ══════════════════════════════════════════════════════════════════


class TestSessionChat:

    @pytest.mark.asyncio
    async def test_verdict_aware_prompt_needs_adjustment(self):
        """When consultant_verdict is needs_adjustment, prompt mentions gaps."""
        from app.api.prototype_sessions import session_chat_endpoint

        mock_resp = _mock_anthropic_response("The spec says multi-step but code shows single page.")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_resp

        request = SessionChatRequest(
            message="What's wrong with the wizard?",
            feature_id="f1",
        )

        with (
            patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION),
            patch("app.api.prototype_sessions.get_prototype", return_value=FAKE_PROTOTYPE),
            patch("app.api.prototype_sessions.list_overlays", return_value=[FAKE_OVERLAY]),
            patch("anthropic.Anthropic", return_value=mock_client),
        ):
            result = await session_chat_endpoint(FAKE_SESSION_ID, request)

            assert isinstance(result, ChatResponse)
            assert "multi-step" in result.response.lower() or result.response  # LLM response

            # Check system prompt includes gaps and verdict
            call_kwargs = mock_client.messages.create.call_args
            system_prompt = call_kwargs.kwargs.get("system") or call_kwargs[1].get("system", "")
            assert "NEEDS ADJUSTMENT" in system_prompt
            assert "Missing MFA step?" in system_prompt

    @pytest.mark.asyncio
    async def test_verdict_aware_prompt_aligned(self):
        """When verdict is aligned, prompt affirms assessment."""
        from app.api.prototype_sessions import session_chat_endpoint

        overlay = {**FAKE_OVERLAY, "consultant_verdict": "aligned"}
        mock_resp = _mock_anthropic_response("Looks good!")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_resp

        request = SessionChatRequest(message="Is this complete?", feature_id="f1")

        with (
            patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION),
            patch("app.api.prototype_sessions.get_prototype", return_value=FAKE_PROTOTYPE),
            patch("app.api.prototype_sessions.list_overlays", return_value=[overlay]),
            patch("anthropic.Anthropic", return_value=mock_client),
        ):
            result = await session_chat_endpoint(FAKE_SESSION_ID, request)

            call_kwargs = mock_client.messages.create.call_args
            system_prompt = call_kwargs.kwargs.get("system") or call_kwargs[1].get("system", "")
            assert "ALIGNED" in system_prompt
            assert "Affirm" in system_prompt

    @pytest.mark.asyncio
    async def test_verdict_aware_prompt_off_track(self):
        """When verdict is off_track, prompt helps articulate the problem."""
        from app.api.prototype_sessions import session_chat_endpoint

        overlay = {**FAKE_OVERLAY, "consultant_verdict": "off_track"}
        mock_resp = _mock_anthropic_response("The core problem is wrong.")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_resp

        request = SessionChatRequest(message="Why is this wrong?", feature_id="f1")

        with (
            patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION),
            patch("app.api.prototype_sessions.get_prototype", return_value=FAKE_PROTOTYPE),
            patch("app.api.prototype_sessions.list_overlays", return_value=[overlay]),
            patch("anthropic.Anthropic", return_value=mock_client),
        ):
            result = await session_chat_endpoint(FAKE_SESSION_ID, request)

            call_kwargs = mock_client.messages.create.call_args
            system_prompt = call_kwargs.kwargs.get("system") or call_kwargs[1].get("system", "")
            assert "OFF TRACK" in system_prompt
            assert "core problem" in system_prompt

    @pytest.mark.asyncio
    async def test_no_verdict_fallback(self):
        """When no verdict set, prompt helps understand the feature."""
        from app.api.prototype_sessions import session_chat_endpoint

        overlay = {**FAKE_OVERLAY, "consultant_verdict": None}
        mock_resp = _mock_anthropic_response("Let me help.")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_resp

        request = SessionChatRequest(message="What is this?", feature_id="f1")

        with (
            patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION),
            patch("app.api.prototype_sessions.get_prototype", return_value=FAKE_PROTOTYPE),
            patch("app.api.prototype_sessions.list_overlays", return_value=[overlay]),
            patch("anthropic.Anthropic", return_value=mock_client),
        ):
            result = await session_chat_endpoint(FAKE_SESSION_ID, request)

            call_kwargs = mock_client.messages.create.call_args
            system_prompt = call_kwargs.kwargs.get("system") or call_kwargs[1].get("system", "")
            assert "No verdict set" in system_prompt

    @pytest.mark.asyncio
    async def test_disagreement_noted_in_prompt(self):
        """When consultant disagrees with AI suggestion, prompt notes it."""
        from app.api.prototype_sessions import session_chat_endpoint

        # AI suggested aligned, consultant says needs_adjustment
        mock_resp = _mock_anthropic_response("Interesting divergence.")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_resp

        request = SessionChatRequest(message="Why do I disagree?", feature_id="f1")

        with (
            patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION),
            patch("app.api.prototype_sessions.get_prototype", return_value=FAKE_PROTOTYPE),
            patch("app.api.prototype_sessions.list_overlays", return_value=[FAKE_OVERLAY]),
            patch("anthropic.Anthropic", return_value=mock_client),
        ):
            result = await session_chat_endpoint(FAKE_SESSION_ID, request)

            call_kwargs = mock_client.messages.create.call_args
            system_prompt = call_kwargs.kwargs.get("system") or call_kwargs[1].get("system", "")
            assert "AI suggested" in system_prompt
            assert "aligned" in system_prompt  # AI suggestion
            assert "needs_adjustment" in system_prompt  # consultant choice

    @pytest.mark.asyncio
    async def test_context_info_in_prompt(self):
        """Session context (page, feature, review progress) appears in system prompt."""
        from app.api.prototype_sessions import session_chat_endpoint

        mock_resp = _mock_anthropic_response("ok")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_resp

        request = SessionChatRequest(
            message="How does this look?",
            feature_id="f1",
            context=SessionContext(
                current_page="/dashboard",
                active_feature_name="Welcome Wizard",
                features_reviewed=["f1", "f2"],
            ),
        )

        with (
            patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION),
            patch("app.api.prototype_sessions.get_prototype", return_value=FAKE_PROTOTYPE),
            patch("app.api.prototype_sessions.list_overlays", return_value=[FAKE_OVERLAY]),
            patch("anthropic.Anthropic", return_value=mock_client),
        ):
            await session_chat_endpoint(FAKE_SESSION_ID, request)

            call_kwargs = mock_client.messages.create.call_args
            system_prompt = call_kwargs.kwargs.get("system") or call_kwargs[1].get("system", "")
            assert "/dashboard" in system_prompt
            assert "Welcome Wizard" in system_prompt
            assert "2/" in system_prompt  # 2 features reviewed

    @pytest.mark.asyncio
    async def test_no_overlay_still_works(self):
        """Chat works even when no overlay matches the feature."""
        from app.api.prototype_sessions import session_chat_endpoint

        mock_resp = _mock_anthropic_response("No overlay found, but I can help.")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_resp

        request = SessionChatRequest(message="Tell me about this", feature_id="unknown-feat")

        with (
            patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION),
            patch("app.api.prototype_sessions.get_prototype", return_value=FAKE_PROTOTYPE),
            patch("app.api.prototype_sessions.list_overlays", return_value=[FAKE_OVERLAY]),
            patch("anthropic.Anthropic", return_value=mock_client),
        ):
            result = await session_chat_endpoint(FAKE_SESSION_ID, request)
            assert result.response == "No overlay found, but I can help."

    @pytest.mark.asyncio
    async def test_model_override_used(self):
        """model_override in request is passed to Anthropic."""
        from app.api.prototype_sessions import session_chat_endpoint

        mock_resp = _mock_anthropic_response("ok")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_resp

        request = SessionChatRequest(
            message="test", model_override="claude-sonnet-4-6"
        )

        with (
            patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION),
            patch("app.api.prototype_sessions.get_prototype", return_value=FAKE_PROTOTYPE),
            patch("app.api.prototype_sessions.list_overlays", return_value=[]),
            patch("anthropic.Anthropic", return_value=mock_client),
        ):
            await session_chat_endpoint(FAKE_SESSION_ID, request)

            call_kwargs = mock_client.messages.create.call_args
            assert call_kwargs.kwargs.get("model") == "claude-sonnet-4-6"

    @pytest.mark.asyncio
    async def test_missing_session_returns_404(self):
        from app.api.prototype_sessions import session_chat_endpoint

        request = SessionChatRequest(message="hello")

        with patch("app.api.prototype_sessions.get_session", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await session_chat_endpoint(FAKE_SESSION_ID, request)
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_first_review_no_forced_questions(self):
        """First review prompt does NOT force follow-up questions."""
        from app.api.prototype_sessions import session_chat_endpoint

        first_session = {**FAKE_SESSION, "session_number": 1, "review_state": "in_progress"}
        mock_resp = _mock_anthropic_response("ok")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_resp

        request = SessionChatRequest(message="Looks good", feature_id="f1")

        with (
            patch("app.api.prototype_sessions.get_session", return_value=first_session),
            patch("app.api.prototype_sessions.get_prototype", return_value=FAKE_PROTOTYPE),
            patch("app.api.prototype_sessions.list_overlays", return_value=[FAKE_OVERLAY]),
            patch("anthropic.Anthropic", return_value=mock_client),
        ):
            await session_chat_endpoint(FAKE_SESSION_ID, request)

            call_kwargs = mock_client.messages.create.call_args
            system_prompt = call_kwargs.kwargs.get("system") or call_kwargs[1].get("system", "")
            assert "ask ONE follow-up question" not in system_prompt
            assert "First review" in system_prompt
            assert "high-level" in system_prompt.lower()

    @pytest.mark.asyncio
    async def test_re_review_allows_specifics(self):
        """Re-review prompt allows addressing specific concerns."""
        from app.api.prototype_sessions import session_chat_endpoint

        re_session = {**FAKE_SESSION, "session_number": 2, "review_state": "re_review"}
        mock_resp = _mock_anthropic_response("ok")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_resp

        request = SessionChatRequest(message="What changed?", feature_id="f1")

        with (
            patch("app.api.prototype_sessions.get_session", return_value=re_session),
            patch("app.api.prototype_sessions.get_prototype", return_value=FAKE_PROTOTYPE),
            patch("app.api.prototype_sessions.list_overlays", return_value=[FAKE_OVERLAY]),
            patch("anthropic.Anthropic", return_value=mock_client),
        ):
            await session_chat_endpoint(FAKE_SESSION_ID, request)

            call_kwargs = mock_client.messages.create.call_args
            system_prompt = call_kwargs.kwargs.get("system") or call_kwargs[1].get("system", "")
            assert "Follow-up review" in system_prompt
            assert "specific concern" in system_prompt.lower()


# ══════════════════════════════════════════════════════════════════
# Epic Verdicts — submit + list + review summary
# ══════════════════════════════════════════════════════════════════


class TestSubmitEpicVerdict:

    @pytest.mark.asyncio
    async def test_upserts_confirmation(self):
        from app.api.prototype_sessions import submit_epic_verdict

        body = SubmitEpicVerdictRequest(
            card_type="vision",
            card_index=0,
            verdict="confirmed",
            notes=None,
            source="consultant",
        )

        mock_result = {
            "id": "verdict-1",
            "session_id": str(FAKE_SESSION_ID),
            "card_type": "vision",
            "card_index": 0,
            "verdict": "confirmed",
        }

        with (
            patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION),
            patch("app.api.prototype_sessions.upsert_epic_confirmation", return_value=mock_result),
        ):
            result = await submit_epic_verdict(FAKE_SESSION_ID, body)
            assert result["verdict"] == "confirmed"
            assert result["card_type"] == "vision"

    @pytest.mark.asyncio
    async def test_refine_verdict_with_notes(self):
        from app.api.prototype_sessions import submit_epic_verdict

        body = SubmitEpicVerdictRequest(
            card_type="vision",
            card_index=1,
            verdict="refine",
            notes="Need to add payment integration",
            source="consultant",
        )

        mock_result = {
            "id": "verdict-2",
            "session_id": str(FAKE_SESSION_ID),
            "card_type": "vision",
            "card_index": 1,
            "verdict": "refine",
            "notes": "Need to add payment integration",
        }

        with (
            patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION),
            patch("app.api.prototype_sessions.upsert_epic_confirmation", return_value=mock_result) as mock_upsert,
        ):
            result = await submit_epic_verdict(FAKE_SESSION_ID, body)
            assert result["verdict"] == "refine"
            assert result["notes"] == "Need to add payment integration"

            # Verify upsert called with correct args
            mock_upsert.assert_called_once_with(
                session_id=FAKE_SESSION_ID,
                card_type="vision",
                card_index=1,
                verdict="refine",
                notes="Need to add payment integration",
                answer=None,
                source="consultant",
            )

    @pytest.mark.asyncio
    async def test_missing_session_returns_404(self):
        from app.api.prototype_sessions import submit_epic_verdict

        body = SubmitEpicVerdictRequest(
            card_type="vision", card_index=0, verdict="confirmed", source="consultant"
        )

        with patch("app.api.prototype_sessions.get_session", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await submit_epic_verdict(FAKE_SESSION_ID, body)
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_discovery_card_with_answer(self):
        from app.api.prototype_sessions import submit_epic_verdict

        body = SubmitEpicVerdictRequest(
            card_type="discovery",
            card_index=0,
            verdict=None,
            answer="We should use OAuth for all external APIs",
            source="consultant",
        )

        mock_result = {
            "id": "verdict-3",
            "session_id": str(FAKE_SESSION_ID),
            "card_type": "discovery",
            "card_index": 0,
            "answer": "We should use OAuth for all external APIs",
        }

        with (
            patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION),
            patch("app.api.prototype_sessions.upsert_epic_confirmation", return_value=mock_result),
        ):
            result = await submit_epic_verdict(FAKE_SESSION_ID, body)
            assert result["card_type"] == "discovery"
            assert "OAuth" in result["answer"]


class TestGetEpicVerdicts:

    @pytest.mark.asyncio
    async def test_returns_all_confirmations(self):
        from app.api.prototype_sessions import get_epic_verdicts

        confirmations = [
            {"card_type": "vision", "card_index": 0, "verdict": "confirmed"},
            {"card_type": "vision", "card_index": 1, "verdict": "refine", "notes": "Add auth"},
            {"card_type": "discovery", "card_index": 0, "answer": "Use SSO"},
        ]

        with (
            patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION),
            patch("app.api.prototype_sessions.list_epic_confirmations", return_value=confirmations),
        ):
            result = await get_epic_verdicts(FAKE_SESSION_ID)
            assert len(result) == 3
            assert result[0]["verdict"] == "confirmed"
            assert result[1]["notes"] == "Add auth"

    @pytest.mark.asyncio
    async def test_missing_session_returns_404(self):
        from app.api.prototype_sessions import get_epic_verdicts

        with patch("app.api.prototype_sessions.get_session", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await get_epic_verdicts(FAKE_SESSION_ID)
            assert exc_info.value.status_code == 404


# ══════════════════════════════════════════════════════════════════
# Review Summary
# ══════════════════════════════════════════════════════════════════


class TestGetReviewSummary:

    @pytest.mark.asyncio
    async def test_tallies_and_touched_gate(self):
        from app.api.prototype_sessions import get_review_summary

        confirmations = [
            {"card_type": "vision", "card_index": 0, "verdict": "confirmed"},
            {"card_type": "vision", "card_index": 1, "verdict": "refine", "notes": "Add payment"},
        ]

        with (
            patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION),
            patch("app.api.prototype_sessions.get_prototype", return_value=FAKE_PROTOTYPE),
            patch("app.api.prototype_sessions.list_epic_confirmations", return_value=confirmations),
            patch("app.api.prototype_sessions._generate_changes_brief", return_value="Will add payment."),
        ):
            result = await get_review_summary(FAKE_SESSION_ID)

            assert result["total_epics"] == 2
            assert result["touched"] == 2
            assert result["all_touched"] is True
            assert result["tallies"]["confirmed"] == 1
            assert result["tallies"]["refine"] == 1
            assert result["tallies"]["flag_for_client"] == 0
            assert result["changes_brief"] == "Will add payment."

    @pytest.mark.asyncio
    async def test_not_all_touched(self):
        from app.api.prototype_sessions import get_review_summary

        # Only 1 of 2 epics has a verdict
        confirmations = [
            {"card_type": "vision", "card_index": 0, "verdict": "confirmed"},
        ]

        with (
            patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION),
            patch("app.api.prototype_sessions.get_prototype", return_value=FAKE_PROTOTYPE),
            patch("app.api.prototype_sessions.list_epic_confirmations", return_value=confirmations),
        ):
            result = await get_review_summary(FAKE_SESSION_ID)

            assert result["total_epics"] == 2
            assert result["touched"] == 1
            assert result["all_touched"] is False
            assert result["changes_brief"] is None  # No refines, no brief

    @pytest.mark.asyncio
    async def test_non_vision_cards_not_counted(self):
        """Only vision card_type verdicts count toward tallies."""
        from app.api.prototype_sessions import get_review_summary

        confirmations = [
            {"card_type": "vision", "card_index": 0, "verdict": "confirmed"},
            {"card_type": "discovery", "card_index": 0, "verdict": None, "answer": "Yes"},
            {"card_type": "ai_flow", "card_index": 0, "verdict": "confirmed"},
        ]

        with (
            patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION),
            patch("app.api.prototype_sessions.get_prototype", return_value=FAKE_PROTOTYPE),
            patch("app.api.prototype_sessions.list_epic_confirmations", return_value=confirmations),
        ):
            result = await get_review_summary(FAKE_SESSION_ID)

            # Only vision with verdict counts
            assert result["tallies"]["confirmed"] == 1
            assert result["touched"] == 1

    @pytest.mark.asyncio
    async def test_items_enriched_with_titles(self):
        from app.api.prototype_sessions import get_review_summary

        confirmations = [
            {"card_type": "vision", "card_index": 0, "verdict": "confirmed"},
            {"card_type": "vision", "card_index": 1, "verdict": "refine", "notes": "More data"},
        ]

        with (
            patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION),
            patch("app.api.prototype_sessions.get_prototype", return_value=FAKE_PROTOTYPE),
            patch("app.api.prototype_sessions.list_epic_confirmations", return_value=confirmations),
            patch("app.api.prototype_sessions._generate_changes_brief", return_value="brief"),
        ):
            result = await get_review_summary(FAKE_SESSION_ID)

            items = result["items"]
            assert len(items) == 2
            assert items[0]["title"] == "Onboarding Journey"
            assert items[1]["title"] == "Analytics Dashboard"

    @pytest.mark.asyncio
    async def test_missing_session_returns_404(self):
        from app.api.prototype_sessions import get_review_summary

        with patch("app.api.prototype_sessions.get_session", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await get_review_summary(FAKE_SESSION_ID)
            assert exc_info.value.status_code == 404


# ══════════════════════════════════════════════════════════════════
# _generate_changes_brief
# ══════════════════════════════════════════════════════════════════


class TestGenerateChangesBrief:

    def test_generates_summary_from_refine_items(self):
        from app.api.prototype_sessions import _generate_changes_brief

        mock_resp = _mock_anthropic_response("The update will add payment processing and fix the checkout flow.")
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_resp

        with patch("anthropic.Anthropic", return_value=mock_client):
            result = _generate_changes_brief([
                {"title": "Checkout", "notes": "Add Stripe integration"},
                {"title": "Cart", "notes": "Fix quantity validation"},
            ])

            assert "payment" in result.lower() or "checkout" in result.lower()
            mock_client.messages.create.assert_called_once()
            call_kwargs = mock_client.messages.create.call_args
            assert call_kwargs.kwargs.get("model") == "claude-haiku-4-5-20251001"

    def test_returns_none_on_failure(self):
        from app.api.prototype_sessions import _generate_changes_brief

        with patch("anthropic.Anthropic", side_effect=Exception("API down")):
            result = _generate_changes_brief([{"title": "X", "notes": "y"}])
            assert result is None

    def test_returns_none_when_no_api_key(self):
        from app.api.prototype_sessions import _generate_changes_brief

        mock_settings = MagicMock()
        mock_settings.ANTHROPIC_API_KEY = ""

        with patch("app.core.config.get_settings", return_value=mock_settings):
            result = _generate_changes_brief([{"title": "X", "notes": "y"}])
            assert result is None


# ══════════════════════════════════════════════════════════════════
# Review State Machine
# ══════════════════════════════════════════════════════════════════


class TestUpdateReviewState:

    @pytest.mark.asyncio
    async def test_valid_state_transition(self):
        from app.api.prototype_sessions import update_review_state

        with (
            patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION),
            patch("app.api.prototype_sessions.update_session") as mock_update,
        ):
            result = await update_review_state(
                FAKE_SESSION_ID, {"review_state": "complete"}
            )
            assert result["review_state"] == "complete"
            mock_update.assert_called_once_with(FAKE_SESSION_ID, review_state="complete")

    @pytest.mark.asyncio
    async def test_all_valid_states_accepted(self):
        from app.api.prototype_sessions import update_review_state

        valid = [
            "not_started", "in_progress", "complete", "updating",
            "re_review", "ready_for_client", "staging",
            "client_exploring", "client_complete",
        ]

        for state in valid:
            with (
                patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION),
                patch("app.api.prototype_sessions.update_session"),
            ):
                result = await update_review_state(
                    FAKE_SESSION_ID, {"review_state": state}
                )
                assert result["review_state"] == state

    @pytest.mark.asyncio
    async def test_invalid_state_returns_400(self):
        from app.api.prototype_sessions import update_review_state

        with patch("app.api.prototype_sessions.get_session", return_value=FAKE_SESSION):
            with pytest.raises(HTTPException) as exc_info:
                await update_review_state(
                    FAKE_SESSION_ID, {"review_state": "invalid_state"}
                )
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_missing_session_returns_404(self):
        from app.api.prototype_sessions import update_review_state

        with patch("app.api.prototype_sessions.get_session", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await update_review_state(
                    FAKE_SESSION_ID, {"review_state": "complete"}
                )
            assert exc_info.value.status_code == 404


# ══════════════════════════════════════════════════════════════════
# Schema validation — SubmitEpicVerdictRequest
# ══════════════════════════════════════════════════════════════════


class TestSubmitEpicVerdictRequestSchema:

    def test_valid_vision_verdict(self):
        body = SubmitEpicVerdictRequest(
            card_type="vision", card_index=0, verdict="confirmed", source="consultant"
        )
        assert body.card_type == "vision"
        assert body.verdict == "confirmed"

    def test_valid_refine_with_notes(self):
        body = SubmitEpicVerdictRequest(
            card_type="vision",
            card_index=2,
            verdict="refine",
            notes="Add dark mode",
            source="consultant",
        )
        assert body.notes == "Add dark mode"

    def test_discovery_with_answer(self):
        body = SubmitEpicVerdictRequest(
            card_type="discovery",
            card_index=0,
            verdict=None,
            answer="We need HIPAA compliance",
            source="consultant",
        )
        assert body.answer == "We need HIPAA compliance"
        assert body.verdict is None

    def test_client_source(self):
        body = SubmitEpicVerdictRequest(
            card_type="vision", card_index=0, verdict="client_review", source="client"
        )
        assert body.source == "client"

    def test_invalid_card_type_rejected(self):
        with pytest.raises(Exception):
            SubmitEpicVerdictRequest(
                card_type="invalid", card_index=0, verdict="confirmed", source="consultant"
            )

    def test_invalid_source_rejected(self):
        with pytest.raises(Exception):
            SubmitEpicVerdictRequest(
                card_type="vision", card_index=0, verdict="confirmed", source="admin"
            )
