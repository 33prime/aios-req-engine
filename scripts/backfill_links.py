#!/usr/bin/env python3
"""
Backfill link enrichment + embedding for entity_dependencies.

For each dependency with enrichment_status='pending':
1. Resolve source and target entity names
2. Generate link description text
3. Embed the link in entity_vectors with entity_type='link'
4. Mark enrichment_status='enriched'

Usage:
    python scripts/backfill_links.py --project-id <uuid>
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import get_logger

logger = get_logger(__name__)

TABLE_MAP = {
    "feature": ("features", "name"),
    "persona": ("personas", "name"),
    "business_driver": ("business_drivers", "description"),
    "workflow": ("workflows", "name"),
    "constraint": ("constraints", "title"),
    "stakeholder": ("stakeholders", "name"),
    "data_entity": ("data_entities", "name"),
    "vp_step": ("vp_steps", "label"),
    "competitor": ("competitor_references", "name"),
    "solution_flow_step": ("solution_flow_steps", "title"),
}


def _resolve_name(sb, entity_type: str, entity_id: str) -> str:
    """Resolve entity name from its table."""
    mapping = TABLE_MAP.get(entity_type)
    if not mapping:
        return f"[{entity_type}]"
    table, col = mapping
    try:
        resp = sb.table(table).select(col).eq("id", entity_id).maybe_single().execute()
        if resp.data:
            return (resp.data.get(col) or "")[:80]
    except Exception:
        pass
    return f"[{entity_type}:{entity_id[:8]}]"


async def backfill_links(project_id: str) -> dict:
    """Enrich and embed all entity_dependencies for a project."""
    from app.core.embeddings import embed_texts_async
    from app.db.supabase_client import get_supabase

    sb = get_supabase()
    start = time.monotonic()

    # Get all dependencies for this project
    deps = (
        sb.table("entity_dependencies")
        .select("*")
        .eq("project_id", project_id)
        .is_("superseded_by", "null")
        .execute()
    ).data or []

    if not deps:
        print("No dependencies found.")
        return {"total": 0, "enriched": 0, "embedded": 0}

    print(f"Found {len(deps)} dependencies to process.")

    # Build name cache to avoid N+1 queries
    name_cache: dict[str, str] = {}
    entity_ids_by_type: dict[str, set] = {}
    for d in deps:
        for prefix in ["source", "target"]:
            etype = d.get(f"{prefix}_entity_type", "")
            eid = d.get(f"{prefix}_entity_id", "")
            if etype and eid:
                entity_ids_by_type.setdefault(etype, set()).add(eid)

    for etype, eids in entity_ids_by_type.items():
        mapping = TABLE_MAP.get(etype)
        if not mapping:
            continue
        table, col = mapping
        try:
            resp = sb.table(table).select(f"id, {col}").in_("id", list(eids)).execute()
            for row in (resp.data or []):
                name_cache[row["id"]] = (row.get(col) or "")[:80]
        except Exception as e:
            logger.debug(f"Name cache build failed for {etype}: {e}")

    enriched = 0
    embedded = 0

    # Process in batches
    batch_texts = []
    batch_deps = []

    for dep in deps:
        source_name = name_cache.get(dep["source_entity_id"], f"[{dep['source_entity_type']}]")
        target_name = name_cache.get(dep["target_entity_id"], f"[{dep['target_entity_type']}]")
        dep_type = dep.get("dependency_type", "related")

        # Build link embedding text
        text = f"{source_name} → {dep_type} → {target_name}"

        # Add enrichment data if we have it
        dep_enrichment = dep.get("enrichment") or {}
        mechanism = dep_enrichment.get("mechanism", "")
        if mechanism:
            text += f"\nMechanism: {mechanism}"
        questions = dep_enrichment.get("hypothetical_questions", [])
        if questions:
            text += "\nQuestions this relationship answers:\n" + "\n".join(f"- {q}" for q in questions)

        if len(text.strip()) >= 10:
            batch_texts.append(text)
            batch_deps.append(dep)

        # Process in batches of 20
        if len(batch_texts) >= 20:
            embedded += await _embed_batch(sb, batch_texts, batch_deps, project_id)
            enriched += len(batch_texts)
            batch_texts = []
            batch_deps = []
            await asyncio.sleep(0.3)

    # Final batch
    if batch_texts:
        embedded += await _embed_batch(sb, batch_texts, batch_deps, project_id)
        enriched += len(batch_texts)

    # Mark all as enriched
    for dep in deps:
        try:
            sb.table("entity_dependencies").update({
                "enrichment_status": "enriched",
            }).eq("id", dep["id"]).execute()
        except Exception:
            pass

    elapsed = time.monotonic() - start
    print(f"\nLink backfill complete:")
    print(f"  Total: {len(deps)}")
    print(f"  Enriched: {enriched}")
    print(f"  Embedded: {embedded}")
    print(f"  Duration: {elapsed:.1f}s")

    return {"total": len(deps), "enriched": enriched, "embedded": embedded}


async def _embed_batch(sb, texts: list[str], deps: list[dict], project_id: str) -> int:
    """Embed a batch of link texts and store in entity_vectors."""
    from app.core.embeddings import embed_texts_async

    try:
        embeddings = await embed_texts_async(texts)
        if len(embeddings) != len(texts):
            return 0

        count = 0
        for i, (text, dep, emb) in enumerate(zip(texts, deps, embeddings)):
            try:
                sb.table("entity_vectors").upsert(
                    {
                        "entity_id": dep["id"],
                        "entity_type": "link",
                        "project_id": project_id,
                        "vector_type": "identity",
                        "embedding": emb,
                        "source_text": text[:500],
                        "updated_at": "now()",
                    },
                    on_conflict="entity_id,entity_type,vector_type",
                ).execute()
                count += 1
            except Exception as e:
                logger.debug(f"Link embed failed for {dep['id']}: {e}")

        return count
    except Exception as e:
        logger.warning(f"Batch embedding failed: {e}")
        return 0


async def main():
    parser = argparse.ArgumentParser(description="Backfill link enrichment + embedding")
    parser.add_argument("--project-id", required=True)
    args = parser.parse_args()

    await backfill_links(args.project_id)


if __name__ == "__main__":
    asyncio.run(main())
