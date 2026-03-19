"""Workspace Agents API — interactive agent execution for the Intelligence Workbench.

Provides Try It functionality: execute demo agents with sample or custom input,
returning structured output the frontend renders as styled cards.
"""

import time

from fastapi import APIRouter

from app.chains.execute_agent_demo import EXAMPLE_INPUTS, execute_agent_demo
from app.core.logging import get_logger
from app.core.schemas_agents import (
    AgentExampleResponse,
    AgentExecuteRequest,
    AgentExecuteResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/agents", tags=["workspace-agents"])


@router.post("/execute", response_model=AgentExecuteResponse)
async def execute_agent(project_id: str, body: AgentExecuteRequest):
    """Execute a demo agent with the given input text.

    Returns structured output matching the agent type's schema.
    """
    start = time.monotonic()

    result = await execute_agent_demo(
        agent_type=body.agent_type,
        agent_name=body.agent_name,
        input_text=body.input_text,
    )

    elapsed_ms = int((time.monotonic() - start) * 1000)

    if result is None:
        result = {
            "error": "Agent execution failed",
            "entities": [],
            "summary": "Unable to process input",
        }

    return AgentExecuteResponse(
        output=result,
        execution_time_ms=elapsed_ms,
        model="claude-haiku-4-5-20251001",
        agent_type=body.agent_type,
    )


def _extract_key_signals(text: str) -> list[str]:
    """Extract key entity names from example text (lines starting with '- ' or 'Feature:' etc.)."""
    signals: list[str] = []
    for line in text.split("\n"):
        line = line.strip()
        for prefix in ("- Feature: ", "- Persona: ", "- Driver: ", "  - "):
            if line.startswith(prefix):
                val = line[len(prefix):].strip()
                if val and len(val) < 80:
                    signals.append(val)
                break
    return signals[:8]


async def _build_project_example(
    project_id: str,
    agent_type: str,
) -> tuple[str, str] | None:
    """Build a project-specific example by pulling real entities/signals."""
    try:
        from uuid import UUID as _UUID

        from app.db.business_drivers import list_business_drivers
        from app.db.features import list_features
        from app.db.personas import list_personas

        pid = _UUID(project_id)
        features = list_features(pid)[:8]
        personas_data = list_personas(pid)[:5]
        drivers = list_business_drivers(pid)[:5]

        # Need at least some data to build a meaningful example
        if not features and not personas_data and not drivers:
            return None

        # Pull solution flow narratives for realistic context
        step_narratives: list[str] = []
        try:
            from app.db.solution_flow import get_flow_overview
            flow = get_flow_overview(pid)
            if flow and flow.get("steps"):
                from app.db.solution_flow import get_flow_step
                for s in flow["steps"][:6]:
                    detail = get_flow_step(_UUID(s["id"]))
                    if detail and detail.get("mock_data_narrative"):
                        step_narratives.append(
                            detail["mock_data_narrative"][:200]
                        )
        except Exception:
            pass

        feature_names = [
            f.get("name", f.get("title", ""))
            for f in (features or [])
        ]
        persona_names = [p.get("name", "") for p in (personas_data or [])]
        persona_roles = {
            p.get("name", ""): p.get("role", "")
            for p in (personas_data or [])
        }
        driver_texts = [
            d.get("description", d.get("name", ""))[:120]
            for d in (drivers or [])
        ]

        # Build a realistic scenario using actual project data
        primary_persona = persona_names[0] if persona_names else "User"
        primary_role = persona_roles.get(primary_persona, "")
        narrative = step_narratives[0] if step_narratives else ""

        parts: list[str] = []

        if agent_type == "classifier":
            parts.append(
                f"Signal from {primary_persona}"
                f"{f' ({primary_role})' if primary_role else ''}:\n"
            )
            if narrative:
                parts.append(f"{narrative}\n")
            parts.append("Entities to classify:")
            for fn in feature_names[:6]:
                parts.append(f"  - {fn}")
            if driver_texts:
                parts.append("\nBusiness context:")
                for dt in driver_texts[:3]:
                    parts.append(f"  - {dt}")
            desc = (
                f"Classify entities from {primary_persona}'s "
                f"perspective using real project data."
            )

        elif agent_type == "matcher":
            parts.append(
                f"Find connections for {primary_persona}:\n"
            )
            if narrative:
                parts.append(f"{narrative}\n")
            for fn in feature_names[:5]:
                parts.append(f"- Feature: {fn}")
            for pn in persona_names[:3]:
                role = persona_roles.get(pn, "")
                parts.append(
                    f"- Persona: {pn}"
                    f"{f' ({role})' if role else ''}"
                )
            if driver_texts:
                for dt in driver_texts[:2]:
                    parts.append(f"- Driver: {dt}")
            desc = (
                "Match features to personas and drivers "
                "using this project's data."
            )

        elif agent_type == "predictor":
            parts.append(f"Predict outcomes for {primary_persona}:\n")
            if narrative:
                parts.append(f"Current situation: {narrative}\n")
            parts.append(
                f"Project scope: {len(feature_names)} features, "
                f"{len(persona_names)} personas"
            )
            if feature_names:
                parts.append(
                    "\nKey features: "
                    + ", ".join(feature_names[:5])
                )
            if driver_texts:
                parts.append("\nBusiness drivers:")
                for dt in driver_texts[:3]:
                    parts.append(f"  - {dt}")
            desc = (
                f"Predict outcomes for {primary_persona} "
                f"based on project data."
            )

        elif agent_type == "watcher":
            parts.append(
                f"Monitor risks for {primary_persona}:\n"
            )
            if narrative:
                parts.append(f"Context: {narrative}\n")
            if feature_names:
                parts.append("Features to monitor:")
                for fn in feature_names[:5]:
                    parts.append(f"  - {fn}")
            if driver_texts:
                parts.append("\nRisk factors:")
                for dt in driver_texts[:3]:
                    parts.append(f"  - {dt}")
            desc = f"Detect risks affecting {primary_persona}."

        elif agent_type == "generator":
            parts.append(
                f"Generate report for {primary_persona}:\n"
            )
            if narrative:
                parts.append(f"Context: {narrative}\n")
            if feature_names:
                parts.append(
                    "Features: " + ", ".join(feature_names[:5])
                )
            if persona_names:
                parts.append(
                    "Personas: " + ", ".join(persona_names[:3])
                )
            if driver_texts:
                parts.append("\nBusiness context:")
                for dt in driver_texts[:2]:
                    parts.append(f"  - {dt}")
            desc = (
                f"Generate documentation for {primary_persona} "
                f"from project entities."
            )

        else:  # processor
            parts.append(
                f"Process signal for {primary_persona}:\n"
            )
            if narrative:
                parts.append(f"{narrative}\n")
            if feature_names:
                parts.append(
                    "Known features: "
                    + ", ".join(feature_names[:5])
                )
            if persona_names:
                parts.append(
                    "Known personas: "
                    + ", ".join(persona_names[:3])
                )
            if driver_texts:
                parts.append("\nBusiness context:")
                for dt in driver_texts[:2]:
                    parts.append(f"  - {dt}")
            desc = (
                f"Extract entities from {primary_persona}'s "
                f"signal data."
            )

        text = "\n".join(parts)
        return (desc, text) if len(text) > 30 else None

    except Exception:
        logger.debug("Could not build project-specific example", exc_info=True)
        return None


@router.get("/examples/{agent_type}", response_model=AgentExampleResponse)
async def get_agent_example(project_id: str, agent_type: str):
    """Get example input text for a given agent type.

    Tries to build a project-specific example first. Falls back to
    generic examples if the project has insufficient data.
    """
    # Input type labels per agent type
    input_type_map = {
        "classifier": "Entity List",
        "matcher": "Feature & Persona Map",
        "predictor": "Project Context",
        "watcher": "Risk Inventory",
        "generator": "Entity Summary",
        "processor": "Signal Text",
    }

    # Try project-specific first
    project_example = await _build_project_example(project_id, agent_type)
    if project_example:
        description, example_text = project_example
        # Extract key signals from the example text (feature/persona names)
        key_signals = _extract_key_signals(example_text)
        return AgentExampleResponse(
            agent_type=agent_type if agent_type in EXAMPLE_INPUTS else "processor",
            example_input=example_text,
            description=description,
            key_signals=key_signals,
            source_label="Project Data",
            input_type=input_type_map.get(agent_type, "Signal Text"),
        )

    # Fall back to generic examples
    if agent_type not in EXAMPLE_INPUTS:
        return AgentExampleResponse(
            agent_type="processor",
            example_input="Paste any text here to see the agent process it.",
            description="Default example",
            key_signals=[],
            source_label="Generic",
            input_type="Signal Text",
        )

    description, example_text = EXAMPLE_INPUTS[agent_type]

    return AgentExampleResponse(
        agent_type=agent_type,
        example_input=example_text,
        description=description,
        key_signals=[],
        source_label="Generic",
        input_type=input_type_map.get(agent_type, "Signal Text"),
    )
