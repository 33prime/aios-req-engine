#!/usr/bin/env python3
"""
Before/After benchmark for the Entity Intelligence Upgrade.

Runs a set of test queries against the retrieval pipeline, records results,
then optionally runs enrichment + multi-vector backfill and re-runs the
same queries to show the improvement.

Usage:
    # Step 1: Record baseline (before enrichment)
    python scripts/benchmark_before_after.py --project-id <uuid> --phase before

    # Step 2: Run enrichment backfill on the project
    python scripts/backfill_enrichment.py --project-id <uuid>

    # Step 3: Enable multi-vector and record results
    # Set USE_MULTI_VECTOR=true in env, then:
    python scripts/benchmark_before_after.py --project-id <uuid> --phase after

    # Step 4: Compare
    python scripts/benchmark_before_after.py --project-id <uuid> --phase compare

    # Or run everything in one shot:
    python scripts/benchmark_before_after.py --project-id <uuid> --phase full
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import get_logger

logger = get_logger(__name__)

RESULTS_DIR = Path(__file__).parent / ".benchmark_results"


# =============================================================================
# Benchmark queries — designed to test different retrieval dimensions
# =============================================================================

BENCHMARK_QUERIES = [
    # Intent queries (should improve most with multi-vector)
    {"query": "What's causing the biggest pain?", "type": "intent", "description": "Broad pain query"},
    {"query": "What should we focus on next?", "type": "intent", "description": "Strategic priority"},
    {"query": "How does data flow through the system?", "type": "intent", "description": "Architecture query"},
    {"query": "Who are the key decision makers?", "type": "intent", "description": "Stakeholder query"},
    {"query": "What's blocking progress?", "type": "intent", "description": "Blocker query"},

    # Specific entity queries (baseline should already handle these)
    {"query": "What features are must-have?", "type": "specific", "description": "Feature priority"},
    {"query": "What workflows exist?", "type": "specific", "description": "Workflow listing"},
    {"query": "What constraints do we have?", "type": "specific", "description": "Constraint listing"},

    # Cross-entity queries (should improve with relationship vectors)
    {"query": "How do the personas relate to the features?", "type": "cross", "description": "Persona-feature mapping"},
    {"query": "What's the connection between the pain points and the solution?", "type": "cross", "description": "Pain-solution link"},

    # Synonym/vocabulary gap queries (should improve dramatically with expanded_terms)
    {"query": "Where are the bottlenecks?", "type": "synonym", "description": "Synonym for pain/constraint"},
    {"query": "What needs automation?", "type": "synonym", "description": "Implied feature need"},
    {"query": "Risk areas in the project", "type": "synonym", "description": "Synonym for constraints/blockers"},
]


# =============================================================================
# Run benchmark
# =============================================================================


async def run_benchmark(project_id: str, phase: str) -> dict:
    """Run benchmark queries and record results."""
    from app.core.embeddings import embed_texts_async
    from app.db.supabase_client import get_supabase

    sb = get_supabase()
    results = {
        "project_id": project_id,
        "phase": phase,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "queries": [],
    }

    # Get project info
    try:
        proj = sb.table("projects").select("name").eq("id", project_id).single().execute()
        results["project_name"] = proj.data.get("name", "Unknown")
    except Exception:
        results["project_name"] = "Unknown"

    # Count entities
    entity_counts = {}
    for etype, table in [
        ("features", "features"), ("personas", "personas"),
        ("business_drivers", "business_drivers"), ("workflows", "workflows"),
        ("constraints", "constraints"), ("stakeholders", "stakeholders"),
    ]:
        try:
            resp = sb.table(table).select("id", count="exact").eq("project_id", project_id).execute()
            entity_counts[etype] = resp.count or 0
        except Exception:
            entity_counts[etype] = 0
    results["entity_counts"] = entity_counts

    # Count enriched entities (after phase)
    try:
        ev_resp = sb.table("entity_vectors").select("id", count="exact").eq("project_id", project_id).execute()
        results["entity_vectors_count"] = ev_resp.count or 0
    except Exception:
        results["entity_vectors_count"] = 0

    # Run each query
    for bq in BENCHMARK_QUERIES:
        query = bq["query"]
        logger.info(f"  [{bq['type']}] {query}")

        try:
            # Method 1: Legacy match_entities (single vector)
            legacy_results = []
            try:
                embeddings = await embed_texts_async([query])
                if embeddings:
                    resp = sb.rpc("match_entities", {
                        "query_embedding": embeddings[0],
                        "match_count": 5,
                        "filter_project_id": project_id,
                    }).execute()
                    legacy_results = [
                        {
                            "entity_id": r.get("entity_id"),
                            "entity_type": r.get("entity_type"),
                            "entity_name": r.get("entity_name"),
                            "similarity": round(float(r.get("similarity", 0)), 4),
                        }
                        for r in (resp.data or [])
                    ]
            except Exception as e:
                logger.debug(f"Legacy search failed: {e}")

            # Method 2: Multi-vector match_entity_vectors (if table has data)
            multivector_results = {}
            for vtype in ["identity", "intent", "relationship", "status"]:
                try:
                    embeddings = await embed_texts_async([query])
                    if embeddings:
                        resp = sb.rpc("match_entity_vectors", {
                            "query_embedding": embeddings[0],
                            "match_count": 5,
                            "filter_project_id": project_id,
                            "filter_vector_type": vtype,
                        }).execute()
                        multivector_results[vtype] = [
                            {
                                "entity_id": r.get("entity_id"),
                                "entity_type": r.get("entity_type"),
                                "similarity": round(float(r.get("similarity", 0)), 4),
                            }
                            for r in (resp.data or [])
                        ]
                except Exception:
                    multivector_results[vtype] = []

            results["queries"].append({
                "query": query,
                "type": bq["type"],
                "description": bq["description"],
                "legacy_results": legacy_results,
                "legacy_top_sim": legacy_results[0]["similarity"] if legacy_results else 0,
                "legacy_count": len(legacy_results),
                "multivector_results": multivector_results,
                "multivector_intent_count": len(multivector_results.get("intent", [])),
                "multivector_intent_top_sim": (
                    multivector_results.get("intent", [{}])[0].get("similarity", 0)
                    if multivector_results.get("intent") else 0
                ),
            })

        except Exception as e:
            logger.warning(f"Query failed: {e}")
            results["queries"].append({
                "query": query, "type": bq["type"], "error": str(e),
            })

    return results


def save_results(results: dict, phase: str, project_id: str) -> Path:
    """Save results to JSON file."""
    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / f"{project_id}_{phase}.json"
    path.write_text(json.dumps(results, indent=2, default=str))
    logger.info(f"Results saved to {path}")
    return path


def compare_results(project_id: str) -> None:
    """Compare before and after results."""
    before_path = RESULTS_DIR / f"{project_id}_before.json"
    after_path = RESULTS_DIR / f"{project_id}_after.json"

    if not before_path.exists():
        logger.error("No 'before' results found. Run with --phase before first.")
        return
    if not after_path.exists():
        logger.error("No 'after' results found. Run with --phase after first.")
        return

    before = json.loads(before_path.read_text())
    after = json.loads(after_path.read_text())

    print("\n" + "=" * 70)
    print(f"BEFORE/AFTER COMPARISON — {before.get('project_name', 'Unknown')}")
    print("=" * 70)

    print(f"\nEntity vectors: {before.get('entity_vectors_count', 0)} → {after.get('entity_vectors_count', 0)}")
    print(f"Entity counts: {json.dumps(before.get('entity_counts', {}))}")

    print(f"\n{'Query':<45} {'Type':<10} {'Before':<10} {'After':<10} {'Delta':<10} {'New Entities'}")
    print("-" * 95)

    improvements = 0
    for bq, aq in zip(before.get("queries", []), after.get("queries", [])):
        query = bq.get("query", "?")[:44]
        qtype = bq.get("type", "?")

        # Compare legacy (before) vs intent vector (after)
        before_sim = bq.get("legacy_top_sim", 0)
        after_intent_sim = aq.get("multivector_intent_top_sim", 0)
        after_legacy_sim = aq.get("legacy_top_sim", 0)

        # Use whichever is better in the after case
        after_best = max(after_intent_sim, after_legacy_sim)
        delta = after_best - before_sim

        # Count entities found in after but not in before
        before_ids = {r.get("entity_id") for r in bq.get("legacy_results", [])}
        after_ids = set()
        for vtype_results in aq.get("multivector_results", {}).values():
            for r in vtype_results:
                after_ids.add(r.get("entity_id"))
        new_entities = len(after_ids - before_ids)

        indicator = "↑" if delta > 0.01 else ("↓" if delta < -0.01 else "=")
        if delta > 0.01:
            improvements += 1

        print(f"{query:<45} {qtype:<10} {before_sim:<10.4f} {after_best:<10.4f} {indicator}{abs(delta):<9.4f} +{new_entities}")

    print("-" * 95)
    total = len(before.get("queries", []))
    print(f"\n{improvements}/{total} queries improved ({improvements/total*100:.0f}%)")

    # Show intent vector unique finds
    print("\n--- Intent Vector Unique Finds ---")
    for aq in after.get("queries", []):
        intent_results = aq.get("multivector_results", {}).get("intent", [])
        legacy_ids = {r.get("entity_id") for r in aq.get("legacy_results", [])}
        unique = [r for r in intent_results if r.get("entity_id") not in legacy_ids]
        if unique:
            print(f"  [{aq.get('type')}] \"{aq.get('query')}\"")
            for u in unique[:3]:
                print(f"    → {u.get('entity_type')}: sim={u.get('similarity', 0):.4f}")


async def run_full_benchmark(project_id: str) -> None:
    """Run full before/after benchmark including enrichment."""
    print("\n=== PHASE 1: Recording baseline (before enrichment) ===\n")
    before = await run_benchmark(project_id, "before")
    save_results(before, "before", project_id)

    print("\n=== PHASE 2: Running enrichment backfill ===\n")
    from scripts.backfill_enrichment import process_entity_type, ENTITY_TYPES

    for etype in ENTITY_TYPES:
        await process_entity_type(etype, project_id=project_id)

    print("\n=== PHASE 3: Recording results (after enrichment) ===\n")
    after = await run_benchmark(project_id, "after")
    save_results(after, "after", project_id)

    print("\n=== PHASE 4: Generating outcomes ===\n")
    try:
        from app.chains.generate_outcomes import generate_outcomes, persist_generated_outcomes
        from app.db.outcomes import list_outcomes
        from app.db.supabase_client import get_supabase

        sb = get_supabase()
        entity_graph = {}
        for etype, table in [
            ("personas", "personas"), ("business_drivers", "business_drivers"),
            ("features", "features"), ("workflows", "workflows"), ("constraints", "constraints"),
        ]:
            resp = sb.table(table).select("*").eq("project_id", project_id).execute()
            entity_graph[etype] = resp.data or []

        existing = list_outcomes(UUID(project_id))
        result = await generate_outcomes(UUID(project_id), entity_graph, existing)
        created = await persist_generated_outcomes(UUID(project_id), result, entity_graph)

        print(f"  Outcomes generated: {len(created)}")
        if result.get("macro_outcome"):
            print(f"  Macro outcome: {result['macro_outcome'][:80]}")
        for o in created:
            print(f"  - [{o.get('horizon', '?')}] {o.get('title', '?')}")

        # Score outcomes
        from app.chains.score_outcomes import score_and_persist_outcome
        for o in created:
            try:
                await score_and_persist_outcome(outcome_id=str(o["id"]))
            except Exception:
                pass

    except Exception as e:
        print(f"  Outcome generation failed: {e}")

    print("\n=== COMPARISON ===\n")
    compare_results(project_id)


async def main():
    parser = argparse.ArgumentParser(description="Before/after benchmark for Entity Intelligence Upgrade")
    parser.add_argument("--project-id", required=True, help="Project UUID")
    parser.add_argument("--phase", choices=["before", "after", "compare", "full"], required=True)
    args = parser.parse_args()

    if args.phase == "before":
        results = await run_benchmark(args.project_id, "before")
        save_results(results, "before", args.project_id)
        print(f"\nBaseline recorded: {len(results.get('queries', []))} queries")

    elif args.phase == "after":
        results = await run_benchmark(args.project_id, "after")
        save_results(results, "after", args.project_id)
        print(f"\nAfter recorded: {len(results.get('queries', []))} queries")

    elif args.phase == "compare":
        compare_results(args.project_id)

    elif args.phase == "full":
        await run_full_benchmark(args.project_id)


if __name__ == "__main__":
    asyncio.run(main())
