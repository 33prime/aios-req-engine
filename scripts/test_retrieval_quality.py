#!/usr/bin/env python3
"""
Interactive retrieval quality testing harness.

Runs queries through the full retrieval pipeline (multi-vector + graph expansion),
displays results in a grading-friendly format, and tracks scores.

Usage:
    # Interactive mode — asks questions, shows results, you grade them
    python scripts/test_retrieval_quality.py --project-id <uuid>

    # Run predefined queries and show results
    python scripts/test_retrieval_quality.py --project-id <uuid> --auto

    # Run a single query
    python scripts/test_retrieval_quality.py --project-id <uuid> --query "What's the biggest risk?"
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# Query sets for different testing angles
# =============================================================================

AUTO_QUERIES = [
    # Intent: broad questions that test "what would someone ask if they need X"
    {"query": "What's causing the most pain for users?", "category": "intent"},
    {"query": "What should we build first and why?", "category": "intent"},
    {"query": "Where are we wasting the most time?", "category": "intent"},

    # Synonym: vocabulary the entities don't literally contain
    {"query": "What are the compliance requirements?",  "category": "synonym"},
    {"query": "Where do things break down?", "category": "synonym"},
    {"query": "What manual processes exist?", "category": "synonym"},

    # Cross-entity: should pull from multiple entity types
    {"query": "How do the workflows connect to user pain points?", "category": "cross"},
    {"query": "Which features address the biggest business drivers?", "category": "cross"},

    # Strategic: broad questions that benefit from convergence
    {"query": "What's the overall health of this project?", "category": "strategic"},
    {"query": "Give me an executive summary of what we know", "category": "strategic"},

    # Link-aware: should surface relationships
    {"query": "What depends on what in this system?", "category": "links"},
    {"query": "What are the key connections between entities?", "category": "links"},
]


async def run_query(project_id: str, query: str, use_multivector: bool = True) -> dict:
    """Run a single query through the retrieval pipeline."""
    from app.core.embeddings import embed_texts_async
    from app.db.supabase_client import get_supabase

    sb = get_supabase()
    results = {"query": query, "entities": [], "links": [], "outcomes": []}

    try:
        embeddings = await embed_texts_async([query])
        if not embeddings:
            return results

        embedding = embeddings[0]

        if use_multivector:
            # Search all 4 vector types in parallel
            vector_types = ["identity", "intent", "relationship", "status"]
            weights = {"intent": 0.4, "identity": 0.3, "relationship": 0.2, "status": 0.1}

            entity_scores = {}
            for vtype in vector_types:
                try:
                    resp = sb.rpc("match_entity_vectors", {
                        "query_embedding": embedding,
                        "match_count": 8,
                        "filter_project_id": project_id,
                        "filter_vector_type": vtype,
                    }).execute()

                    w = weights.get(vtype, 0.1)
                    for row in (resp.data or []):
                        eid = row["entity_id"]
                        sim = float(row.get("similarity", 0))
                        if eid not in entity_scores:
                            entity_scores[eid] = {
                                "entity_id": eid,
                                "entity_type": row.get("entity_type", ""),
                                "weighted_score": 0.0,
                                "vector_hits": {},
                            }
                        entity_scores[eid]["weighted_score"] += sim * w
                        entity_scores[eid]["vector_hits"][vtype] = round(sim, 4)
                except Exception:
                    pass

            # Sort and get top 10
            ranked = sorted(entity_scores.values(), key=lambda x: x["weighted_score"], reverse=True)[:10]

            # Resolve names
            for entity in ranked:
                eid = entity["entity_id"]
                etype = entity["entity_type"]
                name = _resolve_entity_name(sb, etype, eid, project_id)
                entity["name"] = name

                # Check if it's an outcome
                if etype == "outcome":
                    results["outcomes"].append(entity)
                elif etype == "link":
                    results["links"].append(entity)
                else:
                    results["entities"].append(entity)

        else:
            # Legacy single-vector search
            resp = sb.rpc("match_entities", {
                "query_embedding": embedding,
                "match_count": 10,
                "filter_project_id": project_id,
            }).execute()
            for row in (resp.data or []):
                results["entities"].append({
                    "entity_id": row.get("entity_id"),
                    "entity_type": row.get("entity_type"),
                    "name": row.get("entity_name", ""),
                    "weighted_score": float(row.get("similarity", 0)),
                    "vector_hits": {"legacy": round(float(row.get("similarity", 0)), 4)},
                })

    except Exception as e:
        results["error"] = str(e)

    return results


def _resolve_entity_name(sb, entity_type: str, entity_id: str, project_id: str) -> str:
    """Resolve entity name from its table."""
    table_map = {
        "feature": ("features", "name"),
        "persona": ("personas", "name"),
        "business_driver": ("business_drivers", "description"),
        "workflow": ("workflows", "name"),
        "constraint": ("constraints", "title"),
        "stakeholder": ("stakeholders", "name"),
        "data_entity": ("data_entities", "name"),
        "vp_step": ("vp_steps", "label"),
        "outcome": ("outcomes", "title"),
        "outcome_capability": ("outcome_capabilities", "name"),
    }

    mapping = table_map.get(entity_type)
    if not mapping:
        return f"[{entity_type}:{entity_id[:8]}]"

    table, name_col = mapping
    try:
        resp = sb.table(table).select(name_col).eq("id", entity_id).maybe_single().execute()
        if resp.data:
            return resp.data.get(name_col, "")[:80]
    except Exception:
        pass
    return f"[{entity_type}:{entity_id[:8]}]"


def format_results(results: dict) -> str:
    """Format results for display."""
    lines = []
    lines.append(f"\n{'='*70}")
    lines.append(f"  QUERY: \"{results['query']}\"")
    lines.append(f"{'='*70}")

    if results.get("error"):
        lines.append(f"  ERROR: {results['error']}")
        return "\n".join(lines)

    # Entities
    entities = results.get("entities", [])
    if entities:
        lines.append(f"\n  ENTITIES ({len(entities)} results):")
        for i, e in enumerate(entities, 1):
            name = e.get("name", "?")[:60]
            etype = e.get("entity_type", "?")
            score = e.get("weighted_score", 0)
            hits = e.get("vector_hits", {})
            hit_str = " | ".join(f"{k}={v:.3f}" for k, v in sorted(hits.items()))
            lines.append(f"    {i}. [{etype:18s}] {name}")
            lines.append(f"       Score: {score:.4f}  ({hit_str})")

    # Outcomes
    outcomes = results.get("outcomes", [])
    if outcomes:
        lines.append(f"\n  OUTCOMES ({len(outcomes)} results):")
        for i, o in enumerate(outcomes, 1):
            name = o.get("name", "?")[:60]
            score = o.get("weighted_score", 0)
            lines.append(f"    {i}. {name}")
            lines.append(f"       Score: {score:.4f}")

    # Links
    links = results.get("links", [])
    if links:
        lines.append(f"\n  LINKS ({len(links)} results):")
        for i, l in enumerate(links, 1):
            lines.append(f"    {i}. {l.get('name', '?')}")

    total = len(entities) + len(outcomes) + len(links)
    if total == 0:
        lines.append("\n  NO RESULTS FOUND")

    lines.append("")
    return "\n".join(lines)


async def run_auto(project_id: str):
    """Run predefined queries and display results."""
    print(f"\nRunning {len(AUTO_QUERIES)} queries against project {project_id[:8]}...\n")

    for bq in AUTO_QUERIES:
        results = await run_query(project_id, bq["query"])
        print(format_results(results))
        print(f"  Category: {bq['category']}")
        print(f"  Entities found: {len(results.get('entities', []))}")
        print(f"  Outcomes found: {len(results.get('outcomes', []))}")
        print("-" * 70)


async def run_single(project_id: str, query: str):
    """Run a single query and display detailed results."""
    print(f"\nQuerying: \"{query}\"")

    # Run both legacy and multi-vector for comparison
    print("\n--- LEGACY (single vector) ---")
    legacy = await run_query(project_id, query, use_multivector=False)
    print(format_results(legacy))

    print("\n--- MULTI-VECTOR (enriched) ---")
    multi = await run_query(project_id, query, use_multivector=True)
    print(format_results(multi))

    # Compare
    legacy_ids = {e["entity_id"] for e in legacy.get("entities", [])}
    multi_ids = {e["entity_id"] for e in multi.get("entities", [])}
    new_finds = multi_ids - legacy_ids
    if new_finds:
        print(f"\n  NEW ENTITIES found by multi-vector ({len(new_finds)}):")
        for e in multi.get("entities", []):
            if e["entity_id"] in new_finds:
                print(f"    + [{e['entity_type']}] {e.get('name', '?')[:60]}")


async def main():
    parser = argparse.ArgumentParser(description="Test retrieval quality")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--auto", action="store_true", help="Run predefined queries")
    parser.add_argument("--query", type=str, help="Run a single query")
    args = parser.parse_args()

    if args.query:
        await run_single(args.project_id, args.query)
    elif args.auto:
        await run_auto(args.project_id)
    else:
        # Interactive mode
        print(f"\nInteractive retrieval testing for project {args.project_id[:8]}")
        print("Type a query and press Enter. Type 'quit' to exit.\n")
        while True:
            try:
                query = input("Query> ").strip()
                if query.lower() in ("quit", "exit", "q"):
                    break
                if not query:
                    continue
                results = await run_query(args.project_id, query)
                print(format_results(results))
            except (EOFError, KeyboardInterrupt):
                break


if __name__ == "__main__":
    asyncio.run(main())
