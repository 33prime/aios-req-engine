"""Build Intelligence Layer — Sonnet planner + parallel Haiku detail builders.

Phase 1: Sonnet analyzes all solution flow steps with ai_config → plans agent team
Phase 2: Haiku (parallel) fills in each agent — tools, autonomy, sample I/O, narratives
Phase 3: Persist to agents + agent_tools tables

Triggered by: POST /intelligence-layer/generate
"""

from __future__ import annotations

import asyncio
import json
import time
from uuid import UUID

from anthropic import AsyncAnthropic

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.schemas_agents_v2 import (
    AgentResponse,
    IntelligenceLayerResponse,
)
from app.db.agents import create_agent, delete_project_agents, list_agents

logger = get_logger(__name__)

# ═══════════════════════════════════════════════
# Tool schemas for Sonnet (planning) and Haiku (detail building)
# ═══════════════════════════════════════════════

PLAN_TOOL = {
    "name": "submit_agent_plan",
    "description": "Submit the planned agent team.",
    "input_schema": {
        "type": "object",
        "required": ["agents"],
        "properties": {
            "agents": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["temp_id", "name", "icon", "agent_type",
                                 "role_description", "source_step_id"],
                    "properties": {
                        "temp_id": {"type": "string",
                                    "description": "Temporary ID for wiring deps (e.g. 'a1')"},
                        "name": {"type": "string"},
                        "icon": {"type": "string",
                                 "description": "Single emoji"},
                        "agent_type": {
                            "type": "string",
                            "enum": ["classifier", "matcher", "predictor",
                                     "watcher", "generator", "processor"],
                        },
                        "role_description": {
                            "type": "string",
                            "description": "1-2 sentence human-friendly description",
                        },
                        "source_step_id": {
                            "type": "string",
                            "description": "Solution flow step ID this agent derives from",
                        },
                        "depends_on": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "temp_ids of agents this depends on",
                        },
                        "feeds_into": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "temp_ids of agents this feeds",
                        },
                        "partner_role": {"type": "string"},
                    },
                },
                "minItems": 3,
                "maxItems": 8,
            },
        },
    },
}

DETAIL_TOOL = {
    "name": "submit_agent_details",
    "description": "Submit full agent details including tools, autonomy, and sample I/O.",
    "input_schema": {
        "type": "object",
        "required": ["tools", "autonomy", "data_sources", "processing_steps",
                     "sample_input", "sample_output", "chat_intro",
                     "chat_suggestions", "cascade_effects"],
        "properties": {
            "tools": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "icon", "description", "example",
                                 "data_touches", "reliability"],
                    "properties": {
                        "name": {"type": "string"},
                        "icon": {"type": "string", "description": "Single emoji"},
                        "description": {"type": "string",
                                        "description": "One sentence"},
                        "example": {
                            "type": "string",
                            "description": "Concrete narrative example of this tool in action",
                        },
                        "data_touches": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "reliability": {
                            "type": "integer",
                            "description": "Estimated reliability 0-100",
                        },
                    },
                },
                "minItems": 3,
                "maxItems": 5,
            },
            "autonomy": {
                "type": "object",
                "required": ["level", "can_do", "needs_approval", "cannot_do"],
                "properties": {
                    "level": {"type": "integer",
                              "description": "Autonomy percentage 0-100"},
                    "can_do": {"type": "array", "items": {"type": "string"}},
                    "needs_approval": {"type": "array",
                                       "items": {"type": "string"}},
                    "cannot_do": {"type": "array",
                                  "items": {"type": "string"}},
                },
            },
            "partner": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "initials": {"type": "string"},
                    "color": {"type": "string"},
                    "relationship": {"type": "string",
                                     "description": "2-3 sentences"},
                    "escalations": {"type": "string"},
                },
            },
            "data_sources": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "access": {"type": "string",
                                   "enum": ["read", "read/write", "query",
                                            "subscribe"]},
                    },
                },
            },
            "processing_steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["label", "tool_icon", "tool_name"],
                    "properties": {
                        "label": {"type": "string"},
                        "tool_icon": {"type": "string"},
                        "tool_name": {"type": "string"},
                    },
                },
                "minItems": 4,
                "maxItems": 6,
            },
            "sample_input": {
                "type": "string",
                "description": "Realistic 1-2 sentence scenario description",
            },
            "sample_output": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["key"],
                    "properties": {
                        "key": {"type": "string"},
                        "val": {"type": "string"},
                        "list": {"type": "array",
                                 "items": {"type": "string"}},
                        "badge": {
                            "type": "string",
                            "enum": ["high", "moderate", "low",
                                     "recommended", "conditional"],
                        },
                    },
                },
                "minItems": 4,
                "maxItems": 7,
            },
            "chat_intro": {
                "type": "string",
                "description": "Agent's greeting (1-3 sentences, first person)",
            },
            "chat_suggestions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "4 suggested questions for the client",
                "minItems": 3,
                "maxItems": 5,
            },
            "cascade_effects": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "target_agent_name": {"type": "string"},
                        "effect_description": {"type": "string"},
                    },
                },
            },
            "transform_before": {"type": "string"},
            "transform_after": {"type": "string"},
            "technique": {
                "type": "string",
                "enum": ["llm", "classification", "embeddings",
                         "rules", "hybrid"],
            },
            "rhythm": {
                "type": "string",
                "enum": ["triggered", "always_on", "on_demand", "periodic"],
            },
            "automation_rate": {"type": "integer"},
            "maturity": {
                "type": "string",
                "enum": ["learning", "reliable", "expert"],
            },
        },
    },
}

# ═══════════════════════════════════════════════
# System prompts
# ═══════════════════════════════════════════════

PLANNER_SYSTEM = """\
You are an AI systems architect. You analyze a product's solution flow \
and identify the AI agents that power it.

RULES:
- Only create agents for steps that have meaningful AI intelligence — \
data transforms, classifications, scoring, monitoring, generation.
- Do NOT create agents for simple CRUD operations, form submissions, \
or basic UI interactions.
- Agents should feel like team members with clear responsibilities.
- Name agents with short, memorable names (2-3 words max).
- Use a single emoji icon that represents the agent's function.
- Identify dependencies: which agents feed data to which others.
- Identify the human partner for each agent (from the step's actors).
- Aim for 3-7 agents. Quality over quantity."""

DETAIL_BUILDER_SYSTEM = """\
You are building the detailed specification for an AI agent. \
Given the agent plan and its source solution flow step, generate \
rich details that make the agent feel real and tangible.

RULES:
- Tools should be specific capabilities, not vague categories. \
Each tool has a concrete example showing it in action.
- Autonomy breakdown: what can it do alone (routine operations), \
what needs human approval (judgment calls), what it absolutely cannot do.
- Sample output should be NARRATIVE — readable by a non-technical client. \
Write like an intelligence brief, not a data dump.
- Processing steps show the agent's workflow. Each step links to a tool.
- Chat intro should be warm and approachable, in first person.
- Cascade effects: if this agent's output changes, what downstream \
agents are affected and how?
- Be domain-specific. Use realistic names, numbers, terminology."""


# ═══════════════════════════════════════════════
# Main pipeline
# ═══════════════════════════════════════════════


async def build_intelligence_layer(
    project_id: UUID,
) -> IntelligenceLayerResponse:
    """Build the full intelligence layer for a project.

    Phase 1: Sonnet plans the agent team
    Phase 2: Haiku builds details for each agent (parallel)
    Phase 3: Persist to DB
    """
    from app.db.solution_flow import get_flow_overview, list_flow_steps

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    t_start = time.monotonic()

    # Load solution flow (overview for metadata)
    flow = get_flow_overview(project_id)
    if not flow or not flow.get("steps"):
        raise ValueError("No solution flow found — generate one first")

    # Load FULL step data (with ai_config) — overview strips it
    all_steps = list_flow_steps(flow["id"])

    # Filter steps with ai_config
    ai_steps = []
    for step in all_steps:
        ai_config = step.get("ai_config") or {}
        if ai_config.get("role") or ai_config.get("ai_role"):
            ai_steps.append(step)

    if len(ai_steps) < 2:
        raise ValueError(
            f"Only {len(ai_steps)} AI-capable steps found. "
            f"Need at least 2 to build an intelligence layer."
        )

    # Load project context for richer generation
    project_context = _build_project_context(project_id, flow)

    # ── Phase 1: Sonnet Plans ──
    logger.info(f"Phase 1: Planning agents from {len(ai_steps)} AI steps")
    agent_plans = await _plan_agents(client, ai_steps, project_context, settings)

    if not agent_plans:
        raise ValueError("Agent planning produced no results")

    logger.info(f"Phase 1 complete: {len(agent_plans)} agents planned")

    # ── Phase 2: Haiku Detail Builders (parallel) ──
    logger.info(f"Phase 2: Building details for {len(agent_plans)} agents")

    step_map = {s["id"]: s for s in all_steps}
    detail_tasks = []
    for plan in agent_plans:
        step = step_map.get(plan.get("source_step_id", ""))
        detail_tasks.append(
            _build_agent_details(client, plan, step, project_context, settings)
        )

    details = await asyncio.gather(*detail_tasks, return_exceptions=True)

    # ── Phase 3: Persist ──
    logger.info("Phase 3: Persisting agents to DB")

    # Clear existing agents for this project
    delete_project_agents(project_id)

    # Build temp_id → real_id mapping for dependency wiring
    temp_to_real: dict[str, str] = {}
    created_agents = []

    for plan, detail in zip(agent_plans, details, strict=False):
        if isinstance(detail, Exception):
            logger.warning(f"Detail build failed for {plan['name']}: {detail}")
            detail = {}

        agent_data = _merge_plan_and_detail(plan, detail)

        agent = create_agent(project_id, agent_data)
        temp_to_real[plan.get("temp_id", "")] = agent["id"]
        created_agents.append(agent)

    # Wire dependencies using real IDs
    _wire_dependencies(created_agents, agent_plans, temp_to_real)

    elapsed = time.monotonic() - t_start
    logger.info(
        f"Intelligence layer built: {len(created_agents)} agents "
        f"in {elapsed:.1f}s"
    )

    # Reload from DB with tools
    agents_data = list_agents(project_id)
    agents = [AgentResponse(**a) for a in agents_data]

    return IntelligenceLayerResponse(
        agents=agents,
        agent_count=len(agents),
        validated_count=0,
    )


# ═══════════════════════════════════════════════
# Phase 1: Sonnet Planner
# ═══════════════════════════════════════════════


async def _plan_agents(
    client: AsyncAnthropic,
    ai_steps: list[dict],
    project_context: str,
    settings,
) -> list[dict]:
    """Sonnet analyzes all AI steps and plans the agent team."""
    steps_text = ""
    for step in ai_steps:
        ai_config = step.get("ai_config") or {}
        steps_text += (
            f"\n--- Step: {step.get('title', 'Untitled')} ---\n"
            f"ID: {step['id']}\n"
            f"Goal: {step.get('goal', '')}\n"
            f"Phase: {step.get('phase', '')}\n"
            f"Actors: {', '.join(step.get('actors', []))}\n"
            f"AI Role: {ai_config.get('role') or ai_config.get('ai_role', '')}\n"
            f"Agent Name: {ai_config.get('agent_name', '')}\n"
            f"Agent Type: {ai_config.get('agent_type', '')}\n"
            f"Behaviors: {', '.join(ai_config.get('behaviors', []))}\n"
            f"Automation: {ai_config.get('automation_estimate', '?')}%\n"
            f"Human touchpoints: {', '.join(ai_config.get('human_touchpoints', []))}\n"
        )

    user_msg = (
        f"Here is the product context:\n{project_context}\n\n"
        f"Here are the solution flow steps with AI capabilities:\n{steps_text}\n\n"
        f"Plan the agent team. For each agent, provide a temp_id, name, icon, "
        f"type, role description, source step ID, dependencies, and human partner role."
    )

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        system=[{
            "type": "text",
            "text": PLANNER_SYSTEM,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": user_msg}],
        tools=[PLAN_TOOL],
        tool_choice={"type": "tool", "name": "submit_agent_plan"},
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_agent_plan":
            return block.input.get("agents", [])

    return []


# ═══════════════════════════════════════════════
# Phase 2: Haiku Detail Builders
# ═══════════════════════════════════════════════


async def _build_agent_details(
    client: AsyncAnthropic,
    plan: dict,
    step: dict | None,
    project_context: str,
    settings,
) -> dict:
    """Haiku fills in rich details for a single agent."""
    step_context = ""
    if step:
        ai_config = step.get("ai_config") or {}
        step_context = (
            f"\nSource step: {step.get('title', '')}\n"
            f"Goal: {step.get('goal', '')}\n"
            f"Actors: {', '.join(step.get('actors', []))}\n"
            f"Information fields: {json.dumps(step.get('information_fields', []))}\n"
            f"AI behaviors: {', '.join(ai_config.get('behaviors', []))}\n"
            f"Data requirements: {json.dumps([d if isinstance(d, dict) else {} for d in ai_config.get('data_requirements', [])][:5])}\n"  # noqa: E501
            f"Human touchpoints: {', '.join(ai_config.get('human_touchpoints', []))}\n"
            f"Automation estimate: {ai_config.get('automation_estimate', 50)}%\n"
        )

    user_msg = (
        f"Build details for this agent:\n\n"
        f"Name: {plan['name']}\n"
        f"Type: {plan['agent_type']}\n"
        f"Role: {plan['role_description']}\n"
        f"Partner: {plan.get('partner_role', 'Domain expert')}\n"
        f"Depends on: {', '.join(plan.get('depends_on', []))}\n"
        f"Feeds: {', '.join(plan.get('feeds_into', []))}\n"
        f"{step_context}\n"
        f"Project context:\n{project_context}\n\n"
        f"Generate tools, autonomy breakdown, sample I/O, processing steps, "
        f"chat intro, and cascade effects."
    )

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2500,
        system=[{
            "type": "text",
            "text": DETAIL_BUILDER_SYSTEM,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": user_msg}],
        tools=[DETAIL_TOOL],
        tool_choice={"type": "tool", "name": "submit_agent_details"},
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_agent_details":
            return block.input

    return {}


# ═══════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════


def _safe_str(val, default=None):
    """Ensure value is a string or None."""
    return val if isinstance(val, str) else default


def _safe_str_list(val):
    """Ensure value is a list of strings."""
    if not isinstance(val, list):
        return []
    return [s for s in val if isinstance(s, str)]


def _safe_dict_list(val):
    """Ensure value is a list of dicts."""
    if not isinstance(val, list):
        return []
    return [d for d in val if isinstance(d, dict)]


def _build_project_context(project_id: UUID, flow: dict) -> str:
    """Build a concise project context string."""
    lines = [f"Project: {flow.get('title', 'Untitled')}"]
    if flow.get("summary"):
        lines.append(f"Summary: {flow['summary']}")

    # Add persona names if available
    try:
        from app.db.personas import list_personas

        personas = list_personas(project_id)
        if personas:
            names = [p.get("name", "") for p in personas[:5]]
            lines.append(f"Personas: {', '.join(names)}")
    except Exception:
        pass

    # Add feature count
    try:
        from app.db.features import list_features

        features = list_features(project_id)
        if features:
            lines.append(f"Features: {len(features)} confirmed")
            top = [f.get("name", "") for f in features[:5]]
            lines.append(f"Top features: {', '.join(top)}")
    except Exception:
        pass

    return "\n".join(lines)


def _merge_plan_and_detail(plan: dict, detail: dict) -> dict:
    """Merge Sonnet plan + Haiku detail into a single agent create dict."""
    autonomy = detail.get("autonomy", {})
    if not isinstance(autonomy, dict):
        autonomy = {}
    partner = detail.get("partner", {})
    if not isinstance(partner, dict):
        partner = {}

    return {
        "name": plan["name"],
        "icon": plan.get("icon", "⬡"),
        "agent_type": plan["agent_type"],
        "role_description": plan.get("role_description", ""),
        "source_step_id": plan.get("source_step_id"),
        # Autonomy
        "autonomy_level": autonomy.get("level", 50),
        "can_do": autonomy.get("can_do", []),
        "needs_approval": autonomy.get("needs_approval", []),
        "cannot_do": autonomy.get("cannot_do", []),
        # Partner
        "partner_role": plan.get("partner_role", partner.get("role")),
        "partner_name": partner.get("name"),
        "partner_initials": partner.get("initials"),
        "partner_color": partner.get("color", "#044159"),
        "partner_relationship": partner.get("relationship"),
        "partner_escalations": partner.get("escalations"),
        # Data + Pipeline
        "data_sources": [
            {"name": d["name"], "access": d.get("access", "read")}
            for d in detail.get("data_sources", [])
            if isinstance(d, dict) and d.get("name")
        ],
        # Intelligence
        "maturity": _safe_str(detail.get("maturity"), "learning"),
        "technique": _safe_str(detail.get("technique"), "llm"),
        "rhythm": _safe_str(detail.get("rhythm"), "on_demand"),
        "automation_rate": detail.get("automation_rate", 50) if isinstance(detail.get("automation_rate"), int) else 50,
        # Narratives
        "transform_before": _safe_str(detail.get("transform_before")),
        "transform_after": _safe_str(detail.get("transform_after")),
        # Chat
        "chat_intro": _safe_str(detail.get("chat_intro")),
        "chat_suggestions": _safe_str_list(detail.get("chat_suggestions")),
        # Sample I/O
        "sample_input": _safe_str(detail.get("sample_input")),
        "sample_output": _safe_dict_list(detail.get("sample_output")),
        "processing_steps": _safe_dict_list(detail.get("processing_steps")),
        "cascade_effects": _safe_dict_list(detail.get("cascade_effects")),
        # Tools (will be created as separate records)
        "tools": [
            {
                "name": t["name"],
                "icon": t.get("icon", "🔧"),
                "description": t.get("description", ""),
                "example": t.get("example"),
                "data_touches": t.get("data_touches", []),
                "reliability": t.get("reliability", 90),
            }
            for t in detail.get("tools", [])
            if isinstance(t, dict) and t.get("name")
        ],
    }


def _wire_dependencies(
    created_agents: list[dict],
    plans: list[dict],
    temp_to_real: dict[str, str],
) -> None:
    """Wire depends_on/feeds_into using real UUIDs."""
    from app.db.agents import update_agent

    for plan, agent in zip(plans, created_agents, strict=False):
        deps = []
        feeds = []

        for temp_id in plan.get("depends_on", []):
            real_id = temp_to_real.get(temp_id)
            if real_id:
                deps.append(real_id)

        for temp_id in plan.get("feeds_into", []):
            real_id = temp_to_real.get(temp_id)
            if real_id:
                feeds.append(real_id)

        if deps or feeds:
            update_data: dict = {}
            if deps:
                update_data["depends_on_agent_ids"] = deps
            if feeds:
                update_data["feeds_agent_ids"] = feeds
            try:
                update_agent(agent["id"], update_data)
            except Exception as e:
                logger.warning(f"Failed to wire deps for {agent['name']}: {e}")
