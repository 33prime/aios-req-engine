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


async def _build_project_example(
    project_id: str,
    agent_type: str,
) -> tuple[str, str] | None:
    """Build a project-specific example by pulling real entities/signals."""
    try:
        from app.db.business_drivers import list_business_drivers
        from app.db.features import list_features
        from app.db.personas import list_personas

        features = await list_features(project_id, limit=8)
        personas_data = await list_personas(project_id, limit=5)
        drivers = await list_business_drivers(project_id, limit=5)

        # Need at least some data to build a meaningful example
        if not features and not personas_data and not drivers:
            return None

        feature_names = [f.get("name", f.get("title", "")) for f in (features or [])]
        persona_names = [p.get("name", "") for p in (personas_data or [])]
        driver_texts = [
            d.get("description", d.get("name", ""))
            for d in (drivers or [])
        ]

        parts: list[str] = []

        if agent_type == "classifier":
            parts.append("Project Entities for Classification:\n")
            if feature_names:
                parts.append("Features:")
                for fn in feature_names[:6]:
                    parts.append(f"  - {fn}")
            if persona_names:
                parts.append("\nPersonas:")
                for pn in persona_names[:4]:
                    parts.append(f"  - {pn}")
            if driver_texts:
                parts.append("\nBusiness Drivers:")
                for dt in driver_texts[:4]:
                    parts.append(f"  - {dt}")
            desc = "Classify entities from this project's actual data."

        elif agent_type == "matcher":
            parts.append("Project Data for Matching:\n")
            if feature_names:
                for fn in feature_names[:6]:
                    parts.append(f"- Feature: {fn}")
            if persona_names:
                for pn in persona_names[:4]:
                    parts.append(f"- Persona: {pn}")
            if driver_texts:
                for dt in driver_texts[:3]:
                    parts.append(f"- Driver: {dt}")
            desc = "Find connections in this project's features and personas."

        elif agent_type == "predictor":
            parts.append("Project Context for Prediction:\n")
            parts.append(
                f"Project has {len(feature_names)} features, "
                f"{len(persona_names)} personas, "
                f"{len(driver_texts)} business drivers.\n"
            )
            if feature_names:
                parts.append("Key features: " + ", ".join(feature_names[:5]))
            if driver_texts:
                parts.append("\nBusiness drivers:")
                for dt in driver_texts[:4]:
                    parts.append(f"  - {dt}")
            desc = "Generate predictions based on this project's data."

        elif agent_type == "watcher":
            parts.append("Project Data for Risk Detection:\n")
            if feature_names:
                parts.append("Features to monitor:")
                for fn in feature_names[:6]:
                    parts.append(f"  - {fn}")
            if driver_texts:
                parts.append("\nBusiness constraints/goals:")
                for dt in driver_texts[:4]:
                    parts.append(f"  - {dt}")
            desc = "Detect risks in this project's requirements."

        elif agent_type == "generator":
            parts.append("Project Data for Content Generation:\n")
            if feature_names:
                parts.append("Features: " + ", ".join(feature_names[:6]))
            if persona_names:
                parts.append("Personas: " + ", ".join(persona_names[:4]))
            if driver_texts:
                parts.append("\nBusiness context:")
                for dt in driver_texts[:3]:
                    parts.append(f"  - {dt}")
            desc = "Generate documentation from this project's entities."

        else:  # processor
            parts.append("Project Signal for Processing:\n")
            if feature_names:
                parts.append("Known features: " + ", ".join(feature_names[:5]))
            if persona_names:
                parts.append("Known personas: " + ", ".join(persona_names[:4]))
            if driver_texts:
                parts.append("\nBusiness context:")
                for dt in driver_texts[:3]:
                    parts.append(f"  - {dt}")
            parts.append(
                "\nProcess this project data to extract additional "
                "entities and generate discovery probes."
            )
            desc = "Process this project's data for entity extraction."

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
    # Try project-specific first
    project_example = await _build_project_example(project_id, agent_type)
    if project_example:
        description, example_text = project_example
        return AgentExampleResponse(
            agent_type=agent_type if agent_type in EXAMPLE_INPUTS else "processor",
            example_input=example_text,
            description=description,
        )

    # Fall back to generic examples
    if agent_type not in EXAMPLE_INPUTS:
        return AgentExampleResponse(
            agent_type="processor",
            example_input="Paste any text here to see the agent process it.",
            description="Default example",
        )

    description, example_text = EXAMPLE_INPUTS[agent_type]

    return AgentExampleResponse(
        agent_type=agent_type,
        example_input=example_text,
        description=description,
    )
