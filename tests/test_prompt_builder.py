"""Tests for dynamic_prompt_builder — focused on the identity/detail split.

Verifies that entity IDs always reach the final prompt regardless of
which context path renders the detail (generic vs specialized).
"""

from uuid import uuid4

import pytest

from app.context.dynamic_prompt_builder import build_smart_chat_prompt
from app.core.schemas_actions import ContextPhase, ProjectContextFrame
from app.core.solution_flow_context import SolutionFlowContext


@pytest.fixture
def minimal_frame():
    """Minimal ProjectContextFrame for prompt builder tests."""
    return ProjectContextFrame(
        phase=ContextPhase.BUILDING,
        phase_progress=0.5,
        state_snapshot="Test project state",
    )


# ─── Identity always present ─────────────────────────────────────────────────


def test_focused_entity_id_in_prompt_generic_path(minimal_frame):
    """Entity ID appears via generic 'Currently Viewing' when no specialized context."""
    entity_id = str(uuid4())
    prompt = build_smart_chat_prompt(
        context_frame=minimal_frame,
        project_name="Test",
        focused_entity={
            "type": "feature",
            "data": {"id": entity_id, "name": "Voice Profiles"},
        },
    )
    assert entity_id in prompt
    assert "Currently Viewing" in prompt


def test_focused_entity_id_in_prompt_with_solution_flow_context(minimal_frame):
    """Entity ID appears even when solution flow context supersedes generic detail."""
    step_id = str(uuid4())
    flow_ctx = SolutionFlowContext(
        flow_summary_prompt="[entry] Onboard user",
        focused_step_prompt=f"Step ID: {step_id}\nTitle: Onboard user\nGoal: Set up voice",
        cross_step_prompt="- Missing phases: output",
    )
    prompt = build_smart_chat_prompt(
        context_frame=minimal_frame,
        project_name="Test",
        page_context="brd:solution-flow",
        focused_entity={
            "type": "solution_flow_step",
            "data": {"id": step_id, "title": "Onboard user", "goal": "Set up voice"},
        },
        solution_flow_context=flow_ctx,
    )
    # ID must appear — both in identity line and in step detail
    assert prompt.count(step_id) >= 2
    assert "Currently Viewing" in prompt


def test_focused_entity_id_in_prompt_empty_flow_context(minimal_frame):
    """Entity ID still present when solution flow context exists but has no focused step."""
    step_id = str(uuid4())
    flow_ctx = SolutionFlowContext(
        flow_summary_prompt="[entry] Onboard user",
        # No focused_step_prompt — generic detail should kick in
    )
    prompt = build_smart_chat_prompt(
        context_frame=minimal_frame,
        project_name="Test",
        page_context="brd:solution-flow",
        focused_entity={
            "type": "solution_flow_step",
            "data": {"id": step_id, "title": "Onboard user"},
        },
        solution_flow_context=flow_ctx,
    )
    assert step_id in prompt
    assert "Currently Viewing" in prompt


def test_no_focused_entity_no_crash(minimal_frame):
    """Prompt builds fine with no focused entity."""
    prompt = build_smart_chat_prompt(
        context_frame=minimal_frame,
        project_name="Test",
    )
    assert "Currently Viewing" not in prompt
    assert len(prompt) > 100


# ─── Detail rendering ────────────────────────────────────────────────────────


def test_generic_detail_includes_goal(minimal_frame):
    """Generic path renders goal when no specialized context."""
    prompt = build_smart_chat_prompt(
        context_frame=minimal_frame,
        project_name="Test",
        focused_entity={
            "type": "feature",
            "data": {"id": str(uuid4()), "name": "Search", "goal": "Find things fast"},
        },
    )
    assert "Find things fast" in prompt


def test_generic_detail_suppressed_by_flow_context(minimal_frame):
    """Generic 'Prioritize this entity' is suppressed when flow context provides detail."""
    step_id = str(uuid4())
    flow_ctx = SolutionFlowContext(
        focused_step_prompt=f"Step ID: {step_id}\nTitle: Test\nGoal: Test goal",
    )
    prompt = build_smart_chat_prompt(
        context_frame=minimal_frame,
        project_name="Test",
        page_context="brd:solution-flow",
        focused_entity={
            "type": "solution_flow_step",
            "data": {"id": step_id, "title": "Test", "goal": "Test goal"},
        },
        solution_flow_context=flow_ctx,
    )
    assert "Prioritize this entity" not in prompt
    assert "Current Step Detail" in prompt


def test_flow_context_sections_rendered(minimal_frame):
    """All solution flow context layers render when populated."""
    step_id = str(uuid4())
    flow_ctx = SolutionFlowContext(
        flow_summary_prompt="[entry] Step A — Creator",
        focused_step_prompt=f"Step ID: {step_id}\nTitle: Step A",
        cross_step_prompt="- Missing phases: admin",
        entity_change_delta='- feature "Search": added priority',
        confirmation_history="Status: ai_generated (v2)",
    )
    prompt = build_smart_chat_prompt(
        context_frame=minimal_frame,
        project_name="Test",
        page_context="brd:solution-flow",
        focused_entity={
            "type": "solution_flow_step",
            "data": {"id": step_id, "title": "Step A"},
        },
        solution_flow_context=flow_ctx,
    )
    assert "Solution Flow Overview" in prompt
    assert "Current Step Detail" in prompt
    assert "Flow Intelligence" in prompt
    assert "Recent Entity Changes" in prompt
    assert "Step History" in prompt


# ─── Page guidance accuracy ──────────────────────────────────────────────────


def test_solution_flow_guidance_references_currently_viewing(minimal_frame):
    """Page guidance tells LLM the step ID is in 'Currently Viewing' — verify it's true."""
    step_id = str(uuid4())
    flow_ctx = SolutionFlowContext(
        focused_step_prompt=f"Step ID: {step_id}\nTitle: Test",
    )
    prompt = build_smart_chat_prompt(
        context_frame=minimal_frame,
        project_name="Test",
        page_context="brd:solution-flow",
        focused_entity={
            "type": "solution_flow_step",
            "data": {"id": step_id, "title": "Test"},
        },
        solution_flow_context=flow_ctx,
    )
    # Guidance says ID is in "Currently Viewing" — verify both exist
    assert 'step ID is in the "Currently Viewing"' in prompt
    # Find the actual "# Currently Viewing" section heading (not the guidance reference)
    heading = "# Currently Viewing\n"
    heading_idx = prompt.index(heading)
    block_start = heading_idx + len(heading)
    # Extract until next section or end
    next_heading = prompt.find("\n\n#", block_start)
    identity_block = prompt[block_start:next_heading] if next_heading != -1 else prompt[block_start:]
    assert step_id in identity_block


# ─── Solution flow context builder ───────────────────────────────────────────


def test_build_focused_step_includes_id():
    """_build_focused_step puts Step ID as the first content line."""
    from app.core.solution_flow_context import _build_focused_step

    step_id = str(uuid4())
    result = _build_focused_step(
        step={"id": step_id, "title": "Test Step", "phase": "entry", "goal": "Do thing"},
        entity_lookup={},
        prev_title=None,
        next_title=None,
    )
    lines = result.strip().split("\n")
    assert lines[0] == f"Step ID: {step_id}"


def test_build_focused_step_includes_all_fields():
    """_build_focused_step renders key fields for LLM context."""
    from app.core.solution_flow_context import _build_focused_step

    step = {
        "id": str(uuid4()),
        "title": "Review content",
        "phase": "core_experience",
        "goal": "Enable quality checks",
        "actors": ["Editor", "Creator"],
        "information_fields": [
            {"name": "Draft", "type": "displayed", "mock_value": "Article text", "confidence": "known"},
        ],
        "open_questions": [
            {"question": "Who approves?", "status": "open"},
            {"question": "Resolved one", "status": "resolved", "resolved_answer": "VP"},
        ],
        "implied_pattern": "Split-pane editor",
        "success_criteria": ["Review in under 5 min"],
        "pain_points_addressed": [{"text": "Manual review is slow", "persona": "Editor"}],
        "goals_addressed": ["Faster turnaround"],
        "ai_config": {"role": "Auto-suggest edits"},
    }
    result = _build_focused_step(step, {}, "Onboard user", "Publish")

    assert "Review content" in result
    assert "core_experience" in result
    assert "Enable quality checks" in result
    assert "Editor" in result
    assert "Draft" in result
    assert "[open] Who approves?" in result
    assert "[resolved]" in result
    assert "Split-pane editor" in result
    assert "Review in under 5 min" in result
    assert "Manual review is slow" in result
    assert "Faster turnaround" in result
    assert "Auto-suggest edits" in result
    assert "Previous: Onboard user" in result
    assert "Next: Publish" in result
