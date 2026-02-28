"""Prompt Compiler — dimensional model for dynamic chat instruction generation.

Selects a cognitive frame across 4 dimensions, then compiles instructions +
context accordingly. Not if/then block selection — dimensional orientation
that shapes how the model thinks.

The Four Dimensions:
  - CognitiveMode: How to think (discover, synthesize, refine, execute, evolve)
  - TemporalEmphasis: What timeframe matters (retrospective, present, forward)
  - Scope: How wide to look (zoomed_in, contextual, panoramic)
  - ConfidencePosture: How sure to be (assertive, exploratory, confirming, evolving)
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.context.project_awareness import FlowHealth, ProjectAwareness, format_awareness_snapshot
from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Dimension Enums ────────────────────────────────────────────────


class CognitiveMode(StrEnum):
    DISCOVER = "discover"
    SYNTHESIZE = "synthesize"
    REFINE = "refine"
    EXECUTE = "execute"
    EVOLVE = "evolve"


class TemporalEmphasis(StrEnum):
    RETROSPECTIVE = "retrospective"
    PRESENT_STATE = "present_state"
    FORWARD_LOOKING = "forward_looking"


class Scope(StrEnum):
    ZOOMED_IN = "zoomed_in"
    CONTEXTUAL = "contextual"
    PANORAMIC = "panoramic"


class ConfidencePosture(StrEnum):
    ASSERTIVE = "assertive"
    EXPLORATORY = "exploratory"
    CONFIRMING = "confirming"
    EVOLVING = "evolving"


@dataclass
class CognitiveFrame:
    mode: CognitiveMode
    temporal: TemporalEmphasis
    scope: Scope
    posture: ConfidencePosture

    @property
    def label(self) -> str:
        return f"{self.mode.value}×{self.temporal.value}×{self.scope.value}×{self.posture.value}"


@dataclass
class CompiledPrompt:
    cached_block: str  # Identity + cognitive instructions (~800-1000t, cached per frame)
    dynamic_block: str  # Awareness state + page context + retrieval (~1500-2500t)
    retrieval_plan: dict  # How retrieval should be shaped
    active_frame: str  # For logging


# ── Frame Selection ────────────────────────────────────────────────


def compile_cognitive_frame(
    intent_type: str,
    awareness: ProjectAwareness,
    page_context: str | None,
    focused_entity: dict | None,
    horizon_state: dict | None = None,
) -> CognitiveFrame:
    """Select cognitive frame from ~20 rules producing hundreds of combinations."""
    phase = awareness.active_phase

    # ── COGNITIVE MODE: from phase + intent ──────────────────────────
    if phase == "brd" and intent_type in ("discuss", "plan"):
        mode = CognitiveMode.DISCOVER
    elif phase == "brd" and intent_type in ("create", "update"):
        mode = CognitiveMode.SYNTHESIZE
    elif phase == "solution_flow" and intent_type in ("discuss", "review"):
        mode = CognitiveMode.REFINE
    elif phase == "solution_flow" and intent_type == "flow":
        mode = CognitiveMode.EXECUTE
    elif phase == "prototype":
        mode = CognitiveMode.EVOLVE
    elif intent_type == "search":
        mode = CognitiveMode.SYNTHESIZE
    else:
        mode = CognitiveMode.SYNTHESIZE

    # ── TEMPORAL: from project state ─────────────────────────────────
    hs = horizon_state or {}
    if phase == "prototype" and awareness.whats_discovered:
        temporal = TemporalEmphasis.RETROSPECTIVE
    elif hs.get("blocking_outcomes", 0) > 0:
        temporal = TemporalEmphasis.FORWARD_LOOKING
    elif page_context in ("overview", "brd:business_context"):
        temporal = TemporalEmphasis.FORWARD_LOOKING
    else:
        temporal = TemporalEmphasis.PRESENT_STATE

    # ── SCOPE: from page + intent ────────────────────────────────────
    if page_context in ("overview",) or intent_type == "plan":
        scope = Scope.PANORAMIC
    elif focused_entity and intent_type in ("update", "flow"):
        scope = Scope.ZOOMED_IN
    else:
        scope = Scope.CONTEXTUAL

    # ── CONFIDENCE POSTURE: from flow health ─────────────────────────
    active_flow = _get_active_flow(awareness, page_context, focused_entity)
    if active_flow:
        if active_flow.status == "confirmed":
            posture = ConfidencePosture.ASSERTIVE
        elif active_flow.status in ("ready", "structured"):
            posture = ConfidencePosture.CONFIRMING
        elif active_flow.status == "evolved":
            posture = ConfidencePosture.EVOLVING
        else:
            posture = ConfidencePosture.EXPLORATORY
    else:
        posture = {
            "brd": ConfidencePosture.EXPLORATORY,
            "solution_flow": ConfidencePosture.CONFIRMING,
            "prototype": ConfidencePosture.EVOLVING,
        }.get(phase, ConfidencePosture.EXPLORATORY)

    return CognitiveFrame(mode, temporal, scope, posture)


def _get_active_flow(
    awareness: ProjectAwareness,
    page_context: str | None,
    focused_entity: dict | None,
) -> FlowHealth | None:
    """Find the flow step currently in focus, if any."""
    if not awareness.flows:
        return None

    # If viewing a specific step, match by title
    if focused_entity and page_context == "brd:solution-flow":
        fe_data = focused_entity.get("data", {})
        step_title = fe_data.get("title", "")
        if step_title:
            for flow in awareness.flows:
                if flow.name == step_title:
                    return flow

    # Default to first non-confirmed flow (the one needing attention)
    for flow in awareness.flows:
        if flow.status not in ("confirmed",):
            return flow

    return awareness.flows[0] if awareness.flows else None


# ── Cognitive Instructions ─────────────────────────────────────────


MODE_INSTRUCTIONS = {
    CognitiveMode.DISCOVER: (
        "You're in discovery mode. Hunt for gaps in understanding, ask probing "
        "questions, and help the consultant uncover what they don't yet know. "
        "Every conversation is a chance to extract requirements data."
    ),
    CognitiveMode.SYNTHESIZE: (
        "Connect the dots. The consultant is building structure — help them see "
        "patterns, relationships, and implications across entities. Link new "
        "information to existing knowledge."
    ),
    CognitiveMode.REFINE: (
        "The narrative is taking shape. Tighten language, strengthen evidence "
        "chains, and identify remaining gaps. Push toward client-ready quality."
    ),
    CognitiveMode.EXECUTE: (
        "Precision mode. The consultant knows what they want — act on specific "
        "instructions quickly and accurately. Minimize back-and-forth."
    ),
    CognitiveMode.EVOLVE: (
        "New discoveries are reshaping the blueprint. Integrate prototype feedback "
        "and client reactions with existing requirements. Acknowledge what changed "
        "and why it matters."
    ),
}

TEMPORAL_INSTRUCTIONS = {
    TemporalEmphasis.RETROSPECTIVE: (
        "Weight what was learned over what was assumed. Reference decisions made, "
        "evidence gathered, and how understanding evolved."
    ),
    TemporalEmphasis.PRESENT_STATE: (
        "Focus on what's real right now. Weight current evidence and recent changes "
        "over historical assumptions."
    ),
    TemporalEmphasis.FORWARD_LOOKING: (
        "Think ahead. Consider horizons, dependencies, and what needs to happen "
        "next. Flag risks early and connect current work to future impact."
    ),
}

SCOPE_INSTRUCTIONS = {
    Scope.ZOOMED_IN: (
        "Focus on this specific entity — its fields, evidence, and immediate needs. "
        "Be precise and detailed."
    ),
    Scope.CONTEXTUAL: (
        "Consider this entity and its immediate relationships — linked flows, "
        "dependent features, relevant stakeholders."
    ),
    Scope.PANORAMIC: (
        "Take the wide view. Cross-entity patterns, project health, strategic "
        "positioning. Think like a senior consultant reviewing the whole engagement."
    ),
}

POSTURE_INSTRUCTIONS = {
    ConfidencePosture.ASSERTIVE: (
        "This area is well-understood. Make confident recommendations. Use language "
        "like 'You should...' and 'The evidence supports...'"
    ),
    ConfidencePosture.EXPLORATORY: (
        "This territory is still being mapped. Ask before assuming. Present options "
        "rather than conclusions. 'What if we...' and 'Have you considered...'"
    ),
    ConfidencePosture.CONFIRMING: (
        "Present your analysis for validation. 'Based on what we have...' and "
        "'Does this match your understanding?' Seek explicit confirmation."
    ),
    ConfidencePosture.EVOLVING: (
        "Acknowledge that understanding is shifting. 'Given what we just learned...' "
        "and 'This changes the picture because...' Be transparent about what moved."
    ),
}


def compile_cognitive_instructions(frame: CognitiveFrame) -> str:
    """Compile a unified instruction paragraph from the 4 dimensions."""
    parts = [
        MODE_INSTRUCTIONS[frame.mode],
        TEMPORAL_INSTRUCTIONS[frame.temporal],
        SCOPE_INSTRUCTIONS[frame.scope],
        POSTURE_INSTRUCTIONS[frame.posture],
    ]
    return "# How to Think Right Now\n" + " ".join(parts)


# ── Retrieval Plan ─────────────────────────────────────────────────


def compile_retrieval_plan(frame: CognitiveFrame) -> dict:
    """Shape retrieval based on how the model needs to think."""
    plan: dict[str, Any] = {}

    # Scope → graph depth
    if frame.scope == Scope.PANORAMIC:
        plan["graph_depth"] = 2
    elif frame.scope == Scope.CONTEXTUAL:
        plan["graph_depth"] = 1
    else:
        plan["graph_depth"] = 0

    # Temporal → recency weighting
    if frame.temporal == TemporalEmphasis.RETROSPECTIVE:
        plan["apply_recency"] = False
    else:
        plan["apply_recency"] = True

    # Posture → what to prioritize
    if frame.posture == ConfidencePosture.EVOLVING:
        plan["boost_recent_signals"] = True
    elif frame.posture == ConfidencePosture.ASSERTIVE:
        plan["boost_confirmed"] = True

    return plan


# ── Memory Formatting ──────────────────────────────────────────────


def format_memory_for_frame(frame: CognitiveFrame, confidence_state: dict) -> str | None:
    """Format memory context based on cognitive frame. Returns None if empty."""
    beliefs = confidence_state.get("low_confidence_beliefs", [])
    insights = confidence_state.get("recent_insights", [])

    if not beliefs and not insights:
        return None

    parts: list[str] = []

    if beliefs:
        belief_lines = []
        for b in beliefs[:3]:
            conf = b.get("confidence", 0)
            summary = b.get("summary", "")
            belief_lines.append(f"- [{conf:.0%}] {summary}")
        parts.append("Uncertain beliefs (verify before citing):\n" + "\n".join(belief_lines))

    if insights and frame.mode in (CognitiveMode.SYNTHESIZE, CognitiveMode.REFINE):
        insight_lines = [f"- {i.get('summary', '')}" for i in insights[:2]]
        parts.append("Recent insights:\n" + "\n".join(insight_lines))

    return "# Memory\n" + "\n".join(parts)


# ── Horizon Formatting ─────────────────────────────────────────────


def format_horizon_context(horizon_state: dict, frame: CognitiveFrame) -> str | None:
    """Format horizon intelligence for prompt inclusion. Returns None if empty."""
    summary = horizon_state.get("horizon_summary")
    if not summary:
        return None

    blocking = horizon_state.get("blocking_details", [])
    compounds = horizon_state.get("compound_decisions", 0)

    parts: list[str] = []

    # Horizon overview
    horizons = summary.get("horizons", [])
    if horizons:
        h_lines = []
        for h in horizons:
            readiness = h.get("readiness_pct", 0)
            outcomes = h.get("outcome_count", 0)
            ba = h.get("blocking_at_risk", 0)
            line = (
                f"H{h['number']}: {h.get('title', '')} "
                f"({readiness:.0f}% ready, {outcomes} outcomes)"
            )
            if ba > 0:
                line += f" ⚠ {ba} blocking"
            h_lines.append(line)
        parts.append("\n".join(h_lines))

    # Blocking details (if forward-looking)
    if blocking and frame.temporal == TemporalEmphasis.FORWARD_LOOKING:
        for b in blocking[:2]:
            parts.append(f"⚠ {b['horizon']}: {b['blocking_at_risk']} blocking outcomes")

    # Compound decisions
    if compounds > 0:
        parts.append(f"{compounds} compound decision{'s' if compounds > 1 else ''} (H1→H2/H3)")

    if not parts:
        return None

    return "# Horizons\n" + "\n".join(parts)


# ── Main Compiler ──────────────────────────────────────────────────


def compile_prompt(
    frame: CognitiveFrame,
    awareness: ProjectAwareness,
    page_context: str | None,
    focused_entity: dict | None,
    retrieval_context: str,
    solution_flow_ctx: Any | None,
    confidence_state: dict,
    horizon_state: dict,
    conversation_context: str | None = None,
    warm_memory: str = "",
) -> CompiledPrompt:
    """Compile a full prompt from cognitive frame + project state.

    Returns cached block (stable instructions) + dynamic block (per-request context).
    """
    from app.context.prompt_blocks import (
        BLOCK_ACTION_CARDS,
        BLOCK_CAPABILITIES,
        BLOCK_CONVERSATION_PATTERNS,
        BLOCK_IDENTITY,
        PAGE_GUIDANCE,
    )

    # ── CACHED BLOCK: Identity + Cognitive Instructions ──────────────
    cached_sections: list[str] = []

    # Identity (~200t)
    cached_sections.append(BLOCK_IDENTITY.format(project_name=awareness.project_name))

    # Cognitive instructions (~200-300t, varies by frame)
    cached_sections.append(compile_cognitive_instructions(frame))

    # Capabilities + action cards + patterns (~600t)
    cached_sections.append(BLOCK_CAPABILITIES)
    cached_sections.append(BLOCK_ACTION_CARDS)
    cached_sections.append(BLOCK_CONVERSATION_PATTERNS)

    # ── DYNAMIC BLOCK: State + Context ───────────────────────────────
    dynamic_sections: list[str] = []

    # Awareness snapshot (~300-500t, always — the peripheral vision)
    dynamic_sections.append(format_awareness_snapshot(awareness))

    # Warm memory (~0-200t, cross-conversation context)
    if warm_memory:
        dynamic_sections.append(warm_memory)

    # Page guidance (~0-460t, conditional on page)
    if page_context:
        guidance = PAGE_GUIDANCE.get(page_context)
        if guidance:
            dynamic_sections.append(f"# Page Guidance\n{guidance}")

    # Focused entity / solution flow detail (~0-300t)
    if solution_flow_ctx and getattr(solution_flow_ctx, "focused_step_prompt", None):
        sf_parts: list[str] = []
        if solution_flow_ctx.flow_summary_prompt:
            sf_parts.append(f"# Solution Flow Overview\n{solution_flow_ctx.flow_summary_prompt}")
        if solution_flow_ctx.focused_step_prompt:
            sf_parts.append(f"# Current Step Detail\n{solution_flow_ctx.focused_step_prompt}")
        if solution_flow_ctx.cross_step_prompt:
            sf_parts.append(f"# Flow Intelligence\n{solution_flow_ctx.cross_step_prompt}")
        if solution_flow_ctx.entity_change_delta:
            sf_parts.append(f"# Recent Entity Changes\n{solution_flow_ctx.entity_change_delta}")
        if solution_flow_ctx.confirmation_history:
            sf_parts.append(f"# Step History\n{solution_flow_ctx.confirmation_history}")
        dynamic_sections.extend(sf_parts)
    elif focused_entity:
        etype = focused_entity.get("type", "entity")
        edata = focused_entity.get("data", {})
        eid = edata.get("id", "")
        ename = edata.get("title") or edata.get("name") or ""
        if eid:
            line = f"# Currently Viewing\n{etype}: {eid}"
            if ename:
                line += f' ("{ename}")'
            egoal = edata.get("goal", "")
            if egoal:
                line += f"\nGoal: {egoal}"
            dynamic_sections.append(line)

    # Conversation starter context
    if conversation_context:
        dynamic_sections.append(
            "# Active Discussion Context\n"
            "The consultant opened chat from a conversation starter:\n"
            f"{conversation_context}"
        )

    # Memory context (~0-150t, conditional on confidence state)
    memory_block = format_memory_for_frame(frame, confidence_state)
    if memory_block:
        dynamic_sections.append(memory_block)

    # Horizon intelligence (~0-150t, conditional)
    if horizon_state.get("is_crystallized"):
        horizon_block = format_horizon_context(horizon_state, frame)
        if horizon_block:
            dynamic_sections.append(horizon_block)

    # Retrieval evidence (fills remaining budget, ~500-1500t)
    if retrieval_context:
        dynamic_sections.append(
            "# Retrieved Evidence\n"
            "Use this evidence to answer questions directly — cite specific quotes.\n"
            "Tags: (strong/moderate/weak) = relationship strength, "
            "(confirmed/review/inferred/stale) = certainty, "
            "(contradicted) = conflicting evidence. 'via X' = indirect.\n"
            f"{retrieval_context}"
        )

    return CompiledPrompt(
        cached_block="\n\n".join(cached_sections),
        dynamic_block="\n\n".join(dynamic_sections),
        retrieval_plan=compile_retrieval_plan(frame),
        active_frame=frame.label,
    )
