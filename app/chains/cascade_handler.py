"""Smart state cascade handler with confidence-based routing.

This module handles automatic propagation of changes between entities:
- Feature → VP Steps (add to needed array)
- Feature → PRD key_features (append)
- Feature → Personas (suggest related_features update)
- Feature with low confidence or MVP → trigger research
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase
from app.chains.activity_feed import log_cascade_triggered, log_needs_review

logger = get_logger(__name__)


class CascadeType(str, Enum):
    """Cascade types based on confidence thresholds."""
    AUTO = "auto"        # confidence > 0.8 - apply immediately
    SUGGESTED = "suggested"  # 0.5 <= confidence <= 0.8 - show in sidebar
    LOGGED = "logged"    # confidence < 0.5 - log for later review


@dataclass
class CascadeResult:
    """Result of a cascade analysis."""
    cascade_type: CascadeType
    confidence: float
    source_entity_type: str
    source_entity_id: UUID
    source_summary: str
    target_entity_type: str
    target_entity_id: UUID
    target_summary: str
    changes: dict[str, Any]
    rationale: str


def get_cascade_type(confidence: float) -> CascadeType:
    """Determine cascade type based on confidence score."""
    if confidence > 0.8:
        return CascadeType.AUTO
    elif confidence >= 0.5:
        return CascadeType.SUGGESTED
    else:
        return CascadeType.LOGGED


def calculate_feature_vp_confidence(
    feature: dict[str, Any],
    vp_step: dict[str, Any],
) -> float:
    """
    Calculate confidence that a feature relates to a VP step.

    High confidence (>0.8):
    - Feature name appears in VP step label/description
    - Feature category matches VP step context

    Medium confidence (0.5-0.8):
    - Keywords overlap between feature and VP step
    - Related through semantic similarity

    Low confidence (<0.5):
    - Weak or no apparent connection
    """
    feature_name = feature.get("name", "").lower()
    feature_category = feature.get("category", "").lower()
    feature_details = str(feature.get("details", {})).lower()

    vp_label = vp_step.get("label", "").lower()
    vp_description = vp_step.get("description", "").lower()
    vp_ui_overview = vp_step.get("ui_overview", "").lower()
    vp_text = f"{vp_label} {vp_description} {vp_ui_overview}"

    # Check for exact name match (high confidence)
    if feature_name in vp_text:
        return 0.9

    # Check for keyword overlap
    feature_words = set(feature_name.split()) | set(feature_category.split())
    vp_words = set(vp_text.split())
    overlap = feature_words & vp_words

    # Remove common stopwords
    stopwords = {"the", "a", "an", "and", "or", "for", "to", "with", "in", "on", "of"}
    overlap -= stopwords

    if len(overlap) >= 2:
        return 0.7
    elif len(overlap) == 1:
        return 0.5

    # Check category-based matching
    category_keywords = {
        "ux": ["interface", "ui", "user", "display", "screen", "input", "form"],
        "core": ["process", "logic", "data", "system", "backend"],
        "security": ["auth", "login", "password", "secure", "encrypt"],
        "integration": ["api", "sync", "connect", "external", "import", "export"],
    }

    if feature_category in category_keywords:
        for keyword in category_keywords[feature_category]:
            if keyword in vp_text:
                return 0.6

    return 0.3


def calculate_feature_persona_confidence(
    feature: dict[str, Any],
    persona: dict[str, Any],
) -> float:
    """
    Calculate confidence that a feature benefits a persona.

    Based on matching feature functionality to persona goals/pain points.
    """
    feature_name = feature.get("name", "").lower()
    feature_details = str(feature.get("details", {})).lower()

    # Combine persona goals and pain points
    goals = [g.lower() for g in persona.get("goals", [])]
    pain_points = [p.lower() for p in persona.get("pain_points", [])]
    persona_text = " ".join(goals + pain_points)

    # Check if feature addresses any goal/pain point
    feature_words = set(feature_name.split())
    stopwords = {"the", "a", "an", "and", "or", "for", "to", "with"}
    feature_words -= stopwords

    matches = 0
    for word in feature_words:
        if len(word) > 3 and word in persona_text:
            matches += 1

    if matches >= 2:
        return 0.7
    elif matches == 1:
        return 0.5

    return 0.3


async def handle_feature_cascade(
    project_id: UUID,
    feature: dict[str, Any],
    operation: str,  # create, update, delete
) -> list[CascadeResult]:
    """
    Handle cascades when a feature is created or updated.

    Cascades:
    1. Feature → VP steps (add to needed array)
    2. Feature → PRD key_features (append to section)
    3. Feature → Personas (suggest related_features update)
    4. Feature with low confidence or MVP → queue for research
    """
    supabase = get_supabase()
    cascades: list[CascadeResult] = []

    feature_id = UUID(feature["id"]) if isinstance(feature.get("id"), str) else feature.get("id")
    feature_name = feature.get("name", "Unknown Feature")

    logger.info(
        f"Handling cascade for feature {operation}: {feature_name}",
        extra={"feature_id": str(feature_id), "operation": operation},
    )

    if operation == "delete":
        # For deletes, we don't cascade - just log
        logger.info(f"Feature deleted, no cascade for: {feature_name}")
        return cascades

    # 1. Feature → VP Steps
    try:
        vp_steps_response = (
            supabase.table("vp_steps")
            .select("id, step_index, label, description, ui_overview, needed")
            .eq("project_id", str(project_id))
            .execute()
        )
        vp_steps = vp_steps_response.data or []

        for vp_step in vp_steps:
            confidence = calculate_feature_vp_confidence(feature, vp_step)

            # Check if feature already in needed array
            needed = vp_step.get("needed", []) or []
            already_linked = any(
                n.get("name", "").lower() == feature_name.lower()
                for n in needed
            )

            if already_linked:
                continue

            cascade = CascadeResult(
                cascade_type=get_cascade_type(confidence),
                confidence=confidence,
                source_entity_type="feature",
                source_entity_id=feature_id,
                source_summary=f"Feature: {feature_name}",
                target_entity_type="vp_step",
                target_entity_id=UUID(vp_step["id"]),
                target_summary=f"VP Step {vp_step['step_index']}: {vp_step['label']}",
                changes={"add_to_needed": {
                    "name": feature_name,
                    "type": "feature",
                    "description": f"Required for {feature_name} functionality",
                }},
                rationale=f"Feature '{feature_name}' may be needed in '{vp_step['label']}' (confidence: {confidence:.0%})",
            )
            cascades.append(cascade)

    except Exception as e:
        logger.error(f"Error analyzing VP step cascades: {e}")

    # 2. Feature → PRD key_features (always AUTO for PRD sync)
    try:
        prd_response = (
            supabase.table("prd_sections")
            .select("id, slug, fields")
            .eq("project_id", str(project_id))
            .eq("slug", "key_features")
            .execute()
        )

        if prd_response.data:
            key_features_section = prd_response.data[0]
            fields = key_features_section.get("fields", {}) or {}
            content = fields.get("content", "")

            # Check if feature already mentioned
            if feature_name.lower() not in content.lower():
                cascade = CascadeResult(
                    cascade_type=CascadeType.AUTO,  # PRD sync is always auto
                    confidence=0.95,
                    source_entity_type="feature",
                    source_entity_id=feature_id,
                    source_summary=f"Feature: {feature_name}",
                    target_entity_type="prd_section",
                    target_entity_id=UUID(key_features_section["id"]),
                    target_summary="PRD: Key Features",
                    changes={"append_feature": feature_name, "mark_ai_added": True},
                    rationale=f"New feature '{feature_name}' should be reflected in Key Features section",
                )
                cascades.append(cascade)

    except Exception as e:
        logger.error(f"Error analyzing PRD cascade: {e}")

    # 3. Feature → Personas
    try:
        personas_response = (
            supabase.table("personas")
            .select("id, slug, name, goals, pain_points, related_features")
            .eq("project_id", str(project_id))
            .execute()
        )
        personas = personas_response.data or []

        for persona in personas:
            # Check if feature already linked
            related = persona.get("related_features", []) or []
            if str(feature_id) in [str(r) for r in related]:
                continue

            confidence = calculate_feature_persona_confidence(feature, persona)

            if confidence >= 0.5:  # Only suggest if reasonable confidence
                cascade = CascadeResult(
                    cascade_type=CascadeType.SUGGESTED,  # Persona links always suggested
                    confidence=confidence,
                    source_entity_type="feature",
                    source_entity_id=feature_id,
                    source_summary=f"Feature: {feature_name}",
                    target_entity_type="persona",
                    target_entity_id=UUID(persona["id"]),
                    target_summary=f"Persona: {persona['name']}",
                    changes={"add_related_feature": str(feature_id)},
                    rationale=f"Feature '{feature_name}' may benefit persona '{persona['name']}' (confidence: {confidence:.0%})",
                )
                cascades.append(cascade)

    except Exception as e:
        logger.error(f"Error analyzing persona cascades: {e}")

    # Route cascades by type
    for cascade in cascades:
        await route_cascade(project_id, cascade)

    logger.info(
        f"Generated {len(cascades)} cascades for feature {feature_name}",
        extra={
            "auto": len([c for c in cascades if c.cascade_type == CascadeType.AUTO]),
            "suggested": len([c for c in cascades if c.cascade_type == CascadeType.SUGGESTED]),
            "logged": len([c for c in cascades if c.cascade_type == CascadeType.LOGGED]),
        },
    )

    return cascades


async def route_cascade(project_id: UUID, cascade: CascadeResult) -> None:
    """Route cascade based on type: apply, suggest, or log."""
    if cascade.cascade_type == CascadeType.AUTO:
        await apply_cascade(project_id, cascade)
    elif cascade.cascade_type == CascadeType.SUGGESTED:
        await store_cascade_suggestion(project_id, cascade)
    else:
        await log_cascade(project_id, cascade)


async def apply_cascade(project_id: UUID, cascade: CascadeResult) -> dict[str, Any]:
    """Apply a cascade change immediately."""
    supabase = get_supabase()

    try:
        if cascade.target_entity_type == "vp_step":
            # Add feature to VP step's needed array
            vp_response = (
                supabase.table("vp_steps")
                .select("needed")
                .eq("id", str(cascade.target_entity_id))
                .execute()
            )

            if vp_response.data:
                current_needed = vp_response.data[0].get("needed", []) or []
                new_item = cascade.changes.get("add_to_needed", {})
                current_needed.append(new_item)

                supabase.table("vp_steps").update({
                    "needed": current_needed,
                    "updated_at": "now()",
                }).eq("id", str(cascade.target_entity_id)).execute()

                logger.info(f"Auto-applied cascade: {cascade.source_summary} → {cascade.target_summary}")

        elif cascade.target_entity_type == "prd_section":
            # Append to PRD key_features content
            prd_response = (
                supabase.table("prd_sections")
                .select("fields")
                .eq("id", str(cascade.target_entity_id))
                .execute()
            )

            if prd_response.data:
                fields = prd_response.data[0].get("fields", {}) or {}
                content = fields.get("content", "")
                feature_name = cascade.changes.get("append_feature", "")

                # Append with AI marker
                if content:
                    new_content = f"{content}\n- {feature_name} [AI-added]"
                else:
                    new_content = f"- {feature_name} [AI-added]"

                fields["content"] = new_content

                supabase.table("prd_sections").update({
                    "fields": fields,
                    "updated_at": "now()",
                }).eq("id", str(cascade.target_entity_id)).execute()

                logger.info(f"Auto-applied cascade: {cascade.source_summary} → {cascade.target_summary}")

        # Record the applied cascade
        cascade_response = supabase.table("cascade_events").insert({
            "project_id": str(project_id),
            "source_entity_type": cascade.source_entity_type,
            "source_entity_id": str(cascade.source_entity_id),
            "source_summary": cascade.source_summary,
            "target_entity_type": cascade.target_entity_type,
            "target_entity_id": str(cascade.target_entity_id),
            "target_summary": cascade.target_summary,
            "cascade_type": cascade.cascade_type.value,
            "confidence": cascade.confidence,
            "changes": cascade.changes,
            "rationale": cascade.rationale,
            "applied": True,
            "applied_at": "now()",
            "applied_by": "auto",
        }).execute()

        # Log to activity feed
        cascade_id = UUID(cascade_response.data[0]["id"]) if cascade_response.data else None
        log_cascade_triggered(
            project_id=project_id,
            source_summary=cascade.source_summary,
            target_entity_type=cascade.target_entity_type,
            target_entity_id=cascade.target_entity_id,
            target_name=cascade.target_summary.split(": ")[-1] if ": " in cascade.target_summary else None,
            cascade_id=cascade_id,
        )

        return {"status": "applied", "cascade": cascade.target_summary}

    except Exception as e:
        logger.error(f"Failed to apply cascade: {e}")
        raise


async def store_cascade_suggestion(project_id: UUID, cascade: CascadeResult) -> dict[str, Any]:
    """Store a cascade suggestion for sidebar display."""
    supabase = get_supabase()

    try:
        response = supabase.table("cascade_events").insert({
            "project_id": str(project_id),
            "source_entity_type": cascade.source_entity_type,
            "source_entity_id": str(cascade.source_entity_id),
            "source_summary": cascade.source_summary,
            "target_entity_type": cascade.target_entity_type,
            "target_entity_id": str(cascade.target_entity_id),
            "target_summary": cascade.target_summary,
            "cascade_type": cascade.cascade_type.value,
            "confidence": cascade.confidence,
            "changes": cascade.changes,
            "rationale": cascade.rationale,
            "applied": False,
        }).execute()

        # Log to activity feed as needs review
        cascade_id = UUID(response.data[0]["id"]) if response.data else None
        log_needs_review(
            project_id=project_id,
            entity_type=cascade.target_entity_type,
            entity_id=cascade.target_entity_id,
            entity_name=cascade.target_summary.split(": ")[-1] if ": " in cascade.target_summary else None,
            change_summary=f"Cascade suggestion: {cascade.source_summary}",
            reason=cascade.rationale,
            source_type="cascade",
            source_id=cascade_id,
            details={"confidence": cascade.confidence, "changes": cascade.changes},
        )

        logger.info(f"Stored cascade suggestion: {cascade.source_summary} → {cascade.target_summary}")
        return {"status": "suggested", "id": response.data[0]["id"] if response.data else None}

    except Exception as e:
        logger.error(f"Failed to store cascade suggestion: {e}")
        raise


async def log_cascade(project_id: UUID, cascade: CascadeResult) -> dict[str, Any]:
    """Log a low-confidence cascade for later review."""
    supabase = get_supabase()

    try:
        response = supabase.table("cascade_events").insert({
            "project_id": str(project_id),
            "source_entity_type": cascade.source_entity_type,
            "source_entity_id": str(cascade.source_entity_id),
            "source_summary": cascade.source_summary,
            "target_entity_type": cascade.target_entity_type,
            "target_entity_id": str(cascade.target_entity_id),
            "target_summary": cascade.target_summary,
            "cascade_type": cascade.cascade_type.value,
            "confidence": cascade.confidence,
            "changes": cascade.changes,
            "rationale": cascade.rationale,
            "applied": False,
        }).execute()

        logger.debug(f"Logged low-confidence cascade: {cascade.source_summary} → {cascade.target_summary}")
        return {"status": "logged", "id": response.data[0]["id"] if response.data else None}

    except Exception as e:
        logger.error(f"Failed to log cascade: {e}")
        raise


def get_pending_cascades(
    project_id: UUID,
    cascade_type: CascadeType | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Get pending cascade suggestions for a project."""
    supabase = get_supabase()

    try:
        query = (
            supabase.table("cascade_events")
            .select("*")
            .eq("project_id", str(project_id))
            .eq("applied", False)
            .eq("dismissed", False)
            .order("created_at", desc=True)
            .limit(limit)
        )

        if cascade_type:
            query = query.eq("cascade_type", cascade_type.value)

        response = query.execute()
        return response.data or []

    except Exception as e:
        logger.error(f"Failed to get pending cascades: {e}")
        return []


async def apply_cascade_by_id(cascade_id: UUID, applied_by: str = "user") -> dict[str, Any]:
    """Apply a pending cascade suggestion by ID."""
    supabase = get_supabase()

    try:
        # Get the cascade event
        response = supabase.table("cascade_events").select("*").eq("id", str(cascade_id)).execute()

        if not response.data:
            raise ValueError(f"Cascade not found: {cascade_id}")

        event = response.data[0]

        if event["applied"]:
            return {"status": "already_applied"}

        if event["dismissed"]:
            return {"status": "dismissed"}

        # Reconstruct cascade result
        cascade = CascadeResult(
            cascade_type=CascadeType(event["cascade_type"]),
            confidence=event["confidence"],
            source_entity_type=event["source_entity_type"],
            source_entity_id=UUID(event["source_entity_id"]),
            source_summary=event["source_summary"],
            target_entity_type=event["target_entity_type"],
            target_entity_id=UUID(event["target_entity_id"]),
            target_summary=event["target_summary"],
            changes=event["changes"],
            rationale=event["rationale"],
        )

        # Apply the cascade
        project_id = UUID(event["project_id"])
        await apply_cascade(project_id, cascade)

        # Mark as applied in cascade_events
        supabase.table("cascade_events").update({
            "applied": True,
            "applied_at": "now()",
            "applied_by": applied_by,
        }).eq("id", str(cascade_id)).execute()

        return {"status": "applied", "target": cascade.target_summary}

    except Exception as e:
        logger.error(f"Failed to apply cascade {cascade_id}: {e}")
        raise


async def dismiss_cascade(cascade_id: UUID) -> dict[str, Any]:
    """Dismiss a cascade suggestion."""
    supabase = get_supabase()

    try:
        supabase.table("cascade_events").update({
            "dismissed": True,
            "dismissed_at": "now()",
        }).eq("id", str(cascade_id)).execute()

        logger.info(f"Dismissed cascade: {cascade_id}")
        return {"status": "dismissed"}

    except Exception as e:
        logger.error(f"Failed to dismiss cascade {cascade_id}: {e}")
        raise
