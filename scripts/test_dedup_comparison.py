"""Dry-run comparison: Current 4-tier dedup vs Graph-aware dedup.

Extracts EntityPatches from the BenyBox discovery call transcript,
runs both dedup strategies, and shows side-by-side results.

Does NOT write anything to the database.

Usage:
    uv run python scripts/test_dedup_comparison.py
"""

import asyncio
import copy
import json
from dataclasses import dataclass
from uuid import UUID

# ── Constants ───────────────────────────────────────────────────────────────
PROJECT_ID = UUID("517d1c9c-80ca-419c-99b2-48c74c67117d")
SIGNAL_ID = UUID("a89fa3fd-62f4-43a4-ac15-4f64dd0e08db")
RUN_ID = UUID("d848d51d-a579-45fd-9214-8d3eaf1c4887")

# ── Graph-aware dedup logic ─────────────────────────────────────────────────

@dataclass
class GraphDedupResult:
    """Result of graph-aware dedup check for a single patch."""
    patch_name: str
    entity_type: str
    decision: str  # "merge" or "keep_new"
    matched_entity_name: str | None = None
    matched_entity_id: str | None = None
    overlap_score: float = 0.0
    shared_connections: list[str] | None = None
    reason: str = ""


async def graph_aware_dedup_check(
    create_patches,  # list[EntityPatch] — only creates that survived 4-tier
    entity_inventory: dict[str, list[dict]],
    project_id: UUID,
) -> list[GraphDedupResult]:
    """Check surviving create patches against existing entities using graph neighborhoods.

    For each create patch:
    1. Extract its declared links (personas, drivers, features it connects to)
    2. For each existing entity of the same type, get its graph neighborhood
    3. Compute connection overlap (Jaccard-like)
    4. If overlap > threshold → suggest merge
    """
    from app.db.graph_queries import get_entity_neighborhood

    results: list[GraphDedupResult] = []

    for patch in create_patches:
        patch_name = patch.payload.get("name") or patch.payload.get("description", "")[:60]
        entity_type = patch.entity_type

        # Get existing entities of the same type
        existing = entity_inventory.get(entity_type, [])
        if not existing:
            results.append(GraphDedupResult(
                patch_name=patch_name,
                entity_type=entity_type,
                decision="keep_new",
                reason="No existing entities of this type",
            ))
            continue

        # Extract patch's declared connections (from links field)
        patch_connections: set[str] = set()
        for link in patch.links:
            if link.target_name:
                patch_connections.add(link.target_name.lower().strip())
            if link.target_type:
                patch_connections.add(f"{link.target_type}:{link.target_name or ''}".lower())

        # Also extract connection hints from evidence quotes
        evidence_text = " ".join(e.quote.lower() for e in patch.evidence if e.quote)

        best_match = None
        best_overlap = 0.0
        best_shared: list[str] = []

        for entity in existing:
            entity_id = entity["id"]
            entity_name = entity.get("name", "")

            # Get graph neighborhood for existing entity
            try:
                neighborhood = await asyncio.to_thread(
                    get_entity_neighborhood,
                    entity_id=UUID(entity_id),
                    entity_type=entity_type,
                    project_id=project_id,
                    max_related=10,
                    depth=1,
                    apply_confidence=True,
                )
            except Exception:
                continue

            if not neighborhood:
                continue

            # Build existing entity's connection set
            existing_connections: set[str] = set()
            related = neighborhood.get("related", [])
            for rel in related:
                rel_name = rel.get("entity_name", "").lower().strip()
                rel_type = rel.get("entity_type", "")
                if rel_name:
                    existing_connections.add(rel_name)
                    existing_connections.add(f"{rel_type}:{rel_name}")

            if not existing_connections and not patch_connections:
                continue

            # Compute overlap: Jaccard similarity of connection sets
            # Also check if patch evidence mentions the existing entity's connections
            shared = patch_connections & existing_connections

            # Bonus: check if patch evidence text mentions existing entity's neighbors
            evidence_matches = set()
            for conn in existing_connections:
                conn_name = conn.split(":")[-1] if ":" in conn else conn
                if conn_name and len(conn_name) > 3 and conn_name in evidence_text:
                    evidence_matches.add(conn_name)

            all_shared = shared | evidence_matches
            union = patch_connections | existing_connections
            overlap = len(all_shared) / max(len(union), 1)

            # Also factor in semantic similarity of names (soft signal)
            try:
                from rapidfuzz import fuzz
                name_sim = fuzz.token_set_ratio(
                    patch_name.lower(), entity_name.lower()
                ) / 100.0
            except ImportError:
                name_sim = 0.0

            # Combined score: connection overlap + name similarity bonus
            combined = overlap * 0.7 + name_sim * 0.3

            if combined > best_overlap:
                best_overlap = combined
                best_match = entity
                best_shared = sorted(all_shared)

        # Decision threshold
        if best_match and best_overlap >= 0.35:
            results.append(GraphDedupResult(
                patch_name=patch_name,
                entity_type=entity_type,
                decision="merge",
                matched_entity_name=best_match.get("name", ""),
                matched_entity_id=best_match["id"],
                overlap_score=round(best_overlap, 3),
                shared_connections=best_shared,
                reason=f"Graph overlap {best_overlap:.0%} — shared connections: {', '.join(best_shared[:5])}",
            ))
        else:
            results.append(GraphDedupResult(
                patch_name=patch_name,
                entity_type=entity_type,
                decision="keep_new",
                overlap_score=round(best_overlap, 3) if best_match else 0.0,
                matched_entity_name=best_match.get("name", "") if best_match else None,
                shared_connections=best_shared if best_shared else None,
                reason=f"Low overlap ({best_overlap:.0%})" if best_match else "No graph connections found",
            ))

    return results


# ── Main ────────────────────────────────────────────────────────────────────

async def main():
    from app.chains.extract_entity_patches import extract_entity_patches
    from app.core.context_snapshot import build_context_snapshot
    from app.core.entity_dedup import dedup_create_patches
    from app.core.schemas_entity_patch import EntityPatchList
    from app.db.supabase_client import get_supabase

    print("=" * 70)
    print("DEDUP COMPARISON: Current 4-Tier vs Graph-Aware")
    print("=" * 70)
    print()

    # ── Load signal text ────────────────────────────────────────────────
    print("[1/5] Loading signal text...")
    sb = get_supabase()
    signal = sb.table("signals").select("raw_text, metadata").eq(
        "id", str(SIGNAL_ID)
    ).single().execute().data
    signal_text = signal["raw_text"]
    print(f"  → {len(signal_text)} chars")

    # ── Build context snapshot ──────────────────────────────────────────
    print("[2/5] Building context snapshot (5-layer)...")
    snapshot = await build_context_snapshot(PROJECT_ID)
    inventory = snapshot.entity_inventory

    print("  → Current entity inventory:")
    for etype, entities in sorted(inventory.items()):
        if entities:
            names = [e.get("name", "?") for e in entities]
            print(f"    {etype} ({len(entities)}): {', '.join(names)}")

    # ── Extract patches ─────────────────────────────────────────────────
    print()
    print("[3/5] Extracting EntityPatches via Sonnet...")
    patch_list = await extract_entity_patches(
        signal_text=signal_text,
        signal_type="meeting_transcript",
        context_snapshot=snapshot,
        source_authority="client",
        signal_id=str(SIGNAL_ID),
        run_id=str(RUN_ID),
    )

    all_patches = patch_list.patches
    creates = [p for p in all_patches if p.operation == "create"]
    merges = [p for p in all_patches if p.operation == "merge"]
    updates = [p for p in all_patches if p.operation == "update"]

    print(f"  → Extracted {len(all_patches)} patches: "
          f"{len(creates)} create, {len(merges)} merge, {len(updates)} update")
    print()

    # Show all extracted patches
    print("  ┌─ RAW EXTRACTION (before dedup) ─────────────────────────")
    for i, p in enumerate(all_patches, 1):
        name = p.payload.get("name") or p.payload.get("description", "")[:60]
        links_str = ""
        if p.links:
            link_names = [f"{l.target_type}:{l.target_name}" for l in p.links[:3]]
            links_str = f" → links: {', '.join(link_names)}"
        target = f" → {p.target_entity_id[:12]}..." if p.target_entity_id else ""
        print(f"  │ {i:2d}. [{p.operation:6s}] {p.entity_type:18s} "
              f"\"{name}\"{target}{links_str}")
    print("  └────────────────────────────────────────────────────────")
    print()

    # ── Run current 4-tier dedup ────────────────────────────────────────
    print("[4/5] Running CURRENT 4-tier dedup...")
    # Deep copy patches so we can compare both results
    patches_for_current = copy.deepcopy(all_patches)

    deduped_current = await dedup_create_patches(
        patches_for_current,
        inventory,
        PROJECT_ID,
    )

    current_creates = [p for p in deduped_current if p.operation == "create"]
    current_merges = [p for p in deduped_current if p.operation == "merge"]
    converted = len(creates) - len(current_creates)

    print(f"  → After dedup: {len(current_creates)} create, {len(current_merges)} merge")
    print(f"  → Converted {converted} creates → merges")
    print()

    # Show dedup decisions
    print("  ┌─ CURRENT DEDUP RESULTS ─────────────────────────────────")
    for p in deduped_current:
        name = p.payload.get("name") or p.payload.get("description", "")[:60]
        if p.operation == "merge" and p.target_entity_id:
            # Find target name
            target_name = "?"
            for etype_entities in inventory.values():
                for e in etype_entities:
                    if e["id"] == p.target_entity_id:
                        target_name = e.get("name", "?")
                        break
            print(f"  │ [MERGE ] {p.entity_type:18s} \"{name}\" → \"{target_name}\"")
        elif p.operation == "create":
            print(f"  │ [CREATE] {p.entity_type:18s} \"{name}\"")
        else:
            print(f"  │ [{p.operation:6s}] {p.entity_type:18s} \"{name}\"")
    print("  └────────────────────────────────────────────────────────")
    print()

    # ── Run graph-aware dedup on surviving creates ──────────────────────
    surviving_creates = [p for p in deduped_current if p.operation == "create"]

    if not surviving_creates:
        print("[5/5] No surviving creates to test graph-aware dedup on.")
    else:
        print(f"[5/5] Running GRAPH-AWARE dedup on {len(surviving_creates)} surviving creates...")
        graph_results = await graph_aware_dedup_check(
            surviving_creates,
            inventory,
            PROJECT_ID,
        )

        graph_would_merge = [r for r in graph_results if r.decision == "merge"]
        graph_would_keep = [r for r in graph_results if r.decision == "keep_new"]

        print(f"  → Graph-aware would additionally merge: {len(graph_would_merge)}")
        print(f"  → Graph-aware keeps as new: {len(graph_would_keep)}")
        print()

        print("  ┌─ GRAPH-AWARE DEDUP RESULTS ─────────────────────────────")
        for r in graph_results:
            if r.decision == "merge":
                print(f"  │ [MERGE ] {r.entity_type:18s} \"{r.patch_name}\"")
                print(f"  │          → into \"{r.matched_entity_name}\" "
                      f"(overlap: {r.overlap_score:.0%})")
                if r.shared_connections:
                    print(f"  │          shared: {', '.join(r.shared_connections[:5])}")
            else:
                print(f"  │ [NEW   ] {r.entity_type:18s} \"{r.patch_name}\"")
                if r.matched_entity_name:
                    print(f"  │          closest: \"{r.matched_entity_name}\" "
                          f"(overlap: {r.overlap_score:.0%}) — too low")
                else:
                    print(f"  │          {r.reason}")
        print("  └────────────────────────────────────────────────────────")

    # ── Summary ─────────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Raw extraction:        {len(creates)} creates, "
          f"{len(merges)} merges, {len(updates)} updates")
    print(f"  After 4-tier dedup:    {len(current_creates)} creates, "
          f"{len(current_merges)} merges")
    print(f"    → Converted:         {converted} create→merge")

    if surviving_creates:
        final_creates = len(graph_would_keep) if 'graph_would_keep' in dir() else len(surviving_creates)
        additional_merges = len(graph_would_merge) if 'graph_would_merge' in dir() else 0
        print(f"  After graph-aware:     {final_creates} creates, "
              f"{len(current_merges) + additional_merges} merges")
        print(f"    → Additional merges: {additional_merges}")

        if additional_merges > 0:
            print()
            print("  GRAPH-AWARE CAUGHT THESE DUPLICATES:")
            for r in graph_would_merge:
                print(f"    • \"{r.patch_name}\" is really \"{r.matched_entity_name}\"")
                print(f"      because they share: {', '.join(r.shared_connections[:4])}")

    print()
    print("─" * 70)
    print("NO DATA WAS WRITTEN. This was a dry run.")
    print("─" * 70)


if __name__ == "__main__":
    asyncio.run(main())
