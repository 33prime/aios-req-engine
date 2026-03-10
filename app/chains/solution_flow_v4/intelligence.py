# ruff: noqa: E501 — prompt text blocks and DB queries have natural line lengths
"""Phase 0: Intelligence Assembly — Load ALL project intelligence in parallel.

Loads the existing 7 BRD queries PLUS 10 intelligence sources that v3 never used:
- entity_dependencies → data flow graph, hidden connections
- enrichment_revisions → field stability / confidence scoring
- memory_nodes → beliefs, tensions, contradictions, insights
- project_open_questions → unresolved knowledge gaps
- stakeholder_assignments → who validates what, verdict history
- client_exploration → assumption responses (agree/disagree/refine)
- creative_brief → client narrative, focus areas, industry context
- call_intelligence → strategy briefs, mission themes, critical requirements
- project_horizons → H1/H2/H3 alignment per feature
- unlocks → discovered value opportunities

All queries run in parallel via asyncio.gather. Output is a structured
FlowIntelligenceContext — not flat text.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


# =============================================================================
# Structured Intelligence Context
# =============================================================================


@dataclass
class FlowIntelligenceContext:
    """Structured intelligence for solution flow generation.

    Every field is populated in parallel by Phase 0.
    Downstream phases filter what they need from this object.
    """

    # Core BRD (existing 7 queries)
    project: dict[str, Any] | None = None
    personas: list[dict[str, Any]] = field(default_factory=list)
    workflows: list[dict[str, Any]] = field(default_factory=list)
    features: list[dict[str, Any]] = field(default_factory=list)
    data_entities: list[dict[str, Any]] = field(default_factory=list)
    constraints: list[dict[str, Any]] = field(default_factory=list)
    drivers: list[dict[str, Any]] = field(default_factory=list)

    # Intelligence Layer (NEW)
    entity_dependencies: list[dict[str, Any]] = field(default_factory=list)
    enrichment_revisions: list[dict[str, Any]] = field(default_factory=list)
    memory_beliefs: list[dict[str, Any]] = field(default_factory=list)
    memory_insights: list[dict[str, Any]] = field(default_factory=list)
    memory_contradictions: list[dict[str, Any]] = field(default_factory=list)
    open_questions: list[dict[str, Any]] = field(default_factory=list)
    stakeholder_assignments: list[dict[str, Any]] = field(default_factory=list)
    client_responses: list[dict[str, Any]] = field(default_factory=list)
    creative_brief: dict[str, Any] | None = None
    strategy_briefs: list[dict[str, Any]] = field(default_factory=list)
    horizons: dict[str, str] = field(default_factory=dict)  # feature_id → H1/H2/H3
    unlocks: list[dict[str, Any]] = field(default_factory=list)

    # Retrieval evidence
    retrieval_evidence: str = ""

    # Computed metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def future_workflows(self) -> list[dict[str, Any]]:
        return [w for w in self.workflows if w.get("state_type") == "future"]

    @property
    def current_workflows(self) -> list[dict[str, Any]]:
        return [w for w in self.workflows if w.get("state_type") != "future"]

    @property
    def goals(self) -> list[dict[str, Any]]:
        return [d for d in self.drivers if d.get("driver_type") == "goal"]

    @property
    def pain_points(self) -> list[dict[str, Any]]:
        return [d for d in self.drivers if d.get("driver_type") == "pain"]

    @property
    def confirmed_features(self) -> list[dict[str, Any]]:
        return [
            f
            for f in self.features
            if f.get("confirmation_status") in ("confirmed_consultant", "confirmed_client")
        ]

    def has_intelligence(self) -> bool:
        """Whether any intelligence beyond basic BRD was loaded."""
        return bool(
            self.entity_dependencies
            or self.memory_beliefs
            or self.memory_insights
            or self.open_questions
            or self.client_responses
            or self.creative_brief
            or self.strategy_briefs
            or self.unlocks
        )


# =============================================================================
# Parallel Intelligence Loaders
# =============================================================================


async def assemble_intelligence(project_id: UUID) -> FlowIntelligenceContext:
    """Load ALL project intelligence in parallel.

    Returns a structured FlowIntelligenceContext with every data source populated.
    Failures in intelligence queries are silently swallowed — BRD data is always loaded.
    """
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()
    pid = str(project_id)
    ctx = FlowIntelligenceContext()

    # ── Core BRD Queries ────────────────────────────────────────────────────

    def _q_project():
        try:
            r = (
                supabase.table("projects")
                .select("name, vision, project_type")
                .eq("id", pid)
                .maybe_single()
                .execute()
            )
            return r.data if r else None
        except Exception as e:
            if "204" in str(e):
                return None
            raise

    def _q_personas():
        return (
            supabase.table("personas")
            .select("id, name, role, goals, pain_points, confirmation_status")
            .eq("project_id", pid)
            .execute()
            .data
            or []
        )

    def _q_workflows():
        wfs = (
            supabase.table("workflows")
            .select("id, name, description, state_type, confirmation_status")
            .eq("project_id", pid)
            .execute()
            .data
            or []
        )
        for wf in wfs:
            steps = (
                supabase.table("vp_steps")
                .select(
                    "id, step_index, label, description, automation_level, "
                    "operation_type, time_minutes, pain_description"
                )
                .eq("workflow_id", wf["id"])
                .order("step_index")
                .execute()
                .data
                or []
            )
            wf["steps"] = steps
        return wfs

    def _q_features():
        return (
            supabase.table("features")
            .select("id, name, overview, priority_group, category, confirmation_status")
            .eq("project_id", pid)
            .execute()
            .data
            or []
        )

    def _q_data_entities():
        return (
            supabase.table("data_entities")
            .select("id, name, description, fields, entity_category")
            .eq("project_id", pid)
            .execute()
            .data
            or []
        )

    def _q_constraints():
        return (
            supabase.table("constraints")
            .select("id, title, description, constraint_type")
            .eq("project_id", pid)
            .execute()
            .data
            or []
        )

    def _q_drivers():
        return (
            supabase.table("business_drivers")
            .select("id, driver_type, title, description, severity")
            .eq("project_id", pid)
            .execute()
            .data
            or []
        )

    # ── Intelligence Layer Queries ──────────────────────────────────────────

    def _q_entity_deps():
        try:
            resp = (
                supabase.table("entity_dependencies")
                .select(
                    "source_entity_type, source_entity_id, target_entity_type, "
                    "target_entity_id, dependency_type, strength, confidence"
                )
                .eq("project_id", pid)
                .eq("disputed", False)
                .execute()
            )
            return resp.data or []
        except Exception:
            return []

    def _q_enrichment_revisions():
        try:
            resp = (
                supabase.table("enrichment_revisions")
                .select(
                    "entity_type, entity_id, entity_label, revision_type, "
                    "new_signals_count, new_facts_count, diff_summary, created_at"
                )
                .eq("project_id", pid)
                .order("created_at", desc=True)
                .limit(100)
                .execute()
            )
            return resp.data or []
        except Exception:
            return []

    def _q_memory_beliefs():
        try:
            resp = (
                supabase.table("memory_nodes")
                .select(
                    "id, content, summary, confidence, source_type, "
                    "linked_entity_type, linked_entity_id, belief_domain"
                )
                .eq("project_id", pid)
                .eq("node_type", "belief")
                .eq("is_active", True)
                .order("confidence", desc=True)
                .limit(50)
                .execute()
            )
            return resp.data or []
        except Exception:
            return []

    def _q_memory_insights():
        try:
            resp = (
                supabase.table("memory_nodes")
                .select("id, content, summary, insight_type, confidence")
                .eq("project_id", pid)
                .eq("node_type", "insight")
                .eq("is_active", True)
                .limit(30)
                .execute()
            )
            return resp.data or []
        except Exception:
            return []

    def _q_open_questions():
        try:
            resp = (
                supabase.table("project_open_questions")
                .select(
                    "id, question, why_it_matters, context, priority, category, "
                    "target_entity_type, target_entity_id, status"
                )
                .eq("project_id", pid)
                .eq("status", "open")
                .order("priority")
                .limit(30)
                .execute()
            )
            return resp.data or []
        except Exception:
            return []

    def _q_stakeholder_assignments():
        try:
            resp = (
                supabase.table("stakeholder_assignments")
                .select("entity_type, entity_id, status, priority")
                .eq("project_id", pid)
                .execute()
            )
            return resp.data or []
        except Exception:
            return []

    def _q_client_responses():
        try:
            # Get latest exploration session
            session_resp = (
                supabase.table("prototype_sessions")
                .select("id")
                .eq("project_id", pid)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            sessions = session_resp.data or []
            if not sessions:
                return []
            session_id = sessions[0]["id"]
            resp = (
                supabase.table("client_assumption_responses")
                .select("epic_index, assumption_index, response, text")
                .eq("session_id", session_id)
                .execute()
            )
            return resp.data or []
        except Exception:
            return []

    def _q_creative_brief():
        try:
            resp = (
                supabase.table("creative_briefs")
                .select("client_name, industry, focus_areas, competitors")
                .eq("project_id", pid)
                .maybe_single()
                .execute()
            )
            return resp.data if resp else None
        except Exception as e:
            if "204" in str(e):
                return None
            return None

    def _q_strategy_briefs():
        try:
            resp = (
                supabase.table("call_strategy_briefs")
                .select(
                    "mission_themes, critical_requirements, focus_areas, "
                    "ambiguity_snapshot, meeting_frame"
                )
                .eq("project_id", pid)
                .order("created_at", desc=True)
                .limit(3)
                .execute()
            )
            return resp.data or []
        except Exception:
            return []

    def _q_horizons():
        try:
            resp = (
                supabase.table("project_horizons")
                .select("feature_id, horizon")
                .eq("project_id", pid)
                .execute()
            )
            return {
                row["feature_id"]: row["horizon"]
                for row in (resp.data or [])
                if row.get("feature_id") and row.get("horizon")
            }
        except Exception:
            return {}

    def _q_unlocks():
        try:
            resp = (
                supabase.table("unlocks")
                .select("title, description, tier, impact_type, status, confirmation_status")
                .eq("project_id", pid)
                .in_("status", ["generated", "promoted"])
                .order("tier")
                .limit(20)
                .execute()
            )
            return resp.data or []
        except Exception:
            return []

    # ── Run ALL queries in parallel ─────────────────────────────────────────

    results = await asyncio.gather(
        # Core BRD (7)
        asyncio.to_thread(_q_project),
        asyncio.to_thread(_q_personas),
        asyncio.to_thread(_q_workflows),
        asyncio.to_thread(_q_features),
        asyncio.to_thread(_q_data_entities),
        asyncio.to_thread(_q_constraints),
        asyncio.to_thread(_q_drivers),
        # Intelligence (10)
        asyncio.to_thread(_q_entity_deps),
        asyncio.to_thread(_q_enrichment_revisions),
        asyncio.to_thread(_q_memory_beliefs),
        asyncio.to_thread(_q_memory_insights),
        asyncio.to_thread(_q_open_questions),
        asyncio.to_thread(_q_stakeholder_assignments),
        asyncio.to_thread(_q_client_responses),
        asyncio.to_thread(_q_creative_brief),
        asyncio.to_thread(_q_strategy_briefs),
        asyncio.to_thread(_q_horizons),
        asyncio.to_thread(_q_unlocks),
        return_exceptions=True,
    )

    # Unpack — treat exceptions as empty results
    def _safe(result, default=None):
        if isinstance(result, Exception):
            logger.debug(f"Intelligence query failed: {result}")
            return default if default is not None else []
        return result

    # Core BRD
    ctx.project = _safe(results[0], default=None)
    ctx.personas = _safe(results[1]) or []
    ctx.workflows = _safe(results[2]) or []
    ctx.features = _safe(results[3]) or []
    ctx.data_entities = _safe(results[4]) or []
    ctx.constraints = _safe(results[5]) or []
    ctx.drivers = _safe(results[6]) or []

    # Intelligence
    ctx.entity_dependencies = _safe(results[7]) or []
    ctx.enrichment_revisions = _safe(results[8]) or []
    ctx.memory_beliefs = _safe(results[9]) or []
    ctx.memory_insights = _safe(results[10]) or []
    ctx.open_questions = _safe(results[11]) or []
    ctx.stakeholder_assignments = _safe(results[12]) or []
    ctx.client_responses = _safe(results[13]) or []
    ctx.creative_brief = _safe(results[14], default=None)
    ctx.strategy_briefs = _safe(results[15]) or []
    ctx.horizons = _safe(results[16], default={}) or {}
    ctx.unlocks = _safe(results[17]) or []

    # ── Retrieval Enrichment ────────────────────────────────────────────────

    try:
        from app.core.retrieval import retrieve
        from app.core.retrieval_format import format_retrieval_for_context

        retrieval_result = await retrieve(
            query="pain points, goals, constraints, and desired outcomes for workflows",
            project_id=pid,
            max_rounds=2,
            entity_types=[
                "workflow",
                "feature",
                "constraint",
                "data_entity",
                "persona",
                "business_driver",
            ],
            evaluation_criteria="Need: current pain, desired outcome, user goals, technical constraints",
            context_hint="generating solution architecture",
            skip_reranking=True,
            graph_depth=2,
            apply_recency=True,
            apply_confidence=True,
        )
        ctx.retrieval_evidence = (
            format_retrieval_for_context(retrieval_result, style="generation", max_tokens=2000)
            or ""
        )
    except Exception:
        logger.debug("Retrieval enrichment failed (non-fatal)")

    # ── Detect contradicting beliefs via memory edges ───────────────────────

    if ctx.memory_beliefs:
        try:
            belief_ids = [b["id"] for b in ctx.memory_beliefs[:20]]
            resp = (
                supabase.table("memory_edges")
                .select("from_node_id, to_node_id, edge_type, rationale")
                .eq("edge_type", "contradicts")
                .in_("from_node_id", belief_ids)
                .execute()
            )
            ctx.memory_contradictions = resp.data or []
        except Exception:
            pass

    # ── Compute metadata ────────────────────────────────────────────────────

    ctx.metadata = {
        "workflow_count": len(ctx.workflows),
        "future_workflow_count": len(ctx.future_workflows),
        "persona_count": len(ctx.personas),
        "feature_count": len(ctx.features),
        "driver_count": len(ctx.drivers),
        "intelligence_sources": sum(
            [
                1 if ctx.entity_dependencies else 0,
                1 if ctx.enrichment_revisions else 0,
                1 if ctx.memory_beliefs else 0,
                1 if ctx.memory_insights else 0,
                1 if ctx.open_questions else 0,
                1 if ctx.client_responses else 0,
                1 if ctx.creative_brief else 0,
                1 if ctx.strategy_briefs else 0,
                1 if ctx.unlocks else 0,
            ]
        ),
    }

    logger.info(
        f"Intelligence assembled: {ctx.metadata['workflow_count']} workflows, "
        f"{ctx.metadata['feature_count']} features, "
        f"{ctx.metadata['intelligence_sources']}/9 intelligence sources loaded"
    )

    return ctx


# =============================================================================
# Intelligence Formatting — Compact text for LLM consumption
# =============================================================================


def format_intelligence_for_insights(ctx: FlowIntelligenceContext) -> str:
    """Format intelligence context for Phase 1 Insight Synthesis (~4K tokens).

    Prioritizes signals that reveal the unseen/unsaid:
    - Contradicting beliefs, low-confidence areas
    - Entity dependency patterns
    - Open questions and knowledge gaps
    - Client feedback patterns
    - Strategic themes from calls
    """
    sections: list[str] = []

    # Memory beliefs — especially low-confidence and contradictions
    if ctx.memory_beliefs:
        parts = ["<beliefs>"]
        for b in ctx.memory_beliefs[:15]:
            conf = b.get("confidence", 0)
            summary = b.get("summary") or b.get("content", "")[:120]
            entity_info = ""
            if b.get("linked_entity_type") and b.get("linked_entity_id"):
                entity_info = f" [{b['linked_entity_type']}]"
            parts.append(f"- [{conf:.0%}]{entity_info} {summary}")
        if ctx.memory_contradictions:
            parts.append("\nContradictions:")
            for c in ctx.memory_contradictions[:5]:
                rationale = c.get("rationale", "")[:100]
                parts.append(f"- {rationale}")
        parts.append("</beliefs>")
        sections.append("\n".join(parts))

    # Entity dependency graph — summarized patterns
    if ctx.entity_dependencies:
        parts = ["<dependency_graph>"]
        # Count by type
        type_counts: dict[str, int] = {}
        for dep in ctx.entity_dependencies:
            dt = dep.get("dependency_type", "unknown")
            type_counts[dt] = type_counts.get(dt, 0) + 1

        parts.append(f"Total links: {len(ctx.entity_dependencies)}")
        for dt, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            parts.append(f"  {dt}: {count}")

        # Key chains: workflow → feature → data_entity
        wf_feature_links = [
            d
            for d in ctx.entity_dependencies
            if (
                d.get("source_entity_type") == "workflow"
                and d.get("target_entity_type") == "feature"
            )
            or (
                d.get("source_entity_type") == "feature"
                and d.get("target_entity_type") == "workflow"
            )
        ]
        if wf_feature_links:
            parts.append(f"\nWorkflow↔Feature links: {len(wf_feature_links)}")

        feature_data_links = [
            d
            for d in ctx.entity_dependencies
            if (
                d.get("source_entity_type") == "feature"
                and d.get("target_entity_type") == "data_entity"
            )
            or (
                d.get("source_entity_type") == "data_entity"
                and d.get("target_entity_type") == "feature"
            )
        ]
        if feature_data_links:
            parts.append(f"Feature↔DataEntity links: {len(feature_data_links)}")

        parts.append("</dependency_graph>")
        sections.append("\n".join(parts))

    # Open questions — knowledge gaps that need attention
    if ctx.open_questions:
        parts = ["<open_questions>"]
        for q in ctx.open_questions[:10]:
            priority = q.get("priority", "medium")
            question = q.get("question", "")[:120]
            target = q.get("target_entity_type", "")
            parts.append(f"- [{priority}]{f' ({target})' if target else ''} {question}")
        parts.append("</open_questions>")
        sections.append("\n".join(parts))

    # Enrichment stability — volatile entities
    if ctx.enrichment_revisions:
        # Count revisions per entity
        entity_revision_counts: dict[str, int] = {}
        for rev in ctx.enrichment_revisions:
            key = f"{rev.get('entity_type', '')}:{rev.get('entity_label', '')}"
            entity_revision_counts[key] = entity_revision_counts.get(key, 0) + 1

        volatile = [(k, c) for k, c in entity_revision_counts.items() if c >= 3]
        if volatile:
            parts = ["<volatile_entities>"]
            for key, count in sorted(volatile, key=lambda x: -x[1])[:8]:
                parts.append(f"- {key}: {count} revisions")
            parts.append("</volatile_entities>")
            sections.append("\n".join(parts))

    # Client feedback — assumption responses
    if ctx.client_responses:
        parts = ["<client_feedback>"]
        by_response: dict[str, int] = {}
        for r in ctx.client_responses:
            resp = r.get("response", "unknown")
            by_response[resp] = by_response.get(resp, 0) + 1

        for resp, count in sorted(by_response.items(), key=lambda x: -x[1]):
            parts.append(f"- {resp}: {count}")

        # Show specific disagreements/refinements
        disagreements = [
            r for r in ctx.client_responses if r.get("response") in ("disagree", "refine")
        ]
        for d in disagreements[:5]:
            text = d.get("text", "")[:100]
            if text:
                parts.append(f"  → {d.get('response')}: {text}")
        parts.append("</client_feedback>")
        sections.append("\n".join(parts))

    # Strategy themes from calls
    if ctx.strategy_briefs:
        parts = ["<strategy_themes>"]
        for brief in ctx.strategy_briefs[:2]:
            themes = brief.get("mission_themes") or []
            if themes and isinstance(themes, list):
                for t in themes[:3]:
                    parts.append(f"- Theme: {t[:100] if isinstance(t, str) else str(t)[:100]}")
            critical = brief.get("critical_requirements") or []
            if critical and isinstance(critical, list):
                for c in critical[:3]:
                    parts.append(f"- Critical: {c[:100] if isinstance(c, str) else str(c)[:100]}")
        parts.append("</strategy_themes>")
        sections.append("\n".join(parts))

    # Creative brief context
    if ctx.creative_brief:
        parts = ["<creative_brief>"]
        if ctx.creative_brief.get("industry"):
            parts.append(f"Industry: {ctx.creative_brief['industry']}")
        focus = ctx.creative_brief.get("focus_areas") or []
        if focus:
            parts.append(f"Focus areas: {', '.join(str(f) for f in focus[:5])}")
        parts.append("</creative_brief>")
        sections.append("\n".join(parts))

    # Unlocks — value opportunities
    if ctx.unlocks:
        parts = ["<unlocks>"]
        for u in ctx.unlocks[:8]:
            tier = u.get("tier", "?")
            impact = u.get("impact_type", "")
            parts.append(f"- [T{tier}/{impact}] {u.get('title', '')[:80]}")
        parts.append("</unlocks>")
        sections.append("\n".join(parts))

    # Horizons summary
    if ctx.horizons:
        h_counts = {"H1": 0, "H2": 0, "H3": 0}
        for h in ctx.horizons.values():
            h_counts[h] = h_counts.get(h, 0) + 1
        parts = ["<horizons>"]
        parts.append(f"H1: {h_counts['H1']} features, H2: {h_counts['H2']}, H3: {h_counts['H3']}")
        parts.append("</horizons>")
        sections.append("\n".join(parts))

    return "\n\n".join(sections)


def format_brd_for_architecture(ctx: FlowIntelligenceContext) -> str:
    """Format core BRD data for Phase 2 Flow Architecture (~6K tokens).

    Compact but complete — everything Sonnet needs to plan the step structure.
    """
    sections: list[str] = []

    # Project
    if ctx.project:
        parts = ["<project>"]
        if ctx.project.get("name"):
            parts.append(f"Name: {ctx.project['name']}")
        if ctx.project.get("project_type"):
            parts.append(f"Type: {ctx.project['project_type']}")
        if ctx.project.get("vision"):
            parts.append(f"Vision: {ctx.project['vision'][:500]}")
        parts.append("</project>")
        sections.append("\n".join(parts))

    # Personas
    if ctx.personas:
        parts = ["<personas>"]
        for p in sorted(
            ctx.personas,
            key=lambda x: (
                0
                if x.get("confirmation_status") in ("confirmed_consultant", "confirmed_client")
                else 1
            ),
        ):
            parts.append(f"- {p.get('name', '?')} (id:{p['id']}) — {p.get('role', '?')}")
            goals = p.get("goals") or []
            if isinstance(goals, list) and goals:
                parts.append(f"  Goals: {', '.join(str(g) for g in goals[:3])}")
            pains = p.get("pain_points") or []
            if isinstance(pains, list) and pains:
                parts.append(f"  Pains: {', '.join(str(pp) for pp in pains[:3])}")
        parts.append("</personas>")
        sections.append("\n".join(parts))

    # Drivers
    if ctx.drivers:
        parts = ["<drivers>"]
        for d in ctx.goals:
            parts.append(f"- [goal] {d.get('description', d.get('title', '?'))[:150]}")
        for d in ctx.pain_points:
            parts.append(f"- [pain] {d.get('description', d.get('title', '?'))[:150]}")
        parts.append("</drivers>")
        sections.append("\n".join(parts))

    # Future-state workflows (full detail)
    if ctx.future_workflows:
        parts = ["<workflows_future>"]
        for wf in sorted(
            ctx.future_workflows,
            key=lambda x: (
                0
                if x.get("confirmation_status") in ("confirmed_consultant", "confirmed_client")
                else 1
            ),
        ):
            parts.append(f"\n## {wf.get('name', '?')} (id:{wf['id']})")
            if wf.get("description"):
                parts.append(f"  {wf['description'][:300]}")
            for step in wf.get("steps", []):
                auto = step.get("automation_level", "manual")
                desc = f" — {step['description'][:100]}" if step.get("description") else ""
                parts.append(
                    f"  {step.get('step_index', '?')}. {step.get('label', '?')} [{auto}]{desc}"
                )
        parts.append("</workflows_future>")
        sections.append("\n".join(parts))

    # Current-state workflows (pain points only)
    if ctx.current_workflows:
        parts = ["<workflows_current>"]
        for wf in ctx.current_workflows:
            pain_steps = [s for s in wf.get("steps", []) if s.get("pain_description")]
            if pain_steps:
                parts.append(f"## {wf.get('name', '?')}")
                for step in pain_steps:
                    parts.append(f"  - {step.get('label', '?')}: {step['pain_description'][:100]}")
        parts.append("</workflows_current>")
        sections.append("\n".join(parts))

    # Features grouped by priority
    if ctx.features:
        parts = ["<features>"]
        by_priority: dict[str, list] = {}
        for f in ctx.features:
            pri = f.get("priority_group", "unset") or "unset"
            by_priority.setdefault(pri, []).append(f)

        for pri in ["must_have", "should_have", "could_have", "unset"]:
            group = by_priority.get(pri, [])
            if group:
                parts.append(f"\n[{pri}]")
                for f in group:
                    h = ctx.horizons.get(f["id"], "")
                    h_tag = f" {h}" if h else ""
                    parts.append(f"- {f.get('name', '?')} (id:{f['id']}){h_tag}")
                    if f.get("overview"):
                        parts.append(f"  {f['overview'][:120]}")
        parts.append("</features>")
        sections.append("\n".join(parts))

    # Data entities
    if ctx.data_entities:
        parts = ["<data_entities>"]
        for de in ctx.data_entities:
            parts.append(f"- {de.get('name', '?')} (id:{de['id']})")
            fields = de.get("fields") or []
            if fields and isinstance(fields, list):
                field_names = [
                    fi.get("name", "?") if isinstance(fi, dict) else str(fi) for fi in fields[:8]
                ]
                parts.append(f"  Fields: {', '.join(field_names)}")
        parts.append("</data_entities>")
        sections.append("\n".join(parts))

    # Constraints
    if ctx.constraints:
        parts = ["<constraints>"]
        for c in ctx.constraints:
            parts.append(
                f"- [{c.get('constraint_type', '?')}] {c.get('title', c.get('description', '?'))[:120]}"
            )
        parts.append("</constraints>")
        sections.append("\n".join(parts))

    return "\n\n".join(sections)
