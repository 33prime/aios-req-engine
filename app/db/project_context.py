"""Database operations for project context."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from app.core.schemas_portal import (
    Competitor,
    ContextSource,
    DesignInspiration,
    KeyUser,
    MetricItem,
    ProjectContext,
    ProjectContextUpdate,
)
from app.db.supabase_client import get_supabase as get_client


async def get_project_context(project_id: UUID) -> Optional[ProjectContext]:
    """Get project context by project ID."""
    client = get_client()
    result = (
        client.table("project_context")
        .select("*")
        .eq("project_id", str(project_id))
        .execute()
    )
    if result.data:
        return _parse_context(result.data[0])
    return None


async def create_project_context(project_id: UUID) -> ProjectContext:
    """Create a new project context record."""
    client = get_client()
    context_data = {
        "project_id": str(project_id),
    }
    result = client.table("project_context").insert(context_data).execute()
    return _parse_context(result.data[0])


async def get_or_create_project_context(project_id: UUID) -> ProjectContext:
    """Get existing context or create a new one."""
    existing = await get_project_context(project_id)
    if existing:
        return existing
    return await create_project_context(project_id)


async def update_project_context(
    project_id: UUID,
    data: ProjectContextUpdate,
    source: ContextSource = ContextSource.MANUAL,
) -> Optional[ProjectContext]:
    """Update project context with partial data."""
    client = get_client()

    # Get current context to check for locked fields
    current = await get_project_context(project_id)
    if not current:
        current = await create_project_context(project_id)

    update_data = {}

    # Process each field, respecting locks
    if data.problem_main is not None and not current.problem_main_locked:
        update_data["problem_main"] = data.problem_main
        update_data["problem_main_source"] = source.value

    if data.problem_why_now is not None and not current.problem_why_now_locked:
        update_data["problem_why_now"] = data.problem_why_now
        update_data["problem_why_now_source"] = source.value

    if data.metrics is not None:
        update_data["metrics"] = [m.model_dump() for m in data.metrics]

    if data.success_future is not None and not current.success_future_locked:
        update_data["success_future"] = data.success_future
        update_data["success_future_source"] = source.value

    if data.success_wow is not None and not current.success_wow_locked:
        update_data["success_wow"] = data.success_wow
        update_data["success_wow_source"] = source.value

    if data.key_users is not None:
        update_data["key_users"] = [u.model_dump() for u in data.key_users]

    if data.design_love is not None:
        update_data["design_love"] = [d.model_dump() for d in data.design_love]

    if data.design_avoid is not None and not current.design_avoid_locked:
        update_data["design_avoid"] = data.design_avoid
        update_data["design_avoid_source"] = source.value

    if data.competitors is not None:
        update_data["competitors"] = [c.model_dump() for c in data.competitors]

    if data.tribal_knowledge is not None and not current.tribal_locked:
        update_data["tribal_knowledge"] = data.tribal_knowledge
        update_data["tribal_source"] = source.value

    if not update_data:
        return current

    result = (
        client.table("project_context")
        .update(update_data)
        .eq("project_id", str(project_id))
        .execute()
    )
    if result.data:
        return _parse_context(result.data[0])
    return None


async def update_context_section(
    project_id: UUID,
    section: str,
    data: dict[str, Any],
    source: ContextSource = ContextSource.MANUAL,
) -> Optional[ProjectContext]:
    """Update a specific section of project context."""
    client = get_client()

    # Get current context
    current = await get_or_create_project_context(project_id)

    update_data = {}

    if section == "problem":
        if "main" in data and not current.problem_main_locked:
            update_data["problem_main"] = data["main"]
            update_data["problem_main_source"] = source.value
        if "why_now" in data and not current.problem_why_now_locked:
            update_data["problem_why_now"] = data["why_now"]
            update_data["problem_why_now_source"] = source.value
        if "metrics" in data:
            update_data["metrics"] = data["metrics"]

    elif section == "success":
        if "future" in data and not current.success_future_locked:
            update_data["success_future"] = data["future"]
            update_data["success_future_source"] = source.value
        if "wow" in data and not current.success_wow_locked:
            update_data["success_wow"] = data["wow"]
            update_data["success_wow_source"] = source.value

    elif section == "users":
        if "users" in data:
            update_data["key_users"] = data["users"]

    elif section == "design":
        if "love" in data:
            update_data["design_love"] = data["love"]
        if "avoid" in data and not current.design_avoid_locked:
            update_data["design_avoid"] = data["avoid"]
            update_data["design_avoid_source"] = source.value

    elif section == "competitors":
        if "competitors" in data:
            update_data["competitors"] = data["competitors"]

    elif section == "tribal":
        if "knowledge" in data and not current.tribal_locked:
            update_data["tribal_knowledge"] = data["knowledge"]
            update_data["tribal_source"] = source.value

    if not update_data:
        return current

    result = (
        client.table("project_context")
        .update(update_data)
        .eq("project_id", str(project_id))
        .execute()
    )
    if result.data:
        return _parse_context(result.data[0])
    return None


async def lock_context_section(
    project_id: UUID,
    section: str,
    field: Optional[str] = None,
) -> Optional[ProjectContext]:
    """Lock a context section/field to prevent auto-updates."""
    client = get_client()

    update_data = {}

    if section == "problem":
        if field == "main" or field is None:
            update_data["problem_main_locked"] = True
        if field == "why_now" or field is None:
            update_data["problem_why_now_locked"] = True

    elif section == "success":
        if field == "future" or field is None:
            update_data["success_future_locked"] = True
        if field == "wow" or field is None:
            update_data["success_wow_locked"] = True

    elif section == "design":
        if field == "avoid" or field is None:
            update_data["design_avoid_locked"] = True

    elif section == "tribal":
        update_data["tribal_locked"] = True

    if not update_data:
        return await get_project_context(project_id)

    result = (
        client.table("project_context")
        .update(update_data)
        .eq("project_id", str(project_id))
        .execute()
    )
    if result.data:
        return _parse_context(result.data[0])
    return None


async def add_key_user(
    project_id: UUID,
    user: KeyUser,
) -> Optional[ProjectContext]:
    """Add a key user to the context."""
    current = await get_or_create_project_context(project_id)
    users = current.key_users.copy()
    users.append(user)

    return await update_project_context(
        project_id,
        ProjectContextUpdate(key_users=users),
        source=user.source or ContextSource.MANUAL,
    )


async def add_competitor(
    project_id: UUID,
    competitor: Competitor,
) -> Optional[ProjectContext]:
    """Add a competitor to the context."""
    current = await get_or_create_project_context(project_id)
    competitors = current.competitors.copy()
    competitors.append(competitor)

    return await update_project_context(
        project_id,
        ProjectContextUpdate(competitors=competitors),
        source=competitor.source or ContextSource.MANUAL,
    )


async def add_tribal_knowledge(
    project_id: UUID,
    knowledge: str,
    source: ContextSource = ContextSource.MANUAL,
) -> Optional[ProjectContext]:
    """Add a tribal knowledge item."""
    current = await get_or_create_project_context(project_id)

    if current.tribal_locked:
        return current

    knowledge_list = list(current.tribal_knowledge) if current.tribal_knowledge else []
    knowledge_list.append(knowledge)

    return await update_project_context(
        project_id,
        ProjectContextUpdate(tribal_knowledge=knowledge_list),
        source=source,
    )


async def update_completion_scores(
    project_id: UUID,
    scores: dict[str, int],
    overall: int,
) -> Optional[ProjectContext]:
    """Update the completion scores for a project context."""
    client = get_client()
    result = (
        client.table("project_context")
        .update({
            "completion_scores": scores,
            "overall_completion": overall,
        })
        .eq("project_id", str(project_id))
        .execute()
    )
    if result.data:
        return _parse_context(result.data[0])
    return None


def _parse_context(data: dict) -> ProjectContext:
    """Parse raw database row into ProjectContext model."""
    # Parse JSONB fields into proper models
    metrics = [MetricItem(**m) for m in (data.get("metrics") or [])]
    key_users = [KeyUser(**u) for u in (data.get("key_users") or [])]
    design_love = [DesignInspiration(**d) for d in (data.get("design_love") or [])]
    competitors = [Competitor(**c) for c in (data.get("competitors") or [])]

    return ProjectContext(
        id=data["id"],
        project_id=data["project_id"],
        problem_main=data.get("problem_main"),
        problem_main_source=data.get("problem_main_source"),
        problem_main_locked=data.get("problem_main_locked", False),
        problem_why_now=data.get("problem_why_now"),
        problem_why_now_source=data.get("problem_why_now_source"),
        problem_why_now_locked=data.get("problem_why_now_locked", False),
        metrics=metrics,
        success_future=data.get("success_future"),
        success_future_source=data.get("success_future_source"),
        success_future_locked=data.get("success_future_locked", False),
        success_wow=data.get("success_wow"),
        success_wow_source=data.get("success_wow_source"),
        success_wow_locked=data.get("success_wow_locked", False),
        key_users=key_users,
        design_love=design_love,
        design_avoid=data.get("design_avoid"),
        design_avoid_source=data.get("design_avoid_source"),
        design_avoid_locked=data.get("design_avoid_locked", False),
        competitors=competitors,
        tribal_knowledge=data.get("tribal_knowledge") or [],
        tribal_source=data.get("tribal_source"),
        tribal_locked=data.get("tribal_locked", False),
        completion_scores=data.get("completion_scores") or {},
        overall_completion=data.get("overall_completion", 0),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )
