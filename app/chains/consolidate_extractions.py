"""Consolidation Engine for Bulk Signal Processing.

Takes outputs from multiple extraction agents and:
1. Matches extracted entities to existing ones using similarity
2. Deduplicates mentions of the same entity
3. Groups related changes
4. Outputs ConsolidatedChanges for proposal generation
"""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.core.schemas_bulk_signal import (
    ConsolidatedChange,
    ConsolidationResult,
    ExtractedEntity,
    ExtractionResult,
    FieldChange,
)
from app.core.similarity import SimilarityMatcher, should_create_or_update
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def get_existing_entities(project_id: UUID) -> dict[str, list[dict]]:
    """
    Fetch all existing entities for a project.

    Returns:
        Dict with keys: features, personas, vp_steps, prd_sections, stakeholders
    """
    supabase = get_supabase()

    try:
        features = (
            supabase.table("features")
            .select("id, name, category, is_mvp, confidence, status, details, overview")
            .eq("project_id", str(project_id))
            .execute()
        ).data or []

        personas = (
            supabase.table("personas")
            .select("id, name, slug, role, goals, pain_points, behaviors")
            .eq("project_id", str(project_id))
            .execute()
        ).data or []

        vp_steps = (
            supabase.table("vp_steps")
            .select("id, step_index, name, description, actor, trigger_event, system_response")
            .eq("project_id", str(project_id))
            .order("step_index")
            .execute()
        ).data or []

        prd_sections = (
            supabase.table("prd_sections")
            .select("id, slug, title, content")
            .eq("project_id", str(project_id))
            .execute()
        ).data or []

        stakeholders = (
            supabase.table("stakeholders")
            .select("id, name, role, email, domain_expertise, stakeholder_type")
            .eq("project_id", str(project_id))
            .execute()
        ).data or []

        return {
            "features": features,
            "personas": personas,
            "vp_steps": vp_steps,
            "prd_sections": prd_sections,
            "stakeholders": stakeholders,
        }

    except Exception as e:
        logger.error(f"Failed to fetch existing entities: {e}")
        return {
            "features": [],
            "personas": [],
            "vp_steps": [],
            "prd_sections": [],
            "stakeholders": [],
        }


def extract_name_from_entity(entity: ExtractedEntity) -> str:
    """Extract the name field from an extracted entity."""
    raw = entity.raw_data

    # Try common name fields
    for field in ["name", "title", "label", "slug"]:
        if raw.get(field):
            return str(raw[field])

    # For facts, use the title
    if raw.get("fact_type") and raw.get("title"):
        return raw["title"]

    return ""


def match_entity_to_existing(
    entity: ExtractedEntity,
    existing: list[dict],
    entity_type: str,
) -> tuple[str, dict | None, float]:
    """
    Match an extracted entity to existing ones.

    Returns:
        Tuple of (action, matched_entity, similarity_score)
        action is "create", "update", or "skip"
    """
    name = extract_name_from_entity(entity)

    if not name:
        return ("skip", None, 0.0)

    if not existing:
        return ("create", None, 0.0)

    # Use similarity matching
    action, match_result = should_create_or_update(
        candidate_name=name,
        existing_entities=existing,
        entity_type=entity_type,
    )

    return (
        action if action != "review" else "update",  # Default ambiguous to update
        match_result.matched_item,
        match_result.score,
    )


def detect_field_changes(
    existing: dict,
    new_data: dict,
    important_fields: list[str],
) -> list[FieldChange]:
    """
    Detect which fields have changed between existing and new data.

    Only reports changes to important_fields.
    """
    changes = []

    for field in important_fields:
        old_value = existing.get(field)
        new_value = new_data.get(field)

        # Skip if no new value
        if new_value is None:
            continue

        # Skip if values are the same
        if old_value == new_value:
            continue

        # For lists/dicts, check if they're meaningfully different
        if isinstance(new_value, (list, dict)):
            if old_value == new_value:
                continue

        changes.append(FieldChange(
            field_name=field,
            old_value=old_value,
            new_value=new_value,
        ))

    return changes


def consolidate_features(
    extracted: list[ExtractedEntity],
    existing_features: list[dict],
) -> list[ConsolidatedChange]:
    """Consolidate extracted features with existing ones."""
    changes = []
    seen_names: set[str] = set()

    important_fields = [
        "name", "category", "is_mvp", "confidence", "status",
        "details", "overview", "target_personas", "user_actions",
        "system_behaviors", "ui_requirements", "rules", "integrations",
    ]

    for entity in extracted:
        if entity.entity_type != "feature":
            continue

        name = extract_name_from_entity(entity)
        if not name:
            continue

        # Dedupe within this batch
        name_lower = name.lower().strip()
        if name_lower in seen_names:
            continue
        seen_names.add(name_lower)

        # Match to existing
        action, matched, score = match_entity_to_existing(
            entity, existing_features, "feature"
        )

        if action == "skip":
            continue

        raw = entity.raw_data

        if action == "create":
            changes.append(ConsolidatedChange(
                entity_type="feature",
                operation="create",
                entity_name=name,
                after={
                    "name": name,
                    "category": raw.get("category"),
                    "is_mvp": raw.get("is_mvp", False),
                    "confidence": raw.get("confidence", "medium"),
                    "status": "draft",
                    "details": raw.get("detail") or raw.get("details"),
                    "overview": raw.get("overview"),
                },
                evidence=[
                    {"excerpt": exc, "source": "signal"}
                    for exc in entity.evidence_excerpts
                ],
                rationale=f"New feature identified: {name}",
                confidence=0.8 if raw.get("confidence") == "high" else 0.6,
            ))

        elif action == "update" and matched:
            # Detect what changed
            new_data = {
                "name": name,
                "category": raw.get("category"),
                "is_mvp": raw.get("is_mvp"),
                "details": raw.get("detail") or raw.get("details"),
                "overview": raw.get("overview"),
            }

            field_changes = detect_field_changes(matched, new_data, important_fields)

            if field_changes:
                changes.append(ConsolidatedChange(
                    entity_type="feature",
                    operation="update",
                    entity_id=UUID(matched["id"]),
                    entity_name=matched.get("name"),
                    before={f.field_name: f.old_value for f in field_changes},
                    after={f.field_name: f.new_value for f in field_changes},
                    field_changes=field_changes,
                    evidence=[
                        {"excerpt": exc, "source": "signal"}
                        for exc in entity.evidence_excerpts
                    ],
                    rationale=f"Updated {len(field_changes)} fields based on new signal",
                    confidence=0.7,
                    similarity_score=score,
                ))

    return changes


def consolidate_personas(
    extracted: list[ExtractedEntity],
    existing_personas: list[dict],
) -> list[ConsolidatedChange]:
    """Consolidate extracted personas with existing ones."""
    changes = []
    seen_names: set[str] = set()

    important_fields = ["name", "role", "goals", "pain_points", "behaviors"]

    for entity in extracted:
        if entity.entity_type != "persona":
            continue

        name = extract_name_from_entity(entity)
        if not name:
            continue

        name_lower = name.lower().strip()
        if name_lower in seen_names:
            continue
        seen_names.add(name_lower)

        action, matched, score = match_entity_to_existing(
            entity, existing_personas, "persona"
        )

        if action == "skip":
            continue

        raw = entity.raw_data

        if action == "create":
            # Generate slug from name
            slug = name.lower().replace(" ", "_").replace("-", "_")[:50]

            changes.append(ConsolidatedChange(
                entity_type="persona",
                operation="create",
                entity_name=name,
                after={
                    "name": name,
                    "slug": slug,
                    "role": raw.get("role"),
                    "goals": raw.get("goals", []),
                    "pain_points": raw.get("pain_points", []),
                    "behaviors": raw.get("behaviors", []),
                },
                evidence=[
                    {"excerpt": exc, "source": "signal"}
                    for exc in entity.evidence_excerpts
                ],
                rationale=f"New persona identified: {name}",
                confidence=0.75,
            ))

        elif action == "update" and matched:
            new_data = {
                "role": raw.get("role"),
                "goals": raw.get("goals"),
                "pain_points": raw.get("pain_points"),
                "behaviors": raw.get("behaviors"),
            }

            field_changes = detect_field_changes(matched, new_data, important_fields)

            if field_changes:
                changes.append(ConsolidatedChange(
                    entity_type="persona",
                    operation="update",
                    entity_id=UUID(matched["id"]),
                    entity_name=matched.get("name"),
                    before={f.field_name: f.old_value for f in field_changes},
                    after={f.field_name: f.new_value for f in field_changes},
                    field_changes=field_changes,
                    evidence=[
                        {"excerpt": exc, "source": "signal"}
                        for exc in entity.evidence_excerpts
                    ],
                    rationale=f"Enriched persona with {len(field_changes)} new details",
                    confidence=0.7,
                    similarity_score=score,
                ))

    return changes


def consolidate_vp_steps(
    extracted: list[ExtractedEntity],
    existing_steps: list[dict],
) -> list[ConsolidatedChange]:
    """Consolidate extracted VP steps with existing ones."""
    changes = []
    seen_names: set[str] = set()

    important_fields = ["name", "description", "actor", "trigger_event", "system_response"]

    for entity in extracted:
        if entity.entity_type != "vp_step":
            continue

        name = extract_name_from_entity(entity)
        if not name:
            continue

        name_lower = name.lower().strip()
        if name_lower in seen_names:
            continue
        seen_names.add(name_lower)

        action, matched, score = match_entity_to_existing(
            entity, existing_steps, "vp_step"
        )

        if action == "skip":
            continue

        raw = entity.raw_data

        if action == "create":
            # Determine step_index (append to end if not specified)
            step_index = raw.get("step_index")
            if step_index is None:
                step_index = len(existing_steps) + len([
                    c for c in changes if c.operation == "create"
                ])

            changes.append(ConsolidatedChange(
                entity_type="vp_step",
                operation="create",
                entity_name=name,
                after={
                    "name": name,
                    "step_index": step_index,
                    "description": raw.get("description"),
                    "actor": raw.get("actor"),
                    "trigger_event": raw.get("trigger_event"),
                    "system_response": raw.get("system_response"),
                },
                evidence=[
                    {"excerpt": exc, "source": "signal"}
                    for exc in entity.evidence_excerpts
                ],
                rationale=f"New value path step: {name}",
                confidence=0.7,
            ))

        elif action == "update" and matched:
            new_data = {
                "description": raw.get("description"),
                "actor": raw.get("actor"),
                "trigger_event": raw.get("trigger_event"),
                "system_response": raw.get("system_response"),
            }

            field_changes = detect_field_changes(matched, new_data, important_fields)

            if field_changes:
                changes.append(ConsolidatedChange(
                    entity_type="vp_step",
                    operation="update",
                    entity_id=UUID(matched["id"]),
                    entity_name=matched.get("name"),
                    before={f.field_name: f.old_value for f in field_changes},
                    after={f.field_name: f.new_value for f in field_changes},
                    field_changes=field_changes,
                    evidence=[
                        {"excerpt": exc, "source": "signal"}
                        for exc in entity.evidence_excerpts
                    ],
                    rationale=f"Updated VP step with {len(field_changes)} changes",
                    confidence=0.65,
                    similarity_score=score,
                ))

    return changes


def consolidate_stakeholders(
    extracted: list[ExtractedEntity],
    existing_stakeholders: list[dict],
) -> list[ConsolidatedChange]:
    """Consolidate extracted stakeholders with existing ones."""
    changes = []
    seen_names: set[str] = set()

    # Use stricter matching for stakeholders (names)
    matcher = SimilarityMatcher(entity_type="persona")  # Similar matching rules

    important_fields = ["name", "role", "email", "domain_expertise", "stakeholder_type"]

    for entity in extracted:
        if entity.entity_type != "stakeholder":
            continue

        name = extract_name_from_entity(entity)
        if not name:
            continue

        name_lower = name.lower().strip()
        if name_lower in seen_names:
            continue
        seen_names.add(name_lower)

        # Match stakeholders by name
        match_result = matcher.find_best_match(
            candidate=name,
            corpus=existing_stakeholders,
            text_field="name",
            id_field="id",
        )

        raw = entity.raw_data

        if not match_result.is_match:
            changes.append(ConsolidatedChange(
                entity_type="stakeholder",
                operation="create",
                entity_name=name,
                after={
                    "name": name,
                    "role": raw.get("role"),
                    "email": raw.get("email"),
                    "domain_expertise": raw.get("domain_expertise", []),
                    "stakeholder_type": raw.get("stakeholder_type", "mentioned"),
                    "source_type": raw.get("source_type", "mentioned"),
                },
                evidence=[
                    {"excerpt": exc, "source": "signal"}
                    for exc in entity.evidence_excerpts
                ],
                rationale=f"New stakeholder identified: {name}",
                confidence=0.8 if raw.get("source_type") == "direct_participant" else 0.6,
            ))

        elif match_result.matched_item:
            matched = match_result.matched_item
            new_data = {
                "role": raw.get("role"),
                "email": raw.get("email"),
                "domain_expertise": raw.get("domain_expertise"),
            }

            field_changes = detect_field_changes(matched, new_data, important_fields)

            if field_changes:
                changes.append(ConsolidatedChange(
                    entity_type="stakeholder",
                    operation="update",
                    entity_id=UUID(matched["id"]),
                    entity_name=matched.get("name"),
                    before={f.field_name: f.old_value for f in field_changes},
                    after={f.field_name: f.new_value for f in field_changes},
                    field_changes=field_changes,
                    evidence=[
                        {"excerpt": exc, "source": "signal"}
                        for exc in entity.evidence_excerpts
                    ],
                    rationale=f"Updated stakeholder info",
                    confidence=0.7,
                    similarity_score=match_result.score,
                ))

    return changes


def facts_to_entities(facts: list[dict]) -> list[ExtractedEntity]:
    """
    Convert extracted facts to typed entities for consolidation.

    Maps fact_type to entity_type:
    - feature, capability, function → feature
    - persona, user, role → persona
    - process, workflow, flow → vp_step
    """
    entities = []

    type_mapping = {
        "feature": "feature",
        "capability": "feature",
        "function": "feature",
        "integration": "feature",
        "persona": "persona",
        "user": "persona",
        "user_type": "persona",
        "role": "persona",
        "process": "vp_step",
        "workflow": "vp_step",
        "flow": "vp_step",
        "step": "vp_step",
    }

    for fact in facts:
        fact_type = fact.get("fact_type", "").lower()
        entity_type = type_mapping.get(fact_type)

        if not entity_type:
            continue

        evidence_excerpts = [
            ev.get("excerpt", "")
            for ev in fact.get("evidence", [])
            if ev.get("excerpt")
        ]

        entities.append(ExtractedEntity(
            entity_type=entity_type,
            raw_data={
                "name": fact.get("title"),
                "title": fact.get("title"),
                "detail": fact.get("detail"),
                "details": fact.get("detail"),
                "confidence": fact.get("confidence"),
            },
            evidence_excerpts=evidence_excerpts,
            source_chunk_ids=[
                ev.get("chunk_id", "")
                for ev in fact.get("evidence", [])
                if ev.get("chunk_id")
            ],
        ))

    return entities


def consolidate_extractions(
    project_id: UUID,
    extraction_results: list[ExtractionResult],
) -> ConsolidationResult:
    """
    Main consolidation function.

    Takes outputs from multiple extraction agents and consolidates them
    into a unified set of changes.

    Args:
        project_id: Project UUID
        extraction_results: Results from extraction agents

    Returns:
        ConsolidationResult with all changes grouped by entity type
    """
    logger.info(
        f"Starting consolidation for project {project_id}",
        extra={
            "project_id": str(project_id),
            "agent_count": len(extraction_results),
        },
    )

    # Fetch existing entities
    existing = get_existing_entities(project_id)

    # Collect all extracted entities
    all_entities: list[ExtractedEntity] = []
    duplicates_merged = 0

    for result in extraction_results:
        if result.error:
            logger.warning(f"Skipping failed agent {result.agent_name}: {result.error}")
            continue

        all_entities.extend(result.entities)

    logger.info(f"Collected {len(all_entities)} entities from {len(extraction_results)} agents")

    # Consolidate by type
    features = consolidate_features(
        [e for e in all_entities if e.entity_type == "feature"],
        existing["features"],
    )

    personas = consolidate_personas(
        [e for e in all_entities if e.entity_type == "persona"],
        existing["personas"],
    )

    vp_steps = consolidate_vp_steps(
        [e for e in all_entities if e.entity_type == "vp_step"],
        existing["vp_steps"],
    )

    stakeholders = consolidate_stakeholders(
        [e for e in all_entities if e.entity_type == "stakeholder"],
        existing["stakeholders"],
    )

    # Calculate summary
    all_changes = features + personas + vp_steps + stakeholders
    total_creates = sum(1 for c in all_changes if c.operation == "create")
    total_updates = sum(1 for c in all_changes if c.operation == "update")

    # Calculate average confidence
    confidences = [c.confidence for c in all_changes if c.confidence]
    average_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    result = ConsolidationResult(
        features=features,
        personas=personas,
        vp_steps=vp_steps,
        stakeholders=stakeholders,
        total_creates=total_creates,
        total_updates=total_updates,
        duplicates_merged=duplicates_merged,
        average_confidence=round(average_confidence, 2),
    )

    logger.info(
        f"Consolidation complete: {total_creates} creates, {total_updates} updates",
        extra={
            "project_id": str(project_id),
            "features": len(features),
            "personas": len(personas),
            "vp_steps": len(vp_steps),
            "stakeholders": len(stakeholders),
        },
    )

    return result
