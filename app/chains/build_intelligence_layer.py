"""Build Intelligence Layer — Hierarchical agent generation.

Phase 1: Sonnet plans the full hierarchy — orchestrators, sub-agents, direct tools
Phase 2: Haiku (parallel) fills in each sub-agent — tools, autonomy, sample I/O, chat
Phase 3: Persist orchestrators (with direct tools), then sub-agents with parent_agent_id

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
# Tool schemas
# ═══════════════════════════════════════════════

HIERARCHY_PLAN_TOOL = {
    "name": "submit_hierarchy_plan",
    "description": "Submit the hierarchical intelligence plan: orchestrators + architecture quadrants.",
    "input_schema": {
        "type": "object",
        "required": ["orchestrators", "intelligence_architecture"],
        "properties": {
            "intelligence_architecture": {
                "type": "object",
                "description": "Classify ALL intelligence the product needs into 4 quadrants.",
                "required": ["knowledge_systems", "scoring_models", "decision_logic", "ai_capabilities"],
                "properties": {
                    "knowledge_systems": {
                        "type": "object",
                        "description": "Data assets the product needs to KNOW — lookup tables, taxonomies, rules databases, reference data.",
                        "required": ["items", "open_questions"],
                        "properties": {
                            "items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["name", "description", "powers"],
                                    "properties": {
                                        "name": {"type": "string"},
                                        "description": {"type": "string", "description": "1-2 sentences"},
                                        "powers": {"type": "string", "description": "Which outcome/feature this knowledge enables"},
                                    },
                                },
                            },
                            "open_questions": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["question", "context"],
                                    "properties": {
                                        "question": {"type": "string"},
                                        "context": {"type": "string", "description": "Why this matters"},
                                    },
                                },
                            },
                        },
                    },
                    "scoring_models": {
                        "type": "object",
                        "description": "How the product MEASURES things that were previously gut-feel — completeness scores, risk rankings, readiness indexes.",
                        "required": ["items", "open_questions"],
                        "properties": {
                            "items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["name", "description", "powers"],
                                    "properties": {
                                        "name": {"type": "string"},
                                        "description": {"type": "string"},
                                        "powers": {"type": "string"},
                                    },
                                },
                            },
                            "open_questions": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["question", "context"],
                                    "properties": {
                                        "question": {"type": "string"},
                                        "context": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                    "decision_logic": {
                        "type": "object",
                        "description": "Deterministic DECISIONS the product makes — routing, triggers, validation rules. Same input = same output.",
                        "required": ["items", "open_questions"],
                        "properties": {
                            "items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["name", "description", "powers"],
                                    "properties": {
                                        "name": {"type": "string"},
                                        "description": {"type": "string"},
                                        "powers": {"type": "string"},
                                    },
                                },
                            },
                            "open_questions": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["question", "context"],
                                    "properties": {
                                        "question": {"type": "string"},
                                        "context": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                    "ai_capabilities": {
                        "type": "object",
                        "description": "Where the product uses AI/LLM to GENERATE something new — classification, generation, prediction, matching.",
                        "required": ["items", "open_questions"],
                        "properties": {
                            "items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["name", "description", "powers"],
                                    "properties": {
                                        "name": {"type": "string"},
                                        "description": {"type": "string"},
                                        "powers": {"type": "string"},
                                    },
                                },
                            },
                            "open_questions": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "required": ["question", "context"],
                                    "properties": {
                                        "question": {"type": "string"},
                                        "context": {"type": "string"},
                                    },
                                },
                            },
                        },
                    },
                },
            },
            "orchestrators": {
                "type": "array",
                "description": "1-3 orchestrating agents, each with sub-agents and direct tools",
                "items": {
                    "type": "object",
                    "required": ["temp_id", "name", "goal", "icon",
                                 "sub_agents", "direct_tools"],
                    "properties": {
                        "temp_id": {
                            "type": "string",
                            "description": "Temporary ID (e.g., 'orch_1')",
                        },
                        "name": {
                            "type": "string",
                            "description": "Goal-oriented name (e.g., 'Family Preparedness Agent')",
                        },
                        "goal": {
                            "type": "string",
                            "description": "The orchestrator's mission in 1-2 sentences",
                        },
                        "icon": {
                            "type": "string",
                            "description": "Single emoji icon",
                        },
                        "rhythm": {
                            "type": "string",
                            "enum": ["triggered", "always_on", "on_demand", "periodic"],
                            "description": "How the orchestrator operates",
                        },
                        "partner_role": {
                            "type": "string",
                            "description": "Primary human partner persona",
                        },
                        "source_step_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Solution flow step IDs this orchestrator covers",
                        },
                        "sub_agents": {
                            "type": "array",
                            "description": "AI-powered capabilities that need LLM intelligence. These get chat and 'See in Action'.",
                            "items": {
                                "type": "object",
                                "required": ["temp_id", "name", "icon",
                                             "agent_type", "role_description",
                                             "source_step_id"],
                                "properties": {
                                    "temp_id": {"type": "string"},
                                    "name": {"type": "string"},
                                    "icon": {
                                        "type": "string",
                                        "description": "Single emoji",
                                    },
                                    "agent_type": {
                                        "type": "string",
                                        "enum": ["classifier", "matcher",
                                                 "predictor", "watcher",
                                                 "generator", "processor"],
                                    },
                                    "role_description": {
                                        "type": "string",
                                        "description": "What this sub-agent does (1-2 sentences)",
                                    },
                                    "source_step_id": {
                                        "type": "string",
                                        "description": "Solution flow step ID",
                                    },
                                    "technique": {
                                        "type": "string",
                                        "enum": ["llm", "classification",
                                                 "embeddings", "hybrid"],
                                    },
                                    "depends_on": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "temp_ids of sibling sub-agents this depends on",
                                    },
                                    "feeds_into": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "description": "temp_ids of sibling sub-agents this feeds",
                                    },
                                    "partner_role": {"type": "string"},
                                },
                            },
                            "minItems": 1,
                            "maxItems": 5,
                        },
                        "direct_tools": {
                            "type": "array",
                            "description": "Rules-based capabilities (scoring, routing, validation, detection). NOT AI — these are deterministic.",
                            "items": {
                                "type": "object",
                                "required": ["name", "icon", "description"],
                                "properties": {
                                    "name": {"type": "string"},
                                    "icon": {
                                        "type": "string",
                                        "description": "Single emoji",
                                    },
                                    "description": {
                                        "type": "string",
                                        "description": "What this tool does (one sentence)",
                                    },
                                    "technique": {
                                        "type": "string",
                                        "enum": ["rules", "scoring",
                                                 "routing", "validation",
                                                 "detection", "generation"],
                                    },
                                    "data_touches": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                },
                            },
                            "minItems": 1,
                            "maxItems": 8,
                        },
                    },
                },
                "minItems": 1,
                "maxItems": 3,
            },
        },
    },
}

# Re-use existing detail tool for sub-agent enrichment
DETAIL_TOOL = {
    "name": "submit_agent_details",
    "description": "Submit full sub-agent details including tools, autonomy, and sample I/O.",
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
                        "description": {"type": "string", "description": "One sentence"},
                        "example": {"type": "string", "description": "Concrete narrative example"},
                        "data_touches": {"type": "array", "items": {"type": "string"}},
                        "reliability": {"type": "integer", "description": "0-100"},
                    },
                },
                "minItems": 2,
                "maxItems": 5,
            },
            "autonomy": {
                "type": "object",
                "required": ["level", "can_do", "needs_approval", "cannot_do"],
                "properties": {
                    "level": {"type": "integer", "description": "0-100"},
                    "can_do": {"type": "array", "items": {"type": "string"}},
                    "needs_approval": {"type": "array", "items": {"type": "string"}},
                    "cannot_do": {"type": "array", "items": {"type": "string"}},
                },
            },
            "partner": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "initials": {"type": "string"},
                    "color": {"type": "string"},
                    "relationship": {"type": "string", "description": "2-3 sentences"},
                    "escalations": {"type": "string"},
                },
            },
            "data_sources": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "access": {"type": "string", "enum": ["read", "read/write", "query", "subscribe"]},
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
                "minItems": 3,
                "maxItems": 6,
            },
            "sample_input": {"type": "string", "description": "Realistic 1-2 sentence scenario"},
            "sample_output": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["key"],
                    "properties": {
                        "key": {"type": "string"},
                        "val": {"type": "string"},
                        "list": {"type": "array", "items": {"type": "string"}},
                        "badge": {"type": "string", "enum": ["high", "moderate", "low", "recommended", "conditional"]},
                    },
                },
                "minItems": 4,
                "maxItems": 7,
            },
            "chat_intro": {"type": "string", "description": "Agent's greeting (1-3 sentences, first person)"},
            "chat_suggestions": {
                "type": "array",
                "items": {"type": "string"},
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
            "automation_rate": {"type": "integer"},
            "maturity": {"type": "string", "enum": ["learning", "reliable", "expert"]},
        },
    },
}

# ═══════════════════════════════════════════════
# System prompts
# ═══════════════════════════════════════════════

PLANNER_SYSTEM = """\
You are an AI systems architect. You analyze a product's solution flow \
and design the INTELLIGENCE HIERARCHY that powers it.

Your job is to identify:
1. ORCHESTRATING AGENTS (1-3): Goal-driven coordinators that manage a workflow.
   Each orchestrator has a clear mission and orchestrates sub-agents and tools.
2. SUB-AGENTS under each orchestrator: AI-powered capabilities that need LLM \
   intelligence — classification, generation, prediction, matching.
3. DIRECT TOOLS under each orchestrator: Rules-based capabilities that are \
   deterministic — scoring formulas, routing logic, validation rules, detection.

CRITICAL DISTINCTION:
- Sub-agents use AI/LLM to generate novel output. They need "See in Action" \
  demos and in-character chat. Examples: document classifier, revenue forecaster, \
  positioning drafter, ICP generator.
- Direct tools are deterministic. Same input = same output. No AI needed. \
  Examples: completeness scorer (uploaded/required), checklist router (state lookup), \
  staleness detector (date comparison), permission validator (ACL matrix).

RULES:
- PREFER FEWER orchestrators. Most products need only 1-2. Only create a 3rd \
  if there is a genuinely separate user journey serving a different persona with \
  a different goal. If two workflows share the same persona or serve the same \
  overarching goal, they belong in ONE orchestrator.
- Name orchestrators with goal-oriented names (e.g., "Family Preparedness Agent").
- Sub-agents: ONLY create these for steps that genuinely need AI/LLM intelligence. \
  Be brutally honest — if a step is just routing, scoring, date comparison, \
  or lookup-table matching, it's a TOOL, not a sub-agent. Most products have \
  1-3 genuine AI sub-agents, not 5+.
- Direct tools: these are the rules, formulas, and logic. They're just as \
  important as AI — they're often the product's real moat.
- Total sub-agents across ALL orchestrators: 1-4. Err on fewer.
- Each orchestrator should have 2-6 direct tools.
- Sub-agent dependencies are within the same orchestrator only."""

DETAIL_BUILDER_SYSTEM = """\
You are building the detailed specification for an AI sub-agent. \
This sub-agent is part of an orchestrator that coordinates a workflow.

RULES:
- Tools should be specific AI capabilities, not vague categories. \
  Each tool has a concrete example showing it in action.
- Autonomy breakdown: what can it do alone, what needs human approval, \
  what it absolutely cannot do.
- Sample output should be NARRATIVE — readable by a non-technical client. \
  Write like an intelligence brief, not a data dump.
- Processing steps show the sub-agent's workflow. Each step links to a tool.
- Chat intro should be warm and approachable, in first person. \
  The sub-agent is an expert in its domain.
- Cascade effects: if this sub-agent's output changes, what other \
  sub-agents in the same orchestrator are affected?
- Be domain-specific. Use realistic names, numbers, terminology."""


# ═══════════════════════════════════════════════
# Main pipeline
# ═══════════════════════════════════════════════


async def build_intelligence_layer(
    project_id: UUID,
) -> IntelligenceLayerResponse:
    """Build the hierarchical intelligence layer for a project.

    Phase 1: Sonnet plans the full hierarchy (orchestrators + sub-agents + tools)
    Phase 2: Haiku builds details for each sub-agent (parallel)
    Phase 3: Persist — orchestrators first, then sub-agents with parent_agent_id
    """
    from app.db.solution_flow import get_flow_overview, list_flow_steps

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    t_start = time.monotonic()

    # Load solution flow
    flow = get_flow_overview(project_id)
    if not flow or not flow.get("steps"):
        raise ValueError("No solution flow found — generate one first")

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

    project_context = _build_project_context(project_id, flow)

    # ── Phase 1: Sonnet Plans Hierarchy + Architecture ──
    logger.info(f"Phase 1: Planning hierarchy from {len(ai_steps)} AI steps")
    hierarchy, architecture_data = await _plan_hierarchy(client, ai_steps, all_steps, project_context, settings)

    if not hierarchy:
        raise ValueError("Hierarchy planning produced no results")

    total_subs = sum(len(o.get("sub_agents", [])) for o in hierarchy)
    total_tools = sum(len(o.get("direct_tools", [])) for o in hierarchy)
    logger.info(
        f"Phase 1 complete: {len(hierarchy)} orchestrators, "
        f"{total_subs} sub-agents, {total_tools} direct tools"
    )

    # ── Phase 2: Haiku Details for Sub-Agents (parallel) ──
    step_map = {s["id"]: s for s in all_steps}
    all_sub_plans = []
    for orch in hierarchy:
        for sub in orch.get("sub_agents", []):
            sub["_orch_name"] = orch["name"]
            all_sub_plans.append(sub)

    logger.info(f"Phase 2: Building details for {len(all_sub_plans)} sub-agents")

    detail_tasks = [
        _build_agent_details(
            client, sub, step_map.get(sub.get("source_step_id", "")),
            project_context, settings,
        )
        for sub in all_sub_plans
    ]

    details = await asyncio.gather(*detail_tasks, return_exceptions=True)

    # ── Phase 3: Persist ──
    logger.info("Phase 3: Persisting hierarchy to DB")

    delete_project_agents(project_id)

    total_sub_count = 0
    total_tool_count = 0

    for orch in hierarchy:
        # Create orchestrator
        orch_data = {
            "name": orch["name"],
            "icon": orch.get("icon", "⬡"),
            "agent_type": "orchestrator",
            "agent_role": "orchestrator",
            "role_description": orch.get("goal", ""),
            "source_step_id": orch.get("source_step_ids", [None])[0],
            "rhythm": orch.get("rhythm", "on_demand"),
            "partner_role": orch.get("partner_role"),
            "automation_rate": 0,
            "maturity": "learning",
            "technique": "hybrid",
            # Direct tools become the orchestrator's agent_tools
            "tools": [
                {
                    "name": t["name"],
                    "icon": t.get("icon", "🔧"),
                    "description": t.get("description", ""),
                    "data_touches": t.get("data_touches", []),
                    "reliability": 95,  # Rules-based tools are highly reliable
                }
                for t in orch.get("direct_tools", [])
                if isinstance(t, dict) and t.get("name")
            ],
        }

        created_orch = create_agent(project_id, orch_data)
        orch_id = created_orch["id"]
        total_tool_count += len(created_orch.get("tools", []))

        # Create sub-agents with parent_agent_id
        orch_sub_plans = orch.get("sub_agents", [])
        temp_to_real: dict[str, str] = {}

        for sub_plan in orch_sub_plans:
            # Find matching detail from Phase 2
            sub_idx = all_sub_plans.index(sub_plan)
            detail = details[sub_idx]
            if isinstance(detail, Exception):
                logger.warning(f"Detail build failed for {sub_plan['name']}: {detail}")
                detail = {}

            sub_data = _merge_sub_agent_data(sub_plan, detail)
            sub_data["parent_agent_id"] = orch_id
            sub_data["agent_role"] = "sub_agent"

            created_sub = create_agent(project_id, sub_data)
            temp_to_real[sub_plan.get("temp_id", "")] = created_sub["id"]
            total_sub_count += 1
            total_tool_count += len(created_sub.get("tools", []))

        # Wire dependencies between sub-agents within this orchestrator
        _wire_sub_dependencies(orch_sub_plans, temp_to_real)

    # ── Persist Intelligence Architecture ──
    arch_response = None
    if architecture_data:
        from app.core.schemas_agents_v2 import IntelArchitectureResponse
        from app.db.intelligence_architecture import upsert_architecture

        try:
            upsert_architecture(project_id, architecture_data)
            arch_response = IntelArchitectureResponse(**architecture_data)
            logger.info(
                f"Architecture saved: "
                f"{len(arch_response.knowledge_systems.items)} knowledge, "
                f"{len(arch_response.scoring_models.items)} scoring, "
                f"{len(arch_response.decision_logic.items)} decision, "
                f"{len(arch_response.ai_capabilities.items)} AI"
            )
        except Exception as e:
            logger.warning(f"Failed to save architecture: {e}")

    elapsed = time.monotonic() - t_start
    logger.info(
        f"Intelligence layer built: {len(hierarchy)} orchestrators, "
        f"{total_sub_count} sub-agents, {total_tool_count} tools "
        f"in {elapsed:.1f}s"
    )

    # Reload from DB (nested structure)
    agents_data = list_agents(project_id)
    agents = [AgentResponse(**a) for a in agents_data]

    return IntelligenceLayerResponse(
        agents=agents,
        agent_count=len(agents),
        sub_agent_count=total_sub_count,
        tool_count=total_tool_count,
        validated_count=0,
        architecture=arch_response,
    )


# ═══════════════════════════════════════════════
# Phase 1: Sonnet Plans Hierarchy
# ═══════════════════════════════════════════════


async def _plan_hierarchy(
    client: AsyncAnthropic,
    ai_steps: list[dict],
    all_steps: list[dict],
    project_context: str,
    settings,
) -> tuple[list[dict], dict]:
    """Sonnet plans hierarchy + intelligence architecture. Returns (orchestrators, architecture)."""
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

    # Also include non-AI steps for context (tools often come from these)
    non_ai_steps_text = ""
    for step in all_steps:
        ai_config = step.get("ai_config") or {}
        if not ai_config.get("role") and not ai_config.get("ai_role"):
            non_ai_steps_text += (
                f"\n--- Step: {step.get('title', 'Untitled')} ---\n"
                f"ID: {step['id']}\n"
                f"Goal: {step.get('goal', '')}\n"
                f"Phase: {step.get('phase', '')}\n"
            )

    user_msg = (
        f"Product context:\n{project_context}\n\n"
        f"Steps with AI capabilities:\n{steps_text}\n\n"
        f"Non-AI steps (may need rules-based tools):\n{non_ai_steps_text}\n\n"
        f"Design BOTH the intelligence architecture AND the agent hierarchy.\n\n"
        f"INTELLIGENCE ARCHITECTURE (4 quadrants):\n"
        f"- Knowledge Systems: data assets, lookup tables, taxonomies, reference data\n"
        f"- Scoring Models: metrics, formulas, indexes that quantify things\n"
        f"- Decision Logic: deterministic routing, triggers, validation rules\n"
        f"- AI Capabilities: where LLM/AI generates novel output\n"
        f"For each item, say what it powers (which outcome/feature).\n"
        f"Include open questions — things the product might need but aren't defined yet.\n\n"
        f"AGENT HIERARCHY:\n"
        f"For each orchestrator, identify:\n"
        f"1. Its goal (what workflow does it coordinate?)\n"
        f"2. Sub-agents (which capabilities genuinely need AI?)\n"
        f"3. Direct tools (which capabilities are rules, scoring, routing, detection?)\n\n"
        f"Be honest about what's AI vs what's rules. A completeness score is math, "
        f"not AI. A state-based checklist is a lookup table, not AI."
    )

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=6000,
        system=[{
            "type": "text",
            "text": PLANNER_SYSTEM,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{"role": "user", "content": user_msg}],
        tools=[HIERARCHY_PLAN_TOOL],
        tool_choice={"type": "tool", "name": "submit_hierarchy_plan"},
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_hierarchy_plan":
            orchestrators = block.input.get("orchestrators", [])
            architecture = block.input.get("intelligence_architecture", {})
            return orchestrators, architecture

    return [], {}


# ═══════════════════════════════════════════════
# Phase 2: Haiku Sub-Agent Details
# ═══════════════════════════════════════════════


async def _build_agent_details(
    client: AsyncAnthropic,
    plan: dict,
    step: dict | None,
    project_context: str,
    settings,
) -> dict:
    """Haiku fills in rich details for a single sub-agent."""
    step_context = ""
    if step:
        ai_config = step.get("ai_config") or {}
        step_context = (
            f"\nSource step: {step.get('title', '')}\n"
            f"Goal: {step.get('goal', '')}\n"
            f"Actors: {', '.join(step.get('actors', []))}\n"
            f"Information fields: {json.dumps(step.get('information_fields', []))}\n"
            f"AI behaviors: {', '.join(ai_config.get('behaviors', []))}\n"
            f"Human touchpoints: {', '.join(ai_config.get('human_touchpoints', []))}\n"
            f"Automation estimate: {ai_config.get('automation_estimate', 50)}%\n"
        )

    user_msg = (
        f"Build details for this AI sub-agent:\n\n"
        f"Name: {plan['name']}\n"
        f"Type: {plan.get('agent_type', 'processor')}\n"
        f"Role: {plan.get('role_description', '')}\n"
        f"Part of orchestrator: {plan.get('_orch_name', 'Unknown')}\n"
        f"Partner: {plan.get('partner_role', 'Domain expert')}\n"
        f"Depends on: {', '.join(plan.get('depends_on', []))}\n"
        f"Feeds: {', '.join(plan.get('feeds_into', []))}\n"
        f"{step_context}\n"
        f"Project context:\n{project_context}\n\n"
        f"Generate tools, autonomy breakdown, sample I/O, processing steps, "
        f"chat intro, and cascade effects. Remember: this is an AI sub-agent "
        f"that genuinely uses LLM intelligence — make the tools and examples "
        f"reflect real AI capabilities."
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
    return val if isinstance(val, str) else default


def _safe_str_list(val):
    if not isinstance(val, list):
        return []
    return [s for s in val if isinstance(s, str)]


def _safe_dict_list(val):
    if not isinstance(val, list):
        return []
    return [d for d in val if isinstance(d, dict)]


def _build_project_context(project_id: UUID, flow: dict) -> str:
    lines = [f"Project: {flow.get('title', 'Untitled')}"]
    if flow.get("summary"):
        lines.append(f"Summary: {flow['summary']}")

    try:
        from app.db.personas import list_personas
        personas = list_personas(project_id)
        if personas:
            names = [p.get("name", "") for p in personas[:5]]
            lines.append(f"Personas: {', '.join(names)}")
    except Exception:
        pass

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


def _merge_sub_agent_data(plan: dict, detail: dict) -> dict:
    """Merge sub-agent plan + Haiku detail into a create dict."""
    autonomy = detail.get("autonomy", {})
    if not isinstance(autonomy, dict):
        autonomy = {}
    partner = detail.get("partner", {})
    if not isinstance(partner, dict):
        partner = {}

    return {
        "name": plan["name"],
        "icon": plan.get("icon", "⬡"),
        "agent_type": plan.get("agent_type", "processor"),
        "role_description": plan.get("role_description", ""),
        "source_step_id": plan.get("source_step_id"),
        # Autonomy
        "autonomy_level": autonomy.get("level", 50),
        "can_do": _safe_str_list(autonomy.get("can_do")),
        "needs_approval": _safe_str_list(autonomy.get("needs_approval")),
        "cannot_do": _safe_str_list(autonomy.get("cannot_do")),
        # Partner
        "partner_role": plan.get("partner_role", partner.get("role")),
        "partner_name": _safe_str(partner.get("name")),
        "partner_initials": _safe_str(partner.get("initials")),
        "partner_color": _safe_str(partner.get("color"), "#044159"),
        "partner_relationship": _safe_str(partner.get("relationship")),
        "partner_escalations": _safe_str(partner.get("escalations")),
        # Data
        "data_sources": [
            {"name": d["name"], "access": d.get("access", "read")}
            for d in detail.get("data_sources", [])
            if isinstance(d, dict) and d.get("name")
        ],
        # Intelligence
        "maturity": _safe_str(detail.get("maturity"), "learning"),
        "technique": plan.get("technique", _safe_str(detail.get("technique"), "llm")),
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
        # Tools
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


def _wire_sub_dependencies(
    sub_plans: list[dict],
    temp_to_real: dict[str, str],
) -> None:
    """Wire depends_on/feeds_into between sub-agents within an orchestrator."""
    from app.db.agents import update_agent

    for plan in sub_plans:
        real_id = temp_to_real.get(plan.get("temp_id", ""))
        if not real_id:
            continue

        deps = []
        feeds = []

        for temp_id in plan.get("depends_on", []):
            real = temp_to_real.get(temp_id)
            if real:
                deps.append(real)

        for temp_id in plan.get("feeds_into", []):
            real = temp_to_real.get(temp_id)
            if real:
                feeds.append(real)

        if deps or feeds:
            update_data: dict = {}
            if deps:
                update_data["depends_on_agent_ids"] = deps
            if feeds:
                update_data["feeds_agent_ids"] = feeds
            try:
                update_agent(real_id, update_data)
            except Exception as e:
                logger.warning(f"Failed to wire deps for {plan['name']}: {e}")
