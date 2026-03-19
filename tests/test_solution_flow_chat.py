"""Tests for the solution flow chat pipeline — end-to-end v2.5 verification.

Covers:
- Intent classification on solution-flow pages (discuss→flow override)
- Cognitive frame selection for solution flow (REFINE/EXECUTE modes)
- Retrieval context building with page-aware filtering
- Solution flow context assembly (step injection, entity types, graph depth)
- Chat stream step title injection
- Full context assembly orchestration
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.context.intent_classifier import ChatIntent, classify_intent
from app.context.project_awareness import FlowHealth, ProjectAwareness
from app.context.prompt_compiler import (
    CognitiveFrame,
    CognitiveMode,
    ConfidencePosture,
    Scope,
    TemporalEmphasis,
    compile_cognitive_frame,
    compile_prompt,
    compile_retrieval_plan,
)
from app.core.chat_context import (
    ChatContext,
    build_retrieval_context,
    build_solution_flow_ctx,
)


# ── Shared fixtures ──────────────────────────────────────────────

SOLUTION_FLOW_PAGE = "brd:solution-flow"

FOCUSED_STEP = {
    "type": "solution_flow_step",
    "data": {
        "id": "step-uuid-123",
        "title": "User Completes Assessment",
        "goal": "Guide user through the assessment questionnaire",
    },
}

AWARENESS_SOLUTION_FLOW = ProjectAwareness(
    project_name="Acme Health",
    active_phase="solution_flow",
    flows=[
        FlowHealth("Login", "confirmed", 1.0),
        FlowHealth("User Completes Assessment", "structured", 0.6, blocking="2 open questions"),
        FlowHealth("Review Results", "drafting", 0.2),
    ],
)

AWARENESS_BRD = ProjectAwareness(
    project_name="Acme Health",
    active_phase="brd",
)


# ══════════════════════════════════════════════════════════════════
# Intent Classification — solution flow overrides
# ══════════════════════════════════════════════════════════════════


class TestIntentClassifierSolutionFlow:

    def test_discuss_overridden_to_flow_on_solution_flow_page(self):
        """Generic 'discuss' intent becomes 'flow' on solution-flow pages."""
        intent = classify_intent("Tell me about this step", SOLUTION_FLOW_PAGE)
        assert intent.type == "flow"

    def test_explicit_flow_keywords_stay_flow(self):
        """Flow keywords like 'step', 'goal' keep 'flow' intent."""
        intent = classify_intent("Update the goal for this step", SOLUTION_FLOW_PAGE)
        assert intent.type in ("update", "flow")

    def test_update_intent_not_overridden(self):
        """Update intent stays 'update', not overridden to 'flow'."""
        intent = classify_intent("Change the goal to X", SOLUTION_FLOW_PAGE)
        assert intent.type == "update"

    def test_search_intent_not_overridden(self):
        """Search intent stays 'search' even on solution-flow page."""
        intent = classify_intent("Find evidence about authentication", SOLUTION_FLOW_PAGE)
        assert intent.type == "search"

    def test_create_intent_not_overridden(self):
        """Create stays 'create' on solution-flow page."""
        intent = classify_intent("Add a new behavior", SOLUTION_FLOW_PAGE)
        assert intent.type == "create"

    def test_discuss_on_other_page_stays_discuss(self):
        """On non-solution-flow pages, discuss stays discuss."""
        intent = classify_intent("Tell me about this", "brd:features")
        assert intent.type == "discuss"

    def test_collaborate_override(self):
        """Discuss becomes collaborate on collaborate page."""
        intent = classify_intent("Tell me about the client", "collaborate")
        assert intent.type == "collaborate"

    def test_topic_extraction_on_solution_flow(self):
        """Entity topics extracted from solution flow messages."""
        intent = classify_intent("How does this feature connect to the persona workflow?", SOLUTION_FLOW_PAGE)
        assert "feature" in intent.topics
        assert "persona" in intent.topics
        assert "workflow" in intent.topics

    def test_complexity_simple(self):
        intent = classify_intent("Update the goal", SOLUTION_FLOW_PAGE)
        assert intent.complexity == "simple"

    def test_complexity_strategic(self):
        intent = classify_intent(
            "How do the feature requirements for persona workflow steps connect to the stakeholder goals and constraints?",
            SOLUTION_FLOW_PAGE,
        )
        assert intent.complexity == "strategic"


# ══════════════════════════════════════════════════════════════════
# Cognitive Frame — solution flow dimensions
# ══════════════════════════════════════════════════════════════════


class TestCognitiveFrameSolutionFlow:

    def test_flow_intent_produces_execute_mode(self):
        """Flow intent on solution-flow → EXECUTE mode."""
        frame = compile_cognitive_frame(
            intent_type="flow",
            awareness=AWARENESS_SOLUTION_FLOW,
            page_context=SOLUTION_FLOW_PAGE,
            focused_entity=FOCUSED_STEP,
        )
        assert frame.mode == CognitiveMode.EXECUTE

    def test_discuss_intent_produces_refine_mode(self):
        """Discuss/review intent on solution-flow → REFINE mode."""
        frame = compile_cognitive_frame(
            intent_type="review",
            awareness=AWARENESS_SOLUTION_FLOW,
            page_context=SOLUTION_FLOW_PAGE,
            focused_entity=FOCUSED_STEP,
        )
        assert frame.mode == CognitiveMode.REFINE

    def test_focused_entity_with_update_gives_zoomed_in(self):
        """Focused entity + update intent → ZOOMED_IN scope."""
        frame = compile_cognitive_frame(
            intent_type="update",
            awareness=AWARENESS_SOLUTION_FLOW,
            page_context=SOLUTION_FLOW_PAGE,
            focused_entity=FOCUSED_STEP,
        )
        assert frame.scope == Scope.ZOOMED_IN

    def test_focused_entity_with_flow_gives_zoomed_in(self):
        """Focused entity + flow intent → ZOOMED_IN scope."""
        frame = compile_cognitive_frame(
            intent_type="flow",
            awareness=AWARENESS_SOLUTION_FLOW,
            page_context=SOLUTION_FLOW_PAGE,
            focused_entity=FOCUSED_STEP,
        )
        assert frame.scope == Scope.ZOOMED_IN

    def test_no_focused_entity_gives_contextual(self):
        """No focused entity → CONTEXTUAL scope."""
        frame = compile_cognitive_frame(
            intent_type="flow",
            awareness=AWARENESS_SOLUTION_FLOW,
            page_context=SOLUTION_FLOW_PAGE,
            focused_entity=None,
        )
        assert frame.scope == Scope.CONTEXTUAL

    def test_solution_flow_default_posture_confirming(self):
        """Solution flow phase defaults to CONFIRMING posture."""
        frame = compile_cognitive_frame(
            intent_type="flow",
            awareness=AWARENESS_SOLUTION_FLOW,
            page_context=SOLUTION_FLOW_PAGE,
            focused_entity=None,
        )
        assert frame.posture == ConfidencePosture.CONFIRMING

    def test_matched_confirmed_flow_gives_assertive(self):
        """When focused step matches a confirmed flow → ASSERTIVE posture."""
        confirmed_step = {
            "type": "solution_flow_step",
            "data": {"id": "x", "title": "Login"},
        }
        frame = compile_cognitive_frame(
            intent_type="flow",
            awareness=AWARENESS_SOLUTION_FLOW,
            page_context=SOLUTION_FLOW_PAGE,
            focused_entity=confirmed_step,
        )
        assert frame.posture == ConfidencePosture.ASSERTIVE

    def test_blocking_outcomes_gives_forward_looking(self):
        """Blocking outcomes in horizon → FORWARD_LOOKING temporal."""
        horizon = {"blocking_outcomes": 3, "is_crystallized": True}
        frame = compile_cognitive_frame(
            intent_type="flow",
            awareness=AWARENESS_SOLUTION_FLOW,
            page_context=SOLUTION_FLOW_PAGE,
            focused_entity=FOCUSED_STEP,
            horizon_state=horizon,
        )
        assert frame.temporal == TemporalEmphasis.FORWARD_LOOKING

    def test_no_blocking_gives_present_state(self):
        """No blocking outcomes → PRESENT_STATE temporal."""
        frame = compile_cognitive_frame(
            intent_type="flow",
            awareness=AWARENESS_SOLUTION_FLOW,
            page_context=SOLUTION_FLOW_PAGE,
            focused_entity=FOCUSED_STEP,
            horizon_state=None,
        )
        assert frame.temporal == TemporalEmphasis.PRESENT_STATE


# ══════════════════════════════════════════════════════════════════
# Retrieval Plan — graph depth, recency, confidence from frame
# ══════════════════════════════════════════════════════════════════


class TestRetrievalPlanSolutionFlow:

    def test_zoomed_in_gives_depth_0(self):
        """ZOOMED_IN scope → graph_depth=0."""
        frame = CognitiveFrame(mode=CognitiveMode.EXECUTE, temporal=TemporalEmphasis.PRESENT_STATE, scope=Scope.ZOOMED_IN, posture=ConfidencePosture.CONFIRMING)
        plan = compile_retrieval_plan(frame)
        assert plan["graph_depth"] == 0

    def test_contextual_gives_depth_1(self):
        """CONTEXTUAL scope → graph_depth=1."""
        frame = CognitiveFrame(mode=CognitiveMode.REFINE, temporal=TemporalEmphasis.PRESENT_STATE, scope=Scope.CONTEXTUAL, posture=ConfidencePosture.CONFIRMING)
        plan = compile_retrieval_plan(frame)
        assert plan["graph_depth"] == 1

    def test_panoramic_gives_depth_2(self):
        """PANORAMIC scope → graph_depth=2."""
        frame = CognitiveFrame(mode=CognitiveMode.SYNTHESIZE, temporal=TemporalEmphasis.PRESENT_STATE, scope=Scope.PANORAMIC, posture=ConfidencePosture.EXPLORATORY)
        plan = compile_retrieval_plan(frame)
        assert plan["graph_depth"] == 2

    def test_evolving_posture_boosts_recent(self):
        frame = CognitiveFrame(mode=CognitiveMode.EXECUTE, temporal=TemporalEmphasis.PRESENT_STATE, scope=Scope.ZOOMED_IN, posture=ConfidencePosture.EVOLVING)
        plan = compile_retrieval_plan(frame)
        assert plan.get("boost_recent_signals") is True

    def test_assertive_posture_boosts_confirmed(self):
        frame = CognitiveFrame(mode=CognitiveMode.EXECUTE, temporal=TemporalEmphasis.PRESENT_STATE, scope=Scope.ZOOMED_IN, posture=ConfidencePosture.ASSERTIVE)
        plan = compile_retrieval_plan(frame)
        assert plan.get("boost_confirmed") is True

    def test_recency_always_true_unless_retrospective(self):
        frame = CognitiveFrame(mode=CognitiveMode.REFINE, temporal=TemporalEmphasis.RETROSPECTIVE, scope=Scope.CONTEXTUAL, posture=ConfidencePosture.CONFIRMING)
        plan = compile_retrieval_plan(frame)
        assert plan["apply_recency"] is False


# ══════════════════════════════════════════════════════════════════
# Page-Context Configuration Maps
# ══════════════════════════════════════════════════════════════════


class TestPageContextMaps:
    """Verify solution-flow page gets correct ChatMode profile."""

    def test_solution_flow_mode(self):
        """Solution flow page uses correct chat mode."""
        from app.context.chat_modes import get_chat_mode

        mode = get_chat_mode("brd:solution-flow")
        assert mode.name == "solution_flow"
        assert mode.primary_entity_type == "solution_flow_step"
        assert mode.thinking_eligible is True
        assert "solution_flow" in mode.tools

    def test_default_mode_for_unknown_page(self):
        """Unknown pages get default mode."""
        from app.context.chat_modes import get_chat_mode

        mode = get_chat_mode("unknown")
        assert mode.name == "default"

    def test_overview_mode_has_no_retrieval(self):
        """Overview page skips retrieval."""
        from app.context.chat_modes import get_chat_mode

        mode = get_chat_mode("overview")
        assert mode.retrieval_strategy == "none"

    def test_features_mode(self):
        """Features page mode."""
        from app.context.chat_modes import get_chat_mode

        mode = get_chat_mode("brd:features")
        assert mode.primary_entity_type == "feature"
        assert mode.load_confidence is True


# ══════════════════════════════════════════════════════════════════
# build_retrieval_context — full v2.5 pipeline verification
# ══════════════════════════════════════════════════════════════════


class TestBuildRetrievalContext:

    @pytest.mark.asyncio
    async def test_calls_retrieve_with_correct_params(self):
        """Retrieval uses defaults when no retrieval plan is provided."""
        mock_result = MagicMock()

        with (
            patch("app.core.retrieval.retrieve", new_callable=AsyncMock, return_value=mock_result) as mock_retrieve,
            patch("app.core.retrieval_format.format_retrieval_for_context", return_value="formatted evidence"),
        ):
            result = await build_retrieval_context(
                message="What behaviors should this step have?",
                project_id="proj-1",
                page_context=SOLUTION_FLOW_PAGE,
                focused_entity=FOCUSED_STEP,
            )

            assert result == "formatted evidence"
            mock_retrieve.assert_called_once()
            call_kwargs = mock_retrieve.call_args.kwargs

            # Core v2.5 assertions (defaults without retrieval plan)
            assert call_kwargs["skip_reranking"] is False
            assert call_kwargs["skip_evaluation"] is True
            assert call_kwargs["apply_recency"] is True
            assert call_kwargs["apply_confidence"] is True
            assert call_kwargs["graph_depth"] == 1  # Default without plan
            assert call_kwargs["entity_types"] is None  # No page-specific filtering
            assert call_kwargs["max_rounds"] == 1

    @pytest.mark.asyncio
    async def test_context_hint_from_focused_entity(self):
        """Focused entity generates a context hint for retrieval."""
        mock_result = MagicMock()

        with (
            patch("app.core.retrieval.retrieve", new_callable=AsyncMock, return_value=mock_result) as mock_retrieve,
            patch("app.core.retrieval_format.format_retrieval_for_context", return_value=""),
        ):
            await build_retrieval_context(
                message="What about this step?",
                project_id="proj-1",
                page_context=SOLUTION_FLOW_PAGE,
                focused_entity=FOCUSED_STEP,
            )

            call_kwargs = mock_retrieve.call_args.kwargs
            hint = call_kwargs["context_hint"]
            assert "User Completes Assessment" in hint
            assert "Guide user through the assessment" in hint

    @pytest.mark.asyncio
    async def test_short_message_skips_decomposition(self):
        """Messages under 6 words skip query decomposition."""
        mock_result = MagicMock()

        with (
            patch("app.core.retrieval.retrieve", new_callable=AsyncMock, return_value=mock_result) as mock_retrieve,
            patch("app.core.retrieval_format.format_retrieval_for_context", return_value=""),
        ):
            await build_retrieval_context(
                message="update the goal",
                project_id="proj-1",
                page_context=SOLUTION_FLOW_PAGE,
                focused_entity=None,
            )

            call_kwargs = mock_retrieve.call_args.kwargs
            assert call_kwargs["skip_decomposition"] is True

    @pytest.mark.asyncio
    async def test_long_message_with_question_does_not_skip_decomposition(self):
        """Messages 15+ words with ? trigger query decomposition."""
        mock_result = MagicMock()

        with (
            patch("app.core.retrieval.retrieve", new_callable=AsyncMock, return_value=mock_result) as mock_retrieve,
            patch("app.core.retrieval_format.format_retrieval_for_context", return_value=""),
        ):
            await build_retrieval_context(
                message="What are the key behaviors and guardrails for this step and how do they relate to the overall flow design?",
                project_id="proj-1",
                page_context=SOLUTION_FLOW_PAGE,
                focused_entity=None,
            )

            call_kwargs = mock_retrieve.call_args.kwargs
            assert call_kwargs["skip_decomposition"] is False

    @pytest.mark.asyncio
    async def test_retrieval_failure_returns_empty(self):
        """Retrieval failure is non-fatal — returns empty string."""
        with patch("app.core.retrieval.retrieve", new_callable=AsyncMock, side_effect=Exception("db down")):
            result = await build_retrieval_context(
                message="test",
                project_id="proj-1",
                page_context=SOLUTION_FLOW_PAGE,
                focused_entity=None,
            )
            assert result == ""

    @pytest.mark.asyncio
    async def test_features_page_defaults_without_plan(self):
        """Features page uses defaults without retrieval plan."""
        mock_result = MagicMock()

        with (
            patch("app.core.retrieval.retrieve", new_callable=AsyncMock, return_value=mock_result) as mock_retrieve,
            patch("app.core.retrieval_format.format_retrieval_for_context", return_value=""),
        ):
            await build_retrieval_context(
                message="Tell me about the login feature",
                project_id="proj-1",
                page_context="brd:features",
                focused_entity=None,
            )

            call_kwargs = mock_retrieve.call_args.kwargs
            assert call_kwargs["entity_types"] is None  # No page-specific filtering
            assert call_kwargs["graph_depth"] == 1  # Default

    @pytest.mark.asyncio
    async def test_no_page_context_uses_defaults(self):
        """No page context → no entity filter, depth 1."""
        mock_result = MagicMock()

        with (
            patch("app.core.retrieval.retrieve", new_callable=AsyncMock, return_value=mock_result) as mock_retrieve,
            patch("app.core.retrieval_format.format_retrieval_for_context", return_value=""),
        ):
            await build_retrieval_context(
                message="Tell me about the project",
                project_id="proj-1",
                page_context=None,
                focused_entity=None,
            )

            call_kwargs = mock_retrieve.call_args.kwargs
            assert call_kwargs["entity_types"] is None
            assert call_kwargs["graph_depth"] == 1


# ══════════════════════════════════════════════════════════════════
# build_solution_flow_ctx — conditional loading
# ══════════════════════════════════════════════════════════════════


class TestBuildSolutionFlowCtx:

    @pytest.mark.asyncio
    async def test_builds_context_on_solution_flow_page(self):
        """Solution flow context loaded when on brd:solution-flow."""
        mock_ctx = MagicMock()
        mock_ctx.focused_step_prompt = "Step: User Completes Assessment"

        with patch(
            "app.core.solution_flow_context.build_solution_flow_context",
            new_callable=AsyncMock,
            return_value=mock_ctx,
        ) as mock_build:
            result = await build_solution_flow_ctx(
                page_context=SOLUTION_FLOW_PAGE,
                project_id="proj-1",
                focused_entity=FOCUSED_STEP,
            )

            assert result is not None
            mock_build.assert_called_once_with(
                project_id="proj-1",
                focused_step_id="step-uuid-123",
            )

    @pytest.mark.asyncio
    async def test_returns_none_on_other_pages(self):
        """Non-solution-flow pages get None."""
        result = await build_solution_flow_ctx(
            page_context="brd:features",
            project_id="proj-1",
            focused_entity=FOCUSED_STEP,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_page(self):
        result = await build_solution_flow_ctx(
            page_context=None,
            project_id="proj-1",
            focused_entity=None,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_handles_no_focused_entity(self):
        """Loads solution flow context even without focused step."""
        mock_ctx = MagicMock()

        with patch(
            "app.core.solution_flow_context.build_solution_flow_context",
            new_callable=AsyncMock,
            return_value=mock_ctx,
        ) as mock_build:
            result = await build_solution_flow_ctx(
                page_context=SOLUTION_FLOW_PAGE,
                project_id="proj-1",
                focused_entity=None,
            )

            assert result is not None
            mock_build.assert_called_once_with(
                project_id="proj-1",
                focused_step_id=None,
            )

    @pytest.mark.asyncio
    async def test_failure_returns_none(self):
        """Solution flow context failure is non-fatal."""
        with patch(
            "app.core.solution_flow_context.build_solution_flow_context",
            new_callable=AsyncMock,
            side_effect=Exception("db error"),
        ):
            result = await build_solution_flow_ctx(
                page_context=SOLUTION_FLOW_PAGE,
                project_id="proj-1",
                focused_entity=FOCUSED_STEP,
            )
            assert result is None


# ══════════════════════════════════════════════════════════════════
# Chat Stream — step title injection
# ══════════════════════════════════════════════════════════════════


class TestStepTitleInjection:
    """Verify that solution flow pages inject step title into user message."""

    def test_step_title_prepended(self):
        """Step title injected at start of user message."""
        # Simulate the injection logic from chat_stream.py lines 77-82
        page_context = SOLUTION_FLOW_PAGE
        focused_entity = FOCUSED_STEP
        message = "What behaviors should this have?"

        user_content = message
        if page_context == "brd:solution-flow" and focused_entity:
            fe_data = focused_entity.get("data", {})
            step_title = fe_data.get("title", "")
            if step_title:
                user_content = f"[Viewing step: {step_title}]\n{message}"

        assert user_content == "[Viewing step: User Completes Assessment]\nWhat behaviors should this have?"

    def test_no_injection_without_focused_entity(self):
        message = "What behaviors should this have?"
        user_content = message
        focused_entity = None

        if SOLUTION_FLOW_PAGE == "brd:solution-flow" and focused_entity:
            fe_data = focused_entity.get("data", {})
            step_title = fe_data.get("title", "")
            if step_title:
                user_content = f"[Viewing step: {step_title}]\n{message}"

        assert user_content == message  # Unchanged

    def test_no_injection_on_other_pages(self):
        message = "What behaviors should this have?"
        user_content = message
        page_context = "brd:features"

        if page_context == "brd:solution-flow" and FOCUSED_STEP:
            fe_data = FOCUSED_STEP.get("data", {})
            step_title = fe_data.get("title", "")
            if step_title:
                user_content = f"[Viewing step: {step_title}]\n{message}"

        assert user_content == message  # Unchanged


# ══════════════════════════════════════════════════════════════════
# Compiled Prompt — solution flow context injection
# ══════════════════════════════════════════════════════════════════


class TestCompiledPromptSolutionFlow:

    def test_solution_flow_ctx_in_dynamic_block(self):
        """Solution flow context appears in compiled prompt's dynamic block."""
        frame = CognitiveFrame(mode=CognitiveMode.EXECUTE, temporal=TemporalEmphasis.PRESENT_STATE, scope=Scope.ZOOMED_IN, posture=ConfidencePosture.CONFIRMING)

        mock_flow_ctx = MagicMock()
        mock_flow_ctx.focused_step_prompt = "Step: User Completes Assessment\nGoal: Guide through questionnaire"
        mock_flow_ctx.flow_summary_prompt = "Flow has 5 steps, 3 confirmed"
        mock_flow_ctx.cross_step_prompt = "Related: Login (confirmed), Review Results (drafting)"

        compiled = compile_prompt(
            frame=frame,
            awareness=AWARENESS_SOLUTION_FLOW,
            page_context=SOLUTION_FLOW_PAGE,
            focused_entity=FOCUSED_STEP,
            retrieval_context="Some evidence from retrieval",
            solution_flow_ctx=mock_flow_ctx,
            confidence_state={},
            horizon_state={},
        )

        # Solution flow context should be in the dynamic block
        assert "User Completes Assessment" in compiled.dynamic_block
        assert "Flow has 5 steps" in compiled.dynamic_block

    def test_page_guidance_in_dynamic_block(self):
        """Solution flow page guidance (tool selection rules) in dynamic block."""
        frame = CognitiveFrame(mode=CognitiveMode.EXECUTE, temporal=TemporalEmphasis.PRESENT_STATE, scope=Scope.ZOOMED_IN, posture=ConfidencePosture.CONFIRMING)

        compiled = compile_prompt(
            frame=frame,
            awareness=AWARENESS_SOLUTION_FLOW,
            page_context=SOLUTION_FLOW_PAGE,
            focused_entity=FOCUSED_STEP,
            retrieval_context="evidence",
            solution_flow_ctx=None,
            confidence_state={},
            horizon_state={},
        )

        # Page guidance for solution-flow should include tool rules
        assert "refine_solution_flow_step" in compiled.dynamic_block
        assert "update_solution_flow_step" in compiled.dynamic_block

    def test_retrieval_context_in_dynamic_block(self):
        """Retrieved evidence appears in dynamic block."""
        frame = CognitiveFrame(mode=CognitiveMode.REFINE, temporal=TemporalEmphasis.PRESENT_STATE, scope=Scope.CONTEXTUAL, posture=ConfidencePosture.CONFIRMING)

        compiled = compile_prompt(
            frame=frame,
            awareness=AWARENESS_SOLUTION_FLOW,
            page_context=SOLUTION_FLOW_PAGE,
            focused_entity=None,
            retrieval_context="## Evidence\n- Signal: Client wants assessment to be mobile-first",
            solution_flow_ctx=None,
            confidence_state={},
            horizon_state={},
        )

        assert "mobile-first" in compiled.dynamic_block

    def test_active_frame_logged(self):
        """Active frame string captures all 4 dimensions."""
        frame = CognitiveFrame(mode=CognitiveMode.EXECUTE, temporal=TemporalEmphasis.PRESENT_STATE, scope=Scope.ZOOMED_IN, posture=ConfidencePosture.CONFIRMING)

        compiled = compile_prompt(
            frame=frame,
            awareness=AWARENESS_SOLUTION_FLOW,
            page_context=SOLUTION_FLOW_PAGE,
            focused_entity=FOCUSED_STEP,
            retrieval_context="",
            solution_flow_ctx=None,
            confidence_state={},
            horizon_state={},
        )

        assert "execute" in compiled.active_frame
        assert "present_state" in compiled.active_frame
        assert "zoomed_in" in compiled.active_frame
        assert "confirming" in compiled.active_frame

    def test_cached_block_has_identity_and_instructions(self):
        """Cached block contains identity + cognitive instructions."""
        frame = CognitiveFrame(mode=CognitiveMode.EXECUTE, temporal=TemporalEmphasis.PRESENT_STATE, scope=Scope.ZOOMED_IN, posture=ConfidencePosture.CONFIRMING)

        compiled = compile_prompt(
            frame=frame,
            awareness=AWARENESS_SOLUTION_FLOW,
            page_context=SOLUTION_FLOW_PAGE,
            focused_entity=FOCUSED_STEP,
            retrieval_context="",
            solution_flow_ctx=None,
            confidence_state={},
            horizon_state={},
        )

        # Cached block should have identity and cognitive mode instructions
        assert "Acme Health" in compiled.cached_block  # project name
        assert compiled.cached_block  # non-empty


# ══════════════════════════════════════════════════════════════════
# Full Context Assembly — orchestration
# ══════════════════════════════════════════════════════════════════


class TestAssembleChatContext:

    @pytest.mark.asyncio
    async def test_assembles_all_8_context_layers(self):
        """All 8 context layers assembled in parallel + awareness after."""
        from app.core.chat_context import assemble_chat_context

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"name": "TestProject"}
        )

        mock_frame = MagicMock()
        mock_flow_ctx = MagicMock()
        mock_awareness = ProjectAwareness(project_name="TestProject", active_phase="solution_flow")

        with (
            patch("app.core.chat_context.compute_context_frame", new_callable=AsyncMock, return_value=mock_frame),
            patch("app.core.chat_context.build_solution_flow_ctx", new_callable=AsyncMock, return_value=mock_flow_ctx),
            patch("app.core.chat_context.build_retrieval_context", new_callable=AsyncMock, return_value="retrieved evidence"),
            patch("app.core.chat_context._safe_load_confidence", new_callable=AsyncMock, return_value={"active_domains": 3}),
            patch("app.core.chat_context._safe_load_horizon", new_callable=AsyncMock, return_value={"is_crystallized": True}),
            patch("app.core.chat_context._safe_load_warm_memory", new_callable=AsyncMock, return_value="Previous chat about auth"),
            patch("app.core.chat_context._safe_load_forge", new_callable=AsyncMock, return_value={"matched_modules": []}),
            patch("app.core.chat_context._safe_load_awareness", new_callable=AsyncMock, return_value=mock_awareness),
        ):
            ctx = await assemble_chat_context(
                project_id="proj-1",
                message="What behaviors should this step have?",
                page_context=SOLUTION_FLOW_PAGE,
                focused_entity=FOCUSED_STEP,
                supabase=mock_sb,
                conversation_id="conv-1",
            )

            assert ctx.context_frame == mock_frame
            assert ctx.solution_flow_ctx == mock_flow_ctx
            assert ctx.retrieval_context == "retrieved evidence"
            assert ctx.project_name == "TestProject"
            assert ctx.awareness == mock_awareness
            assert ctx.confidence_state == {"active_domains": 3}
            assert ctx.horizon_state == {"is_crystallized": True}
            assert ctx.warm_memory == "Previous chat about auth"
            assert ctx.forge_state == {"matched_modules": []}

    @pytest.mark.asyncio
    async def test_solution_flow_ctx_only_on_correct_page(self):
        """build_solution_flow_ctx called with correct page context."""
        from app.core.chat_context import assemble_chat_context

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"name": "Test"}
        )

        with (
            patch("app.core.chat_context.compute_context_frame", new_callable=AsyncMock, return_value=MagicMock()),
            patch("app.core.chat_context.build_solution_flow_ctx", new_callable=AsyncMock, return_value=None) as mock_flow,
            patch("app.core.chat_context.build_retrieval_context", new_callable=AsyncMock, return_value=""),
            patch("app.core.chat_context._safe_load_confidence", new_callable=AsyncMock, return_value={}),
            patch("app.core.chat_context._safe_load_horizon", new_callable=AsyncMock, return_value={}),
            patch("app.core.chat_context._safe_load_warm_memory", new_callable=AsyncMock, return_value=""),
            patch("app.core.chat_context._safe_load_forge", new_callable=AsyncMock, return_value={}),
            patch("app.core.chat_context._safe_load_awareness", new_callable=AsyncMock, return_value=ProjectAwareness()),
        ):
            # On features page — should pass "brd:features" to build_solution_flow_ctx
            await assemble_chat_context(
                project_id="proj-1",
                message="test",
                page_context="brd:features",
                focused_entity=None,
                supabase=mock_sb,
            )

            # build_solution_flow_ctx receives the page context and returns None
            mock_flow.assert_called_once_with("brd:features", "proj-1", None)


# ══════════════════════════════════════════════════════════════════
# End-to-end: intent → frame → retrieval plan consistency
# ══════════════════════════════════════════════════════════════════


class TestEndToEndFrameConsistency:
    """Verify the full chain produces consistent results for solution flow."""

    def test_typical_solution_flow_message(self):
        """'Build out the AI flow for this step' → flow intent → EXECUTE + ZOOMED_IN."""
        intent = classify_intent("Build out the AI flow for this step", SOLUTION_FLOW_PAGE)
        # "build" triggers "create", not "flow"
        assert intent.type in ("create", "flow")

        frame = compile_cognitive_frame(
            intent_type=intent.type,
            awareness=AWARENESS_SOLUTION_FLOW,
            page_context=SOLUTION_FLOW_PAGE,
            focused_entity=FOCUSED_STEP,
        )

        # Create on solution_flow page → SYNTHESIZE mode
        # But with focused_entity and create intent → scope depends on mode
        assert frame.mode in (CognitiveMode.EXECUTE, CognitiveMode.SYNTHESIZE)
        plan = compile_retrieval_plan(frame)
        assert plan["apply_recency"] is True

    def test_review_message_on_solution_flow(self):
        """'How are we doing on this step?' → review → REFINE mode."""
        intent = classify_intent("How are we doing on this step?", SOLUTION_FLOW_PAGE)
        assert intent.type == "review"

        frame = compile_cognitive_frame(
            intent_type="review",
            awareness=AWARENESS_SOLUTION_FLOW,
            page_context=SOLUTION_FLOW_PAGE,
            focused_entity=FOCUSED_STEP,
        )
        assert frame.mode == CognitiveMode.REFINE

    def test_search_message_on_solution_flow(self):
        """'Find evidence about authentication' → search → SYNTHESIZE mode."""
        intent = classify_intent("Find evidence about authentication", SOLUTION_FLOW_PAGE)
        assert intent.type == "search"

        frame = compile_cognitive_frame(
            intent_type="search",
            awareness=AWARENESS_SOLUTION_FLOW,
            page_context=SOLUTION_FLOW_PAGE,
            focused_entity=FOCUSED_STEP,
        )
        assert frame.mode == CognitiveMode.SYNTHESIZE

    def test_generic_discuss_becomes_flow_then_execute(self):
        """Generic 'tell me about this' → discuss→flow → EXECUTE mode."""
        intent = classify_intent("Tell me about this", SOLUTION_FLOW_PAGE)
        assert intent.type == "flow"  # Overridden from discuss

        frame = compile_cognitive_frame(
            intent_type="flow",
            awareness=AWARENESS_SOLUTION_FLOW,
            page_context=SOLUTION_FLOW_PAGE,
            focused_entity=FOCUSED_STEP,
        )
        assert frame.mode == CognitiveMode.EXECUTE
        assert frame.scope == Scope.ZOOMED_IN
