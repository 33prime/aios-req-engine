"""Entity CRUD, task, belief, and reference tool implementations."""

from typing import Any, Dict
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


# =============================================================================
# Unified Entity CRUD
# =============================================================================


async def _create_entity(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create any entity type from a unified interface.

    Supports: feature, persona, vp_step, stakeholder, data_entity, workflow.
    """
    entity_type = params.get("entity_type")
    name = params.get("name")
    fields = params.get("fields", {})

    if not entity_type or not name:
        return {
            "success": False,
            "error": "entity_type and name are required",
        }

    try:
        if entity_type == "feature":
            return await _create_feature_entity(project_id, name, fields)
        elif entity_type == "persona":
            return await _create_persona_entity(project_id, name, fields)
        elif entity_type == "vp_step":
            return await _create_vp_step_entity(project_id, name, fields)
        elif entity_type == "stakeholder":
            return await _create_stakeholder_entity(project_id, name, fields)
        elif entity_type == "data_entity":
            return await _create_data_entity_entity(project_id, name, fields)
        elif entity_type == "workflow":
            return await _create_workflow_entity(project_id, name, fields)
        elif entity_type == "business_driver":
            return await _create_business_driver_entity(project_id, name, fields)
        else:
            return {"success": False, "error": f"Unsupported entity type: {entity_type}"}

    except Exception as e:
        logger.error(f"Error creating {entity_type}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def _update_entity(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update any entity type from a unified interface.

    Supports: feature, persona, vp_step, stakeholder, data_entity, workflow.
    """
    entity_type = params.get("entity_type")
    entity_id = params.get("entity_id")
    fields = params.get("fields", {})

    if not entity_type or not entity_id:
        return {
            "success": False,
            "error": "entity_type and entity_id are required",
        }

    if not fields:
        return {
            "success": False,
            "error": "fields must contain at least one field to update",
        }

    try:
        eid = UUID(entity_id)
    except (ValueError, TypeError):
        return {"success": False, "error": f"Invalid entity_id: {entity_id}"}

    try:
        if entity_type == "feature":
            return await _update_feature_entity(eid, fields)
        elif entity_type == "persona":
            return await _update_persona_entity(eid, fields)
        elif entity_type == "vp_step":
            return await _update_vp_step_entity(eid, fields)
        elif entity_type == "stakeholder":
            return await _update_stakeholder_entity(eid, fields)
        elif entity_type == "data_entity":
            return await _update_data_entity_entity(eid, fields)
        elif entity_type == "workflow":
            return await _update_workflow_entity(eid, fields)
        elif entity_type == "business_driver":
            return await _update_business_driver_entity(eid, project_id, fields)
        else:
            return {"success": False, "error": f"Unsupported entity type: {entity_type}"}

    except Exception as e:
        logger.error(f"Error updating {entity_type} {entity_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def _delete_entity(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Delete any entity type by ID.

    Supports: feature, persona, vp_step, stakeholder, data_entity, workflow.
    Uses cascade delete for features and personas to clean up references.
    """
    entity_type = params.get("entity_type")
    entity_id = params.get("entity_id")

    if not entity_type or not entity_id:
        return {
            "success": False,
            "error": "entity_type and entity_id are required",
        }

    try:
        eid = UUID(entity_id)
    except (ValueError, TypeError):
        return {"success": False, "error": f"Invalid entity_id: {entity_id}"}

    try:
        supabase = get_supabase()

        if entity_type == "feature":
            from app.db.cascade import delete_feature_with_cascade
            result = delete_feature_with_cascade(eid)
            entity_name = result.get("feature_name", "Unknown")
            return {
                "success": True,
                "entity_type": "feature",
                "entity_name": entity_name,
            }

        elif entity_type == "persona":
            from app.db.cascade import delete_persona_with_cascade
            result = delete_persona_with_cascade(eid)
            entity_name = result.get("persona_name", "Unknown")
            return {
                "success": True,
                "entity_type": "persona",
                "entity_name": entity_name,
            }

        elif entity_type == "business_driver":
            from app.db.business_drivers import get_business_driver, delete_business_driver

            driver = get_business_driver(eid)
            if not driver:
                return {"success": False, "error": f"Business driver not found: {entity_id}"}

            entity_name = driver.get("description", "Unknown")[:80]
            driver_type = driver.get("driver_type", "driver")
            delete_business_driver(eid, project_id)

            return {
                "success": True,
                "entity_type": "business_driver",
                "driver_type": driver_type,
                "entity_name": entity_name,
            }

        elif entity_type in ("vp_step", "stakeholder", "data_entity", "workflow"):
            table_map = {
                "vp_step": ("vp_steps", "label"),
                "stakeholder": ("stakeholders", "name"),
                "data_entity": ("data_entities", "name"),
                "workflow": ("workflows", "name"),
            }
            table, name_col = table_map[entity_type]

            # Fetch name before deleting
            fetch = (
                supabase.table(table)
                .select(f"id, {name_col}")
                .eq("id", str(eid))
                .maybe_single()
                .execute()
            )
            if not fetch.data:
                return {"success": False, "error": f"{entity_type} not found: {entity_id}"}

            entity_name = fetch.data.get(name_col, "Unknown")

            supabase.table(table).delete().eq("id", str(eid)).execute()

            return {
                "success": True,
                "entity_type": entity_type,
                "entity_name": entity_name,
            }

        else:
            return {"success": False, "error": f"Unsupported entity type: {entity_type}"}

    except Exception as e:
        logger.error(f"Error deleting {entity_type} {entity_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# =============================================================================
# Type-Specific Create/Update Handlers
# =============================================================================


# --- Feature ---

async def _create_feature_entity(project_id: UUID, name: str, fields: dict) -> Dict[str, Any]:
    """Create a single feature via direct insert."""
    supabase = get_supabase()

    data = {
        "project_id": str(project_id),
        "name": name,
        "category": fields.get("category", "core"),
        "is_mvp": fields.get("is_mvp", True),
        "confirmation_status": "ai_generated",
        "status": "proposed",
        "confidence": fields.get("confidence", 0.7),
    }
    if fields.get("overview"):
        data["overview"] = fields["overview"]
    if fields.get("priority_group"):
        data["priority_group"] = fields["priority_group"]
    if fields.get("evidence"):
        data["evidence"] = fields["evidence"]

    response = supabase.table("features").insert(data).execute()
    if not response.data:
        return {"success": False, "error": "Failed to insert feature"}

    feature = response.data[0]
    return {
        "success": True,
        "entity_type": "feature",
        "entity_id": feature["id"],
        "name": name,
    }


async def _update_feature_entity(entity_id: UUID, fields: dict) -> Dict[str, Any]:
    """Update a feature."""
    supabase = get_supabase()

    ALLOWED = {"name", "category", "overview", "priority_group", "is_mvp", "confidence", "status"}
    updates = {k: v for k, v in fields.items() if k in ALLOWED}

    if not updates:
        return {"success": False, "error": f"No valid fields to update. Allowed: {', '.join(ALLOWED)}"}

    updates["updated_at"] = "now()"
    response = supabase.table("features").update(updates).eq("id", str(entity_id)).execute()

    if not response.data:
        return {"success": False, "error": "Feature not found"}

    return {
        "success": True,
        "entity_type": "feature",
        "entity_id": str(entity_id),
        "updated_fields": [k for k in updates if k != "updated_at"],
    }


# --- Persona ---

async def _create_persona_entity(project_id: UUID, name: str, fields: dict) -> Dict[str, Any]:
    """Create a persona."""
    from app.db.personas import create_persona

    slug = name.lower().replace(" ", "_").replace("-", "_")[:50]

    persona = create_persona(
        project_id=project_id,
        slug=slug,
        name=name,
        role=fields.get("role"),
        goals=fields.get("goals"),
        pain_points=fields.get("pain_points"),
        description=fields.get("description"),
        confirmation_status="ai_generated",
    )

    return {
        "success": True,
        "entity_type": "persona",
        "entity_id": persona["id"],
        "name": name,
        "role": fields.get("role"),
    }


async def _update_persona_entity(entity_id: UUID, fields: dict) -> Dict[str, Any]:
    """Update a persona."""
    from app.db.personas import update_persona

    ALLOWED = {"name", "role", "goals", "pain_points", "description", "demographics", "psychographics"}
    updates = {k: v for k, v in fields.items() if k in ALLOWED}

    if not updates:
        return {"success": False, "error": f"No valid fields. Allowed: {', '.join(ALLOWED)}"}

    persona = update_persona(persona_id=entity_id, updates=updates)
    return {
        "success": True,
        "entity_type": "persona",
        "entity_id": str(entity_id),
        "name": persona.get("name", ""),
        "updated_fields": list(updates.keys()),
    }


# --- VP Step (workflow step) ---

async def _create_vp_step_entity(project_id: UUID, name: str, fields: dict) -> Dict[str, Any]:
    """Create a workflow step."""
    from app.db.workflows import create_workflow_step

    workflow_id = fields.get("workflow_id")
    if not workflow_id:
        return {"success": False, "error": "workflow_id is required for vp_step creation"}

    step_data = {
        "name": name,
        "step_number": fields.get("step_number", 99),
        "actor": fields.get("actor"),
        "pain_description": fields.get("pain_description"),
        "benefit_description": fields.get("benefit_description"),
        "time_minutes": fields.get("time_minutes"),
        "automation_level": fields.get("automation_level"),
        "operation_type": fields.get("operation_type"),
        "confirmation_status": "ai_generated",
    }
    # Remove None values
    step_data = {k: v for k, v in step_data.items() if v is not None}

    step = create_workflow_step(
        workflow_id=UUID(workflow_id),
        project_id=project_id,
        data=step_data,
    )

    return {
        "success": True,
        "entity_type": "vp_step",
        "entity_id": step["id"],
        "name": name,
    }


async def _update_vp_step_entity(entity_id: UUID, fields: dict) -> Dict[str, Any]:
    """Update a workflow step."""
    from app.db.workflows import update_workflow_step

    ALLOWED = {
        "name", "step_number", "actor", "pain_description",
        "benefit_description", "time_minutes", "automation_level", "operation_type",
    }
    updates = {k: v for k, v in fields.items() if k in ALLOWED}

    if not updates:
        return {"success": False, "error": f"No valid fields. Allowed: {', '.join(ALLOWED)}"}

    step = update_workflow_step(step_id=entity_id, data=updates)
    return {
        "success": True,
        "entity_type": "vp_step",
        "entity_id": str(entity_id),
        "name": step.get("name", ""),
        "updated_fields": list(updates.keys()),
    }


# --- Stakeholder ---

async def _create_stakeholder_entity(project_id: UUID, name: str, fields: dict) -> Dict[str, Any]:
    """Create a stakeholder."""
    from app.db.stakeholders import create_stakeholder

    stakeholder_type = fields.get("stakeholder_type", "influencer")

    stakeholder = create_stakeholder(
        project_id=project_id,
        name=name,
        stakeholder_type=stakeholder_type,
        email=fields.get("email"),
        role=fields.get("role"),
        organization=fields.get("organization"),
        influence_level=fields.get("influence_level", "medium"),
        priorities=fields.get("priorities", []),
        concerns=fields.get("concerns", []),
        confirmation_status="ai_generated",
    )

    return {
        "success": True,
        "entity_type": "stakeholder",
        "entity_id": stakeholder["id"],
        "name": name,
        "stakeholder_type": stakeholder_type,
    }


async def _update_stakeholder_entity(entity_id: UUID, fields: dict) -> Dict[str, Any]:
    """Update a stakeholder."""
    from app.db.stakeholders import update_stakeholder

    ALLOWED = {
        "name", "stakeholder_type", "email", "role", "organization",
        "influence_level", "priorities", "concerns", "notes",
    }
    updates = {k: v for k, v in fields.items() if k in ALLOWED}

    if not updates:
        return {"success": False, "error": f"No valid fields. Allowed: {', '.join(ALLOWED)}"}

    stakeholder = update_stakeholder(stakeholder_id=entity_id, updates=updates)
    return {
        "success": True,
        "entity_type": "stakeholder",
        "entity_id": str(entity_id),
        "name": stakeholder.get("name", ""),
        "updated_fields": list(updates.keys()),
    }


# --- Data Entity ---

async def _create_data_entity_entity(project_id: UUID, name: str, fields: dict) -> Dict[str, Any]:
    """Create a data entity."""
    from app.db.data_entities import create_data_entity

    data = {
        "name": name,
        "entity_type": fields.get("entity_type", "domain_object"),
        "fields": fields.get("fields", []),
        "description": fields.get("description"),
        "confirmation_status": "ai_generated",
    }

    entity = create_data_entity(project_id=project_id, data=data)

    return {
        "success": True,
        "entity_type": "data_entity",
        "entity_id": entity["id"],
        "name": name,
    }


async def _update_data_entity_entity(entity_id: UUID, fields: dict) -> Dict[str, Any]:
    """Update a data entity."""
    from app.db.data_entities import update_data_entity

    ALLOWED = {"name", "entity_type", "fields", "description"}
    updates = {k: v for k, v in fields.items() if k in ALLOWED}

    if not updates:
        return {"success": False, "error": f"No valid fields. Allowed: {', '.join(ALLOWED)}"}

    entity = update_data_entity(entity_id=entity_id, data=updates)
    return {
        "success": True,
        "entity_type": "data_entity",
        "entity_id": str(entity_id),
        "name": entity.get("name", ""),
        "updated_fields": list(updates.keys()),
    }


# --- Workflow ---

async def _create_workflow_entity(project_id: UUID, name: str, fields: dict) -> Dict[str, Any]:
    """Create a workflow."""
    from app.db.workflows import create_workflow

    data = {
        "name": name,
        "workflow_type": fields.get("workflow_type", "current"),
        "description": fields.get("description"),
    }

    workflow = create_workflow(project_id=project_id, data=data)

    return {
        "success": True,
        "entity_type": "workflow",
        "entity_id": workflow["id"],
        "name": name,
        "workflow_type": data["workflow_type"],
    }


async def _update_workflow_entity(entity_id: UUID, fields: dict) -> Dict[str, Any]:
    """Update a workflow."""
    from app.db.workflows import update_workflow

    ALLOWED = {"name", "description", "workflow_type"}
    updates = {k: v for k, v in fields.items() if k in ALLOWED}

    if not updates:
        return {"success": False, "error": f"No valid fields. Allowed: {', '.join(ALLOWED)}"}

    workflow = update_workflow(workflow_id=entity_id, data=updates)
    return {
        "success": True,
        "entity_type": "workflow",
        "entity_id": str(entity_id),
        "name": workflow.get("name", ""),
        "updated_fields": list(updates.keys()),
    }


# --- Business Driver ---


async def _create_business_driver_entity(project_id: UUID, description: str, fields: dict) -> Dict[str, Any]:
    """Create a business driver (goal, pain point, or KPI)."""
    from app.db.business_drivers import create_business_driver

    driver_type = fields.get("driver_type", "goal")
    if driver_type not in ("goal", "pain", "kpi"):
        return {"success": False, "error": f"Invalid driver_type: {driver_type}. Must be goal, pain, or kpi."}

    driver = create_business_driver(
        project_id=project_id,
        driver_type=driver_type,
        description=description,
        measurement=fields.get("measurement"),
        timeframe=fields.get("timeframe"),
        priority=fields.get("priority", 3),
    )

    return {
        "success": True,
        "entity_type": "business_driver",
        "entity_id": driver["id"],
        "driver_type": driver_type,
        "description": description[:80],
    }


async def _update_business_driver_entity(entity_id: UUID, project_id: UUID, fields: dict) -> Dict[str, Any]:
    """Update a business driver (goal, pain point, or KPI)."""
    from app.db.business_drivers import update_business_driver, get_business_driver

    ALLOWED = {"description", "measurement", "timeframe", "priority", "driver_type",
               "severity", "frequency", "affected_users", "business_impact", "current_workaround",
               "goal_timeframe", "success_criteria", "dependencies", "owner",
               "baseline_value", "target_value", "measurement_method", "tracking_frequency",
               "data_source", "responsible_team"}
    updates = {k: v for k, v in fields.items() if k in ALLOWED}

    if not updates:
        return {"success": False, "error": f"No valid fields. Allowed: {', '.join(sorted(ALLOWED))}"}

    driver = update_business_driver(entity_id, project_id, **updates)
    if not driver:
        return {"success": False, "error": f"Business driver not found: {entity_id}"}

    return {
        "success": True,
        "entity_type": "business_driver",
        "entity_id": str(entity_id),
        "driver_type": driver.get("driver_type", "driver"),
        "updated_fields": list(updates.keys()),
    }


# =============================================================================
# Task Handler
# =============================================================================


async def _create_task(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Create a project task from the chat assistant."""
    from datetime import datetime as dt

    from app.core.schemas_tasks import TaskCreate, TaskSourceType, TaskType, AnchoredEntityType
    from app.db.tasks import create_task

    title = params.get("title", "").strip()
    if not title:
        return {"error": "title is required"}

    # Map task_type string to enum
    task_type_str = params.get("task_type", "custom")
    task_type_map = {t.value: t for t in TaskType}
    task_type = task_type_map.get(task_type_str, TaskType.CUSTOM)

    # Map anchored_entity_type string to enum
    anchored_type = None
    anchored_type_str = params.get("anchored_entity_type")
    if anchored_type_str:
        entity_type_map = {t.value: t for t in AnchoredEntityType}
        anchored_type = entity_type_map.get(anchored_type_str)

    anchored_id = None
    anchored_id_str = params.get("anchored_entity_id")
    if anchored_id_str:
        try:
            anchored_id = UUID(anchored_id_str)
        except (ValueError, TypeError):
            pass

    # Parse datetime fields
    remind_at = None
    if params.get("remind_at"):
        try:
            remind_at = dt.fromisoformat(params["remind_at"])
        except (ValueError, TypeError):
            pass

    meeting_date = None
    if params.get("meeting_date"):
        try:
            meeting_date = dt.fromisoformat(params["meeting_date"])
        except (ValueError, TypeError):
            pass

    # Smart defaults
    review_status = None
    if task_type == TaskType.REVIEW_REQUEST:
        review_status = "pending_review"

    task_data = TaskCreate(
        title=title,
        description=params.get("description"),
        task_type=task_type,
        requires_client_input=params.get("requires_client_input", False),
        anchored_entity_type=anchored_type,
        anchored_entity_id=anchored_id,
        source_type=TaskSourceType.AI_ASSISTANT,
        remind_at=remind_at,
        meeting_type=params.get("meeting_type"),
        meeting_date=meeting_date,
        action_verb=params.get("action_verb"),
        review_status=review_status,
    )

    try:
        task = await create_task(project_id, task_data)
        return {
            "success": True,
            "task_id": str(task.id),
            "title": title,
            "task_type": task_type.value,
        }
    except Exception as e:
        logger.error(f"Failed to create task: {e}", exc_info=True)
        return {"error": f"Failed to create task: {str(e)}"}


# =============================================================================
# Knowledge & Reference Handlers
# =============================================================================


async def _add_belief(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Record a belief/knowledge in the project knowledge graph."""
    from app.db.memory_graph import create_node

    content = params.get("content", "").strip()
    if not content:
        return {"error": "content is required"}

    domain = params.get("domain")
    linked_entity_type = params.get("linked_entity_type")
    linked_entity_id = params.get("linked_entity_id")

    summary = content[:100] + ("..." if len(content) > 100 else "")

    try:
        node = create_node(
            project_id=project_id,
            node_type="belief",
            content=content,
            summary=summary,
            confidence=0.8,
            source_type="user",
            belief_domain=domain,
            linked_entity_type=linked_entity_type,
            linked_entity_id=UUID(linked_entity_id) if linked_entity_id else None,
        )
        return {
            "success": True,
            "node_id": node.get("id"),
            "summary": summary,
        }
    except Exception as e:
        logger.error(f"Failed to add belief: {e}", exc_info=True)
        return {"error": f"Failed to record belief: {str(e)}"}


async def _add_company_reference(project_id: UUID, params: Dict[str, Any]) -> Dict[str, Any]:
    """Add a competitor or design/feature inspiration."""
    from app.db.competitor_refs import create_competitor_ref

    name = params.get("name", "").strip()
    url = params.get("url", "").strip()
    if not name:
        return {"error": "name is required"}
    if not url:
        return {"error": "url is required"}

    reference_type = params.get("reference_type", "competitor")
    notes = params.get("notes")

    try:
        ref = create_competitor_ref(
            project_id=project_id,
            reference_type=reference_type,
            name=name,
            url=url,
            research_notes=notes,
        )
        return {
            "success": True,
            "ref_id": ref.get("id"),
            "name": name,
            "url": url,
            "reference_type": reference_type,
        }
    except Exception as e:
        logger.error(f"Failed to add company reference: {e}", exc_info=True)
        return {"error": f"Failed to add reference: {str(e)}"}
