"""Missed extraction recovery — re-scan signal chunks for entities that
should have been extracted but weren't.

When pulse detects a chain gap (e.g., feature has no linked pain point):
1. Query signal_impact for chunks mentioning the feature
2. Re-scan those specific chunks with a focused extraction prompt
3. If found → create entity + link (standard patch pipeline)
4. If not found → surface as gap in briefing

Key constraint: Only recover from existing signal chunks. Never fabricate.

Usage:
    from app.core.missed_extraction import recover_missing_entities
    results = await recover_missing_entities(project_id, gap_entities)
"""

from __future__ import annotations

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


async def recover_missing_entities(
    project_id: UUID,
    gap_entities: list[dict],
    max_chunks_per_entity: int = 5,
) -> dict:
    """Re-scan signal chunks for entities missing from value chains.

    Args:
        project_id: Project UUID
        gap_entities: List of dicts with {entity_type, entity_id, entity_name, missing_link_types}
            e.g., [{"entity_type": "feature", "entity_id": "...", "entity_name": "Dashboard",
                    "missing_link_types": ["addresses"]}]
        max_chunks_per_entity: Max chunks to re-scan per gap entity

    Returns:
        Dict with {recovered: [{entity_type, entity_id, link_type, found_name}],
                   unresolved: [{entity_type, entity_id, entity_name}]}
    """
    from app.db.supabase_client import get_supabase

    sb = get_supabase()
    recovered: list[dict] = []
    unresolved: list[dict] = []

    for gap in gap_entities:
        entity_id = gap.get("entity_id", "")
        entity_name = gap.get("entity_name", "")
        entity_type = gap.get("entity_type", "")
        missing_types = gap.get("missing_link_types", [])

        if not entity_id or not missing_types:
            continue

        # 1. Get chunks mentioning this entity
        try:
            impact_result = (
                sb.table("signal_impact")
                .select("chunk_id")
                .eq("entity_id", entity_id)
                .limit(max_chunks_per_entity)
                .execute()
            )
            chunk_ids = list({
                r["chunk_id"] for r in (impact_result.data or [])
                if r.get("chunk_id")
            })
        except Exception as e:
            logger.debug(f"Failed to get chunks for {entity_id}: {e}")
            unresolved.append(gap)
            continue

        if not chunk_ids:
            unresolved.append(gap)
            continue

        # 2. Get chunk content
        try:
            chunks_result = (
                sb.table("signal_chunks")
                .select("id, content")
                .in_("id", chunk_ids[:max_chunks_per_entity])
                .execute()
            )
            chunks = chunks_result.data or []
        except Exception as e:
            logger.debug(f"Failed to get chunk content for {entity_id}: {e}")
            unresolved.append(gap)
            continue

        if not chunks:
            unresolved.append(gap)
            continue

        # 3. Re-scan with focused prompt
        found = await _focused_rescan(
            project_id=project_id,
            entity_name=entity_name,
            entity_type=entity_type,
            missing_types=missing_types,
            chunks=chunks,
        )

        if found:
            recovered.extend(found)
        else:
            unresolved.append(gap)

    if recovered:
        logger.info(
            f"Missed extraction recovery: {len(recovered)} entities recovered, "
            f"{len(unresolved)} unresolved"
        )

    return {
        "recovered": recovered,
        "unresolved": unresolved,
    }


async def _focused_rescan(
    project_id: UUID,
    entity_name: str,
    entity_type: str,
    missing_types: list[str],
    chunks: list[dict],
) -> list[dict]:
    """Re-scan chunks with a focused extraction prompt.

    Looks for specific relationship types (pain points, personas, workflows)
    mentioned alongside the target entity.
    """
    try:
        from anthropic import AsyncAnthropic

        from app.core.config import Settings

        settings = Settings()
        if not settings.ANTHROPIC_API_KEY:
            return []

        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        # Build focused context
        chunk_text = "\n\n---\n\n".join(
            c.get("content", "")[:2000] for c in chunks
        )

        type_descriptions = {
            "addresses": "pain points, problems, or challenges",
            "targets": "personas, user roles, or stakeholders",
            "actor_of": "workflows, processes, or activities",
            "enables": "capabilities, goals, or outcomes",
        }
        looking_for = ", ".join(
            type_descriptions.get(t, t) for t in missing_types
        )

        prompt = (
            f"Analyze these text excerpts and identify any "
            f"{looking_for} mentioned alongside "
            f'"{entity_name}" (a {entity_type}).\n\n'
            f"## Text Excerpts\n{chunk_text}\n\n"
            f"## Task\n"
            f"For each relationship found, return a JSON array:\n"
            f"- \"name\": the entity name found\n"
            f"- \"type\": entity type "
            f"(persona, business_driver, workflow, feature)\n"
            f"- \"link_type\": relationship type "
            f"({', '.join(missing_types)})\n"
            f"- \"evidence_quote\": exact text implying this\n\n"
            f"Return ONLY a JSON array. Return [] if nothing "
            f"found. Do NOT fabricate — only extract what is "
            f"explicitly stated in the text."
        )

        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )

        import json
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]

        results = json.loads(text.strip())
        if not isinstance(results, list):
            return []

        # Process each found entity through the standard pipeline
        recovered = []
        for item in results:
            if not isinstance(item, dict):
                continue
            found_name = item.get("name", "")
            found_type = item.get("type", "")
            link_type = item.get("link_type", "")
            if found_name and found_type and link_type:
                # Create through standard patch pipeline
                try:
                    created = await _create_recovered_entity(
                        project_id=project_id,
                        entity_name=found_name,
                        entity_type=found_type,
                        source_entity_type=entity_type,
                        source_entity_name=entity_name,
                        link_type=link_type,
                        chunk_ids=[c.get("id", "") for c in chunks if c.get("id")],
                    )
                    if created:
                        recovered.append(created)
                except Exception as e:
                    logger.debug(f"Failed to create recovered entity: {e}")

        return recovered

    except Exception as e:
        logger.debug(f"Focused rescan failed: {e}")
        return []


async def _create_recovered_entity(
    project_id: UUID,
    entity_name: str,
    entity_type: str,
    source_entity_type: str,
    source_entity_name: str,
    link_type: str,
    chunk_ids: list[str],
) -> dict | None:
    """Create a recovered entity using the standard patch pipeline."""
    from app.core.schemas_entity_patch import EntityLink, EntityPatch, EvidenceRef
    from app.db.patch_applicator import apply_entity_patches

    # Build payload based on entity type
    payload: dict = {}
    if entity_type == "business_driver":
        payload = {
            "title": entity_name,
            "description": f"Recovered from context of {source_entity_name}",
            "driver_type": "pain",
        }
    elif entity_type == "persona":
        payload = {"name": entity_name, "role": entity_name, "goals": [], "pain_points": []}
    elif entity_type == "workflow":
        payload = {"name": entity_name, "description": f"Related to {source_entity_name}"}
    elif entity_type == "feature":
        payload = {"name": entity_name, "overview": f"Related to {source_entity_name}"}
    else:
        return None

    patch = EntityPatch(
        operation="create",
        entity_type=entity_type,
        payload=payload,
        confidence="medium",
        confidence_reasoning="Recovered via missed extraction analysis",
        source_authority="research",
        evidence=[
            EvidenceRef(chunk_id=cid, quote=f"Mentioned alongside {source_entity_name}")
            for cid in chunk_ids[:2]
        ],
        links=[
            EntityLink(
                target_type=source_entity_type,
                target_name=source_entity_name,
                link_type=link_type,
            )
        ],
    )

    result = await apply_entity_patches(
        project_id=project_id,
        patches=[patch],
        signal_id=None,
        run_id=None,
    )

    if result.applied:
        applied = result.applied[0]
        return {
            "entity_type": entity_type,
            "entity_id": applied.get("entity_id"),
            "entity_name": entity_name,
            "link_type": link_type,
            "recovered_from": source_entity_name,
        }

    return None
