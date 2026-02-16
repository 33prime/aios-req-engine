"""Consolidation Engine for Bulk Signal Processing.

Takes outputs from multiple extraction agents and:
1. Matches extracted entities to existing ones using similarity
2. Deduplicates mentions of the same entity
3. Groups related changes
4. Outputs ConsolidatedChanges for proposal generation
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        Dict with keys: features, personas, vp_steps, stakeholders,
        constraints, business_drivers, competitor_refs, company_info
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
            .select("id, name, slug, role, goals, pain_points, description")
            .eq("project_id", str(project_id))
            .execute()
        ).data or []

        vp_steps = (
            supabase.table("vp_steps")
            .select("id, step_index, label, description, actor_persona_name")
            .eq("project_id", str(project_id))
            .order("step_index")
            .execute()
        ).data or []

        stakeholders = (
            supabase.table("stakeholders")
            .select("id, name, role, email, domain_expertise, stakeholder_type")
            .eq("project_id", str(project_id))
            .execute()
        ).data or []

        # Fetch constraints
        try:
            constraints = (
                supabase.table("constraints")
                .select("id, title, description, constraint_type, severity")
                .eq("project_id", str(project_id))
                .execute()
            ).data or []
        except Exception:
            constraints = []

        # Fetch business drivers (kpi, pain, goal)
        try:
            business_drivers = (
                supabase.table("business_drivers")
                .select("id, driver_type, description, measurement, timeframe, priority")
                .eq("project_id", str(project_id))
                .execute()
            ).data or []
        except Exception:
            business_drivers = []

        # Fetch competitor references
        try:
            competitor_refs = (
                supabase.table("competitor_references")
                .select("id, reference_type, name, url, category, strengths, weaknesses")
                .eq("project_id", str(project_id))
                .execute()
            ).data or []
        except Exception:
            competitor_refs = []

        # Fetch company info (one per project)
        try:
            company_info_result = (
                supabase.table("company_info")
                .select("id, name, industry, stage, size, description")
                .eq("project_id", str(project_id))
                .execute()
            ).data or []
            company_info = company_info_result[0] if company_info_result else None
        except Exception:
            company_info = None

        # Fetch data entities
        try:
            data_entities = (
                supabase.table("data_entities")
                .select("id, name, description, entity_category, fields")
                .eq("project_id", str(project_id))
                .execute()
            ).data or []
        except Exception:
            data_entities = []

        # Fetch workflows
        try:
            workflows = (
                supabase.table("workflows")
                .select("id, name, state_type, description, paired_workflow_id")
                .eq("project_id", str(project_id))
                .execute()
            ).data or []
        except Exception:
            workflows = []

        return {
            "features": features,
            "personas": personas,
            "vp_steps": vp_steps,
            "stakeholders": stakeholders,
            "constraints": constraints,
            "business_drivers": business_drivers,
            "competitor_refs": competitor_refs,
            "company_info": company_info,
            "data_entities": data_entities,
            "workflows": workflows,
        }

    except Exception as e:
        logger.error(f"Failed to fetch existing entities: {e}")
        return {
            "features": [],
            "personas": [],
            "vp_steps": [],
            "stakeholders": [],
            "constraints": [],
            "business_drivers": [],
            "competitor_refs": [],
            "company_info": None,
            "data_entities": [],
            "workflows": [],
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

    important_fields = ["name", "role", "goals", "pain_points", "description"]

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
                    "description": raw.get("description", ""),
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
                "description": raw.get("description"),
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

    important_fields = ["label", "description", "actor", "trigger_event", "system_response"]

    for entity in extracted:
        if entity.entity_type != "vp_step":
            continue

        # Skip workflow-tagged entities — handled by consolidate_workflows()
        if entity.raw_data.get("workflow_name"):
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
                    "label": name,  # Database column is 'label', not 'name'
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
                    entity_name=matched.get("label") or matched.get("name"),
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


def consolidate_constraints(
    extracted: list[ExtractedEntity],
    existing_constraints: list[dict],
) -> list[ConsolidatedChange]:
    """
    Consolidate extracted constraints (risks, KPIs, requirements, etc.)

    Constraints include:
    - Technical/business constraints
    - Risks and threats
    - KPIs and success metrics
    - Assumptions
    """
    changes = []
    seen_titles: set[str] = set()

    # Use looser matching for constraints (they can be worded differently)
    matcher = SimilarityMatcher(entity_type="feature")

    important_fields = ["title", "description", "constraint_type", "severity"]

    for entity in extracted:
        if entity.entity_type != "constraint":
            continue

        title = extract_name_from_entity(entity)
        if not title:
            continue

        title_lower = title.lower().strip()
        if title_lower in seen_titles:
            continue
        seen_titles.add(title_lower)

        raw = entity.raw_data
        fact_type = raw.get("fact_type", "constraint").lower()

        # Map fact_type to constraint_type (6-category system — migration 0120)
        constraint_type_mapping = {
            "risk": "strategic",
            "threat": "strategic",
            "kpi": "strategic",
            "metric": "strategic",
            "goal": "strategic",
            "objective": "strategic",
            "organizational_goal": "organizational",
            "assumption": "organizational",
            "constraint": "technical",
            "requirement": "technical",
            "integration": "technical",
            "data_requirement": "technical",
        }
        constraint_type = constraint_type_mapping.get(fact_type, "technical")

        # Match against existing constraints
        match_result = matcher.find_best_match(
            candidate=title,
            corpus=existing_constraints,
            text_field="title",
            id_field="id",
        )

        if not match_result.is_match:
            changes.append(ConsolidatedChange(
                entity_type="constraint",
                operation="create",
                entity_name=title,
                after={
                    "title": title,
                    "description": raw.get("detail") or raw.get("description"),
                    "constraint_type": constraint_type,
                    "severity": "medium",  # Default severity
                },
                evidence=[
                    {"excerpt": exc, "source": "signal"}
                    for exc in entity.evidence_excerpts
                ],
                rationale=f"New {constraint_type} identified: {title}",
                confidence=raw.get("confidence", 0.7) if isinstance(raw.get("confidence"), (int, float)) else 0.7,
            ))

        elif match_result.matched_item:
            matched = match_result.matched_item
            new_data = {
                "description": raw.get("detail") or raw.get("description"),
            }

            field_changes = detect_field_changes(matched, new_data, important_fields)

            if field_changes:
                changes.append(ConsolidatedChange(
                    entity_type="constraint",
                    operation="update",
                    entity_id=UUID(matched["id"]),
                    entity_name=matched.get("title"),
                    before={f.field_name: f.old_value for f in field_changes},
                    after={f.field_name: f.new_value for f in field_changes},
                    field_changes=field_changes,
                    evidence=[
                        {"excerpt": exc, "source": "signal"}
                        for exc in entity.evidence_excerpts
                    ],
                    rationale=f"Updated {constraint_type} info",
                    confidence=0.7,
                    similarity_score=match_result.score,
                ))

    return changes


def _resolve_name_to_id(
    name: str | None,
    entities: list[dict],
    text_field: str = "name",
) -> str | None:
    """Resolve a string name to an entity UUID using similarity matching."""
    if not name or not entities:
        return None
    matcher = SimilarityMatcher(entity_type="feature")
    result = matcher.find_best_match(
        candidate=name,
        corpus=entities,
        text_field=text_field,
        id_field="id",
    )
    if result.is_match and result.matched_item:
        return result.matched_item["id"]
    return None


def consolidate_business_drivers(
    extracted: list[ExtractedEntity],
    existing_drivers: list[dict],
    existing_personas: list[dict] | None = None,
    existing_features: list[dict] | None = None,
    existing_vp_steps: list[dict] | None = None,
) -> list[ConsolidatedChange]:
    """
    Consolidate extracted business drivers (KPIs, pains, goals).

    Maps fact_type to driver_type:
    - kpi, metric → kpi
    - pain → pain
    - goal, objective → goal

    Also resolves extraction relationship hints (related_actor, related_process,
    addresses_feature) into linked_persona_ids, linked_vp_step_ids, linked_feature_ids.
    """
    changes = []
    seen_descriptions: set[str] = set()

    matcher = SimilarityMatcher(entity_type="feature")

    for entity in extracted:
        if entity.entity_type != "business_driver":
            continue

        raw = entity.raw_data
        description = raw.get("title") or raw.get("description") or ""
        if not description:
            continue

        desc_lower = description.lower().strip()[:100]
        if desc_lower in seen_descriptions:
            continue
        seen_descriptions.add(desc_lower)

        # Map fact_type to driver_type
        fact_type = raw.get("fact_type", "").lower()
        driver_type_mapping = {
            "kpi": "kpi",
            "metric": "kpi",
            "pain": "pain",
            "goal": "goal",
            "objective": "goal",
            "organizational_goal": "goal",
        }
        driver_type = driver_type_mapping.get(fact_type, "goal")

        # Match against existing drivers of same type
        same_type_drivers = [d for d in existing_drivers if d.get("driver_type") == driver_type]
        match_result = matcher.find_best_match(
            candidate=description,
            corpus=same_type_drivers,
            text_field="description",
            id_field="id",
        )

        # Resolve relationship hints to entity IDs
        linked_persona_ids: list[str] = []
        linked_feature_ids: list[str] = []
        linked_vp_step_ids: list[str] = []

        related_actor = raw.get("related_actor")
        if related_actor and existing_personas:
            pid = _resolve_name_to_id(related_actor, existing_personas, "name")
            if pid:
                linked_persona_ids.append(pid)

        addresses_feature = raw.get("addresses_feature")
        if addresses_feature and existing_features:
            fid = _resolve_name_to_id(addresses_feature, existing_features, "name")
            if fid:
                linked_feature_ids.append(fid)

        related_process = raw.get("related_process")
        if related_process and existing_vp_steps:
            vid = _resolve_name_to_id(related_process, existing_vp_steps, "label")
            if vid:
                linked_vp_step_ids.append(vid)

        if not match_result.is_match:
            after_data: dict = {
                "driver_type": driver_type,
                "description": description,
                "measurement": raw.get("measurement") or raw.get("detail"),
                "timeframe": raw.get("timeframe"),
                "priority": 3,  # Default medium priority
            }
            if linked_persona_ids:
                after_data["linked_persona_ids"] = linked_persona_ids
            if linked_feature_ids:
                after_data["linked_feature_ids"] = linked_feature_ids
            if linked_vp_step_ids:
                after_data["linked_vp_step_ids"] = linked_vp_step_ids

            changes.append(ConsolidatedChange(
                entity_type="business_driver",
                operation="create",
                entity_name=description[:50],
                after=after_data,
                evidence=[
                    {"excerpt": exc, "source": "signal"}
                    for exc in entity.evidence_excerpts
                ],
                rationale=f"New {driver_type} identified: {description[:50]}",
                confidence=0.75,
            ))

        elif match_result.matched_item:
            matched = match_result.matched_item
            new_data: dict[str, Any] = {
                "measurement": raw.get("measurement") or raw.get("detail"),
                "timeframe": raw.get("timeframe"),
            }
            # Merge link arrays with existing
            if linked_persona_ids:
                existing_pids = matched.get("linked_persona_ids") or []
                merged_pids = list(set([str(p) for p in existing_pids] + linked_persona_ids))
                new_data["linked_persona_ids"] = merged_pids
            if linked_feature_ids:
                existing_fids = matched.get("linked_feature_ids") or []
                merged_fids = list(set([str(f) for f in existing_fids] + linked_feature_ids))
                new_data["linked_feature_ids"] = merged_fids
            if linked_vp_step_ids:
                existing_vids = matched.get("linked_vp_step_ids") or []
                merged_vids = list(set([str(v) for v in existing_vids] + linked_vp_step_ids))
                new_data["linked_vp_step_ids"] = merged_vids

            field_changes = detect_field_changes(
                matched, new_data, ["description", "measurement", "timeframe",
                                    "linked_persona_ids", "linked_feature_ids", "linked_vp_step_ids"]
            )

            if field_changes:
                changes.append(ConsolidatedChange(
                    entity_type="business_driver",
                    operation="update",
                    entity_id=UUID(matched["id"]),
                    entity_name=matched.get("description", "")[:50],
                    before={f.field_name: f.old_value for f in field_changes},
                    after={f.field_name: f.new_value for f in field_changes},
                    field_changes=field_changes,
                    evidence=[
                        {"excerpt": exc, "source": "signal"}
                        for exc in entity.evidence_excerpts
                    ],
                    rationale=f"Updated {driver_type} with new details",
                    confidence=0.7,
                    similarity_score=match_result.score,
                ))

    return changes


def consolidate_competitor_refs(
    extracted: list[ExtractedEntity],
    existing_refs: list[dict],
) -> list[ConsolidatedChange]:
    """
    Consolidate extracted competitor references (competitors, design inspiration).

    Maps fact_type to reference_type:
    - competitor → competitor
    - design_inspiration → design_inspiration
    - feature_inspiration → feature_inspiration
    """
    changes = []
    seen_names: set[str] = set()

    matcher = SimilarityMatcher(entity_type="feature")

    for entity in extracted:
        if entity.entity_type != "competitor_ref":
            continue

        raw = entity.raw_data
        name = raw.get("title") or raw.get("name") or ""
        if not name:
            continue

        name_lower = name.lower().strip()
        if name_lower in seen_names:
            continue
        seen_names.add(name_lower)

        # Map fact_type to reference_type
        fact_type = raw.get("fact_type", "").lower()
        ref_type_mapping = {
            "competitor": "competitor",
            "design_inspiration": "design_inspiration",
            "feature_inspiration": "feature_inspiration",
        }
        reference_type = ref_type_mapping.get(fact_type, "competitor")

        # Match against existing refs
        match_result = matcher.find_best_match(
            candidate=name,
            corpus=existing_refs,
            text_field="name",
            id_field="id",
        )

        if not match_result.is_match:
            changes.append(ConsolidatedChange(
                entity_type="competitor_ref",
                operation="create",
                entity_name=name,
                after={
                    "reference_type": reference_type,
                    "name": name,
                    "url": raw.get("url"),
                    "category": raw.get("category", "Direct competitor" if reference_type == "competitor" else "Design reference"),
                    "research_notes": raw.get("detail") or raw.get("description"),
                },
                evidence=[
                    {"excerpt": exc, "source": "signal"}
                    for exc in entity.evidence_excerpts
                ],
                rationale=f"New {reference_type.replace('_', ' ')}: {name}",
                confidence=0.8,
            ))

        elif match_result.matched_item:
            matched = match_result.matched_item
            new_data = {
                "url": raw.get("url"),
                "research_notes": raw.get("detail") or raw.get("description"),
            }

            field_changes = detect_field_changes(
                matched, new_data, ["url", "research_notes", "category"]
            )

            if field_changes:
                changes.append(ConsolidatedChange(
                    entity_type="competitor_ref",
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
                    rationale=f"Updated {reference_type.replace('_', ' ')} info",
                    confidence=0.7,
                    similarity_score=match_result.score,
                ))

    return changes


def consolidate_company_info(
    extracted: list[ExtractedEntity],
    existing_company: dict | None,
) -> list[ConsolidatedChange]:
    """
    Consolidate extracted company info (one per project).

    If company info exists, update it. Otherwise create new.
    """
    changes = []

    company_entities = [e for e in extracted if e.entity_type == "company_info"]
    if not company_entities:
        return changes

    # Take the first company info entity (should only be one per signal)
    entity = company_entities[0]
    raw = entity.raw_data

    name = raw.get("title") or raw.get("name") or raw.get("client_name") or ""
    if not name:
        return changes

    if not existing_company:
        changes.append(ConsolidatedChange(
            entity_type="company_info",
            operation="create",
            entity_name=name,
            after={
                "name": name,
                "industry": raw.get("industry"),
                "stage": raw.get("stage"),
                "size": raw.get("size"),
                "description": raw.get("detail") or raw.get("description"),
                "key_differentiators": raw.get("key_differentiators", []),
            },
            evidence=[
                {"excerpt": exc, "source": "signal"}
                for exc in entity.evidence_excerpts
            ],
            rationale=f"New company info: {name}",
            confidence=0.85,
        ))
    else:
        new_data = {
            "name": name,
            "industry": raw.get("industry"),
            "stage": raw.get("stage"),
            "size": raw.get("size"),
            "description": raw.get("detail") or raw.get("description"),
        }

        field_changes = detect_field_changes(
            existing_company, new_data,
            ["name", "industry", "stage", "size", "description"]
        )

        if field_changes:
            changes.append(ConsolidatedChange(
                entity_type="company_info",
                operation="update",
                entity_id=UUID(existing_company["id"]),
                entity_name=existing_company.get("name"),
                before={f.field_name: f.old_value for f in field_changes},
                after={f.field_name: f.new_value for f in field_changes},
                field_changes=field_changes,
                evidence=[
                    {"excerpt": exc, "source": "signal"}
                    for exc in entity.evidence_excerpts
                ],
                rationale="Updated company info",
                confidence=0.8,
            ))

    return changes


def consolidate_data_entities(
    extracted: list[ExtractedEntity],
    existing_data_entities: list[dict],
) -> list[ConsolidatedChange]:
    """Consolidate extracted data entities with existing ones."""
    changes = []
    seen_names: set[str] = set()

    matcher = SimilarityMatcher(entity_type="feature")
    important_fields = ["name", "description", "entity_category", "fields"]

    for entity in extracted:
        if entity.entity_type != "data_entity":
            continue

        name = extract_name_from_entity(entity)
        if not name:
            continue

        name_lower = name.lower().strip()
        if name_lower in seen_names:
            continue
        seen_names.add(name_lower)

        raw = entity.raw_data

        match_result = matcher.find_best_match(
            candidate=name,
            corpus=existing_data_entities,
            text_field="name",
            id_field="id",
        )

        if not match_result.is_match:
            changes.append(ConsolidatedChange(
                entity_type="data_entity",
                operation="create",
                entity_name=name,
                after={
                    "name": name,
                    "description": raw.get("detail") or raw.get("description", ""),
                    "entity_category": raw.get("entity_category", "domain"),
                    "fields": raw.get("fields", []),
                },
                evidence=[
                    {"excerpt": exc, "source": "signal"}
                    for exc in entity.evidence_excerpts
                ],
                rationale=f"New data entity identified: {name}",
                confidence=0.75,
            ))

        elif match_result.matched_item:
            matched = match_result.matched_item
            # Merge fields: combine existing + new, dedup by name
            existing_fields = matched.get("fields") or []
            extracted_fields = raw.get("fields") or []
            if extracted_fields and existing_fields:
                existing_names = {f.get("name", "").lower() for f in existing_fields if isinstance(f, dict)}
                merged = list(existing_fields)
                for f in extracted_fields:
                    if isinstance(f, dict) and f.get("name", "").lower() not in existing_names:
                        merged.append(f)
                merged_fields = merged if len(merged) > len(existing_fields) else None
            elif extracted_fields:
                merged_fields = extracted_fields
            else:
                merged_fields = None

            new_data = {
                "description": raw.get("detail") or raw.get("description"),
            }
            if merged_fields is not None:
                new_data["fields"] = merged_fields

            field_changes = detect_field_changes(matched, new_data, important_fields)

            if field_changes:
                changes.append(ConsolidatedChange(
                    entity_type="data_entity",
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
                    rationale=f"Updated data entity with new details",
                    confidence=0.7,
                    similarity_score=match_result.score,
                ))

    return changes


def consolidate_workflows(
    extracted: list[ExtractedEntity],
    existing_workflows: list[dict],
    existing_steps: list[dict],
) -> tuple[list[ConsolidatedChange], list[ConsolidatedChange]]:
    """
    Group workflow-tagged vp_step entities into workflow + step changes.

    Returns:
        (workflow_changes, step_changes) — workflow creates must be applied first
    """
    workflow_changes: list[ConsolidatedChange] = []
    step_changes: list[ConsolidatedChange] = []

    # Filter for vp_step entities with workflow_name
    workflow_entities = [
        e for e in extracted
        if e.entity_type == "vp_step" and e.raw_data.get("workflow_name")
    ]

    if not workflow_entities:
        return workflow_changes, step_changes

    # Group by workflow_name
    groups: dict[str, list[ExtractedEntity]] = {}
    for entity in workflow_entities:
        wf_name = entity.raw_data["workflow_name"]
        groups.setdefault(wf_name, []).append(entity)

    matcher = SimilarityMatcher(entity_type="feature")

    # Track workflow names to detect pairs
    created_workflows: dict[str, dict] = {}  # name -> {state_type, ...}

    for wf_name, entities in groups.items():
        # Determine state_type from entities in this group
        fact_types = [e.raw_data.get("fact_type", "") for e in entities]
        has_current = any(ft == "current_process" for ft in fact_types)
        has_future = any(ft == "future_process" for ft in fact_types)

        if has_current and not has_future:
            state_type = "current"
        elif has_future and not has_current:
            state_type = "future"
        elif has_current and has_future:
            # Mixed — split into two workflow groups
            state_type = "current"  # Process current first, future below
        else:
            state_type = "future"  # Default

        # Match against existing workflows by name
        match_result = matcher.find_best_match(
            candidate=wf_name,
            corpus=existing_workflows,
            text_field="name",
            id_field="id",
        )

        if not match_result.is_match:
            # If mixed, create both current and future workflows
            if has_current and has_future:
                current_name = wf_name
                future_name = wf_name

                workflow_changes.append(ConsolidatedChange(
                    entity_type="workflow",
                    operation="create",
                    entity_name=current_name,
                    after={
                        "name": current_name,
                        "state_type": "current",
                        "description": f"Current state: {current_name}",
                        "pair_with_name": future_name,
                        "pair_state": "future",
                    },
                    rationale=f"New current-state workflow: {current_name}",
                    confidence=0.75,
                ))
                created_workflows[f"{current_name}::current"] = {"state_type": "current"}

                workflow_changes.append(ConsolidatedChange(
                    entity_type="workflow",
                    operation="create",
                    entity_name=future_name,
                    after={
                        "name": future_name,
                        "state_type": "future",
                        "description": f"Future state: {future_name}",
                        "pair_with_name": current_name,
                        "pair_state": "current",
                    },
                    rationale=f"New future-state workflow: {future_name}",
                    confidence=0.75,
                ))
                created_workflows[f"{future_name}::future"] = {"state_type": "future"}
            else:
                workflow_changes.append(ConsolidatedChange(
                    entity_type="workflow",
                    operation="create",
                    entity_name=wf_name,
                    after={
                        "name": wf_name,
                        "state_type": state_type,
                        "description": f"{'Current' if state_type == 'current' else 'Future'} state: {wf_name}",
                    },
                    rationale=f"New {state_type}-state workflow: {wf_name}",
                    confidence=0.75,
                ))
                created_workflows[f"{wf_name}::{state_type}"] = {"state_type": state_type}

        # Create step changes for each entity in this group
        step_index_counter = len(existing_steps)
        for entity in entities:
            raw = entity.raw_data
            name = extract_name_from_entity(entity)
            if not name:
                continue

            # Determine step's state_type from its fact_type
            ft = raw.get("fact_type", "")
            if ft == "current_process":
                step_state = "current"
            elif ft == "future_process":
                step_state = "future"
            else:
                step_state = state_type

            step_index_counter += 1

            step_data = {
                "label": name,
                "step_index": raw.get("step_index", step_index_counter),
                "description": raw.get("detail") or raw.get("description") or name,
                "workflow_name": wf_name,
                "state_type": step_state,
                "time_minutes": raw.get("time_minutes"),
                "pain_description": raw.get("pain_description"),
                "benefit_description": raw.get("benefit_description"),
                "automation_level": raw.get("automation_level", "manual"),
                "actor_persona_name": raw.get("related_actor"),
            }

            step_changes.append(ConsolidatedChange(
                entity_type="vp_step",
                operation="create",
                entity_name=name,
                after=step_data,
                evidence=[
                    {"excerpt": exc, "source": "signal"}
                    for exc in entity.evidence_excerpts
                ],
                rationale=f"Workflow step ({step_state}): {name}",
                confidence=0.7,
            ))

    logger.info(
        f"Workflow consolidation: {len(workflow_changes)} workflows, {len(step_changes)} steps",
    )

    return workflow_changes, step_changes


def facts_to_entities(facts: list[dict]) -> list[ExtractedEntity]:
    """
    Convert extracted facts to typed entities for consolidation.

    Maps fact_type to entity_type:
    - feature, capability, function → feature
    - persona, user, role → persona
    - process, workflow, flow → vp_step
    - kpi, pain, goal → business_driver
    - competitor, design_inspiration → competitor_ref
    """
    entities = []

    type_mapping = {
        # Features - ONLY user-facing capabilities
        "feature": "feature",
        "capability": "feature",
        "function": "feature",

        # Personas - user archetypes
        "persona": "persona",
        "user": "persona",
        "user_type": "persona",

        # VP Steps - journey steps
        "process": "vp_step",
        "workflow": "vp_step",
        "flow": "vp_step",
        "step": "vp_step",
        "journey": "vp_step",
        "stage": "vp_step",
        "vp_step": "vp_step",
        "current_process": "vp_step",
        "future_process": "vp_step",

        # Stakeholders - people mentioned in signals
        "stakeholder": "stakeholder",
        "actor": "stakeholder",

        # Constraints - technical/business limitations
        "constraint": "constraint",
        "requirement": "constraint",
        "integration": "constraint",
        "data_requirement": "constraint",

        # Risks - go to constraints table with type='risk'
        "risk": "constraint",
        "threat": "constraint",

        # Assumptions - go to constraints table with type='assumption'
        "assumption": "constraint",

        # Business Drivers - KPIs, Pains, Goals → business_drivers table
        "kpi": "business_driver",
        "metric": "business_driver",
        "pain": "business_driver",
        "goal": "business_driver",
        "objective": "business_driver",
        "organizational_goal": "business_driver",

        # Competitor References - competitors and design inspiration
        "competitor": "competitor_ref",
        "design_inspiration": "competitor_ref",
        "feature_inspiration": "competitor_ref",

        # Company Info - client company details
        "company_info": "company_info",

        # Data Entities - domain data objects
        "data_entity": "data_entity",
        "entity": "data_entity",
        "data_object": "data_entity",
        "record_type": "data_entity",
        "model": "data_entity",
    }

    for fact in facts:
        fact_type = fact.get("fact_type", "").lower()
        entity_type = type_mapping.get(fact_type)

        if not entity_type:
            logger.info(
                f"Unmapped fact type '{fact_type}' - title: {fact.get('title', 'unknown')}",
                extra={"fact_type": fact_type, "title": fact.get("title")},
            )
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
                "fact_type": fact_type,  # Pass through for driver_type/reference_type mapping
                # For company_info
                "industry": fact.get("industry"),
                "stage": fact.get("stage"),
                "size": fact.get("size"),
                "client_name": fact.get("client_name"),
                # For business drivers
                "measurement": fact.get("measurement"),
                "timeframe": fact.get("timeframe"),
                # Relationship hints from extraction (for link resolution)
                "related_actor": fact.get("related_actor"),
                "related_process": fact.get("related_process"),
                "addresses_feature": fact.get("addresses_feature"),
                # For competitor refs
                "url": fact.get("url"),
                "category": fact.get("category"),
                # Workflow-aware fields
                "workflow_name": fact.get("workflow_name"),
                "state_type": fact.get("state_type"),
                "time_minutes": fact.get("time_minutes"),
                "pain_description": fact.get("pain_description"),
                "benefit_description": fact.get("benefit_description"),
                "automation_level": fact.get("automation_level"),
            },
            evidence_excerpts=evidence_excerpts,
            source_chunk_ids=[
                str(ev.get("chunk_id", ""))
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

    # Pre-filter entities by type for parallel consolidation
    entities_by_type = {
        "feature": [e for e in all_entities if e.entity_type == "feature"],
        "persona": [e for e in all_entities if e.entity_type == "persona"],
        "vp_step": [e for e in all_entities if e.entity_type == "vp_step"],
        "stakeholder": [e for e in all_entities if e.entity_type == "stakeholder"],
        "constraint": [e for e in all_entities if e.entity_type == "constraint"],
        "business_driver": [e for e in all_entities if e.entity_type == "business_driver"],
        "competitor_ref": [e for e in all_entities if e.entity_type == "competitor_ref"],
        "data_entity": [e for e in all_entities if e.entity_type == "data_entity"],
    }

    # Build task list: (function, filtered_entities, existing_data)
    tasks = {
        "features": (consolidate_features, entities_by_type["feature"], existing["features"]),
        "personas": (consolidate_personas, entities_by_type["persona"], existing["personas"]),
        "vp_steps": (consolidate_vp_steps, entities_by_type["vp_step"], existing["vp_steps"]),
        "stakeholders": (consolidate_stakeholders, entities_by_type["stakeholder"], existing["stakeholders"]),
        "constraints": (consolidate_constraints, entities_by_type["constraint"], existing.get("constraints", [])),
        "business_drivers": (
            lambda ents, exist: consolidate_business_drivers(
                ents, exist,
                existing_personas=existing.get("personas", []),
                existing_features=existing.get("features", []),
                existing_vp_steps=existing.get("vp_steps", []),
            ),
            entities_by_type["business_driver"],
            existing.get("business_drivers", []),
        ),
        "competitor_refs": (consolidate_competitor_refs, entities_by_type["competitor_ref"], existing.get("competitor_refs", [])),
        "company_info": (consolidate_company_info, all_entities, existing.get("company_info")),
        "data_entities": (consolidate_data_entities, entities_by_type["data_entity"], existing.get("data_entities", [])),
    }

    # Execute consolidation functions in parallel (max 5 workers to respect DB pool)
    t_start = time.monotonic()
    results: dict[str, list[ConsolidatedChange]] = {}

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(func, entities, exist): name
            for name, (func, entities, exist) in tasks.items()
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception:
                logger.exception(f"Consolidation failed for {name}, returning empty changes")
                results[name] = []

    t_elapsed = time.monotonic() - t_start
    logger.info(f"Parallel consolidation completed in {t_elapsed:.2f}s")

    features = results["features"]
    personas = results["personas"]
    vp_steps = results["vp_steps"]
    stakeholders = results["stakeholders"]
    constraints = results["constraints"]
    business_drivers = results["business_drivers"]
    competitor_refs = results["competitor_refs"]
    company_info = results["company_info"]
    data_entities = results["data_entities"]

    # Workflow consolidation (runs after parallel block — needs vp_step entities)
    workflow_changes, workflow_step_changes = consolidate_workflows(
        entities_by_type["vp_step"],
        existing.get("workflows", []),
        existing["vp_steps"],
    )
    workflows = workflow_changes
    vp_steps = vp_steps + workflow_step_changes

    # Calculate summary
    all_changes = (
        features + personas + vp_steps + stakeholders + constraints +
        business_drivers + competitor_refs + company_info + data_entities +
        workflows
    )
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
        constraints=constraints,
        business_drivers=business_drivers,
        competitor_refs=competitor_refs,
        company_info=company_info,
        data_entities=data_entities,
        workflows=workflows,
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
            "constraints": len(constraints),
            "business_drivers": len(business_drivers),
            "competitor_refs": len(competitor_refs),
            "company_info": len(company_info),
            "data_entities": len(data_entities),
            "workflows": len(workflows),
        },
    )

    return result
