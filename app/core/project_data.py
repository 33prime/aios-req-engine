"""Shared project data loading utilities.

Extracted from action_engine.py — used by pulse_engine, briefing_engine,
context_snapshot, and the new synthesize_intelligence chain.
"""

import asyncio
import logging
from uuid import UUID

logger = logging.getLogger(__name__)


async def load_project_data(project_id: UUID) -> dict:
    """Load all project data needed for health scoring and intelligence.

    Single async boundary — everything below is sync DB calls run in parallel.
    """
    from app.db.business_drivers import list_business_drivers
    from app.db.entity_dependencies import get_dependency_graph
    from app.db.features import list_features
    from app.db.open_questions import list_open_questions
    from app.db.personas import list_personas
    from app.db.workflows import get_workflow_pairs

    phase = "discovery"
    phase_progress = 0.0

    def _q_stakeholders() -> list[str]:
        try:
            from app.db.supabase_client import get_supabase

            sb = get_supabase()
            result = (
                sb.table("stakeholders")
                .select("id, first_name, last_name, name, role, stakeholder_type")
                .eq("project_id", str(project_id))
                .execute()
            )
            return [
                f"{s.get('first_name', '')} {s.get('last_name', '')}".strip() or s.get("name", "")
                for s in (result.data or [])
            ]
        except Exception as e:
            logger.warning(f"Stakeholder load failed: {e}")
            return []

    (
        workflow_pairs,
        drivers,
        personas,
        features,
        dep_graph,
        questions,
        stakeholder_names,
    ) = await asyncio.gather(
        asyncio.to_thread(get_workflow_pairs, project_id),
        asyncio.to_thread(list_business_drivers, project_id, None, 200),
        asyncio.to_thread(list_personas, project_id),
        asyncio.to_thread(list_features, project_id),
        asyncio.to_thread(get_dependency_graph, project_id),
        asyncio.to_thread(lambda: list_open_questions(project_id, status="open", limit=50)),
        asyncio.to_thread(_q_stakeholders),
    )

    return {
        "phase": phase,
        "phase_progress": phase_progress,
        "workflow_pairs": workflow_pairs,
        "drivers": drivers,
        "personas": personas,
        "features": features,
        "dep_graph": dep_graph,
        "questions": questions,
        "stakeholder_names": stakeholder_names,
    }


def count_entities(data: dict) -> dict:
    """Count entities by type from loaded project data."""
    workflow_pairs = data.get("workflow_pairs") or []
    current_steps = sum(len(p.get("current_steps") or []) for p in workflow_pairs)
    future_steps = sum(len(p.get("future_steps") or []) for p in workflow_pairs)
    return {
        "workflows": len(workflow_pairs),
        "current_steps": current_steps,
        "future_steps": future_steps,
        "features": len(data.get("features") or []),
        "personas": len(data.get("personas") or []),
        "stakeholders": len(data.get("stakeholder_names") or []),
    }
