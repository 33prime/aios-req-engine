"""Canonical index builder for entity routing.

Loads all entities with stable IDs and key fields for claim routing.

Phase 2: Surgical Updates for All Entity Types
"""

from uuid import UUID

from app.core.logging import get_logger
from app.core.schemas_claims import CanonicalEntity, CanonicalIndex
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def build_canonical_index(project_id: UUID) -> CanonicalIndex:
    """Build canonical index of all entities for a project.

    Used by claim extraction to route claims to the correct entity.

    Args:
        project_id: Project UUID

    Returns:
        CanonicalIndex with all entities and their key fields

    Raises:
        Exception: If database queries fail
    """
    logger.info(
        f"Building canonical index for project {project_id}",
        extra={"project_id": str(project_id)},
    )

    supabase = get_supabase()

    # Load features
    features_response = (
        supabase.table("features")
        .select("id, name, description, confirmation_status")
        .eq("project_id", str(project_id))
        .order("created_at")
        .execute()
    )

    features = [
        CanonicalEntity(
            id=f["id"],
            type="feature",
            name=f["name"],
            description=f.get("description", "")[:200] if f.get("description") else "",
            confirmation_status=f.get("confirmation_status", "ai_generated"),
        )
        for f in features_response.data
    ]

    # Load personas
    personas_response = (
        supabase.table("personas")
        .select("id, name, slug, role, description, confirmation_status")
        .eq("project_id", str(project_id))
        .order("created_at")
        .execute()
    )

    personas = [
        CanonicalEntity(
            id=p["id"],
            type="persona",
            name=p["name"],
            slug=p.get("slug"),
            role=p.get("role"),
            description=p.get("description", "")[:200] if p.get("description") else "",
            confirmation_status=p.get("confirmation_status", "ai_generated"),
        )
        for p in personas_response.data
    ]

    # Load VP steps
    vp_steps_response = (
        supabase.table("vp_steps")
        .select("id, step_index, description, confirmation_status")
        .eq("project_id", str(project_id))
        .order("step_index")
        .execute()
    )

    vp_steps = [
        CanonicalEntity(
            id=v["id"],
            type="vp_step",
            name=f"Step {v['step_index']}: {v.get('description', '')[:50]}",
            step_index=v.get("step_index"),
            description=v.get("description", "")[:200] if v.get("description") else "",
            confirmation_status=v.get("confirmation_status", "ai_generated"),
        )
        for v in vp_steps_response.data
    ]

    # Load PRD sections
    prd_sections_response = (
        supabase.table("prd_sections")
        .select("id, slug, label, content, confirmation_status")
        .eq("project_id", str(project_id))
        .order("created_at")
        .execute()
    )

    prd_sections = [
        CanonicalEntity(
            id=s["id"],
            type="prd_section",
            name=s.get("label", s["slug"]),
            slug=s["slug"],
            description=s.get("content", "")[:200] if s.get("content") else "",
            confirmation_status=s.get("confirmation_status", "ai_generated"),
        )
        for s in prd_sections_response.data
    ]

    index = CanonicalIndex(
        features=features,
        personas=personas,
        prd_sections=prd_sections,
        vp_steps=vp_steps,
    )

    logger.info(
        f"Built canonical index: {len(features)} features, {len(personas)} personas, "
        f"{len(vp_steps)} VP steps, {len(prd_sections)} PRD sections",
        extra={
            "project_id": str(project_id),
            "feature_count": len(features),
            "persona_count": len(personas),
            "vp_step_count": len(vp_steps),
            "prd_section_count": len(prd_sections),
        },
    )

    return index
