"""Query per-document extraction data for People Pulse project."""
import json
import sys

# Add project root to path
sys.path.insert(0, "/Users/matt/aios-req-engine")

from app.db.supabase_client import get_supabase

PROJECT_ID = "634647e8-a22a-4b6f-b42a-452659620bc4"

def main():
    sb = get_supabase()

    # ─── 0. Get all signals for this project ───
    print("=" * 80)
    print("PEOPLE PULSE PROJECT — PER-DOCUMENT EXTRACTION DATA")
    print("=" * 80)

    signals_resp = (
        sb.table("signals")
        .select("id, signal_type, source, created_at, metadata")
        .eq("project_id", PROJECT_ID)
        .order("created_at", desc=False)
        .execute()
    )
    signals = signals_resp.data or []
    print(f"\nTotal signals: {len(signals)}")

    for i, sig in enumerate(signals):
        sig_name = sig.get("metadata", {}).get("filename") or sig.get("metadata", {}).get("subject") or sig.get("source", "unknown")
        print(f"  [{i+1}] {sig['id'][:12]}... | type={sig['signal_type']} | source={sig['source']} | name={sig_name}")

    # ─── 1. Signal chunks per signal ───
    print("\n" + "=" * 80)
    print("1. SIGNAL CHUNKS PER DOCUMENT")
    print("=" * 80)

    for i, sig in enumerate(signals):
        sig_id = sig["id"]
        sig_name = sig.get("metadata", {}).get("filename") or sig.get("metadata", {}).get("subject") or sig.get("source", "unknown")

        chunks_resp = (
            sb.table("signal_chunks")
            .select("id, chunk_index, content, metadata, start_char, end_char, embedding")
            .eq("signal_id", sig_id)
            .order("chunk_index", desc=False)
            .execute()
        )
        chunks = chunks_resp.data or []

        print(f"\n  Signal [{i+1}]: {sig_name} ({sig['signal_type']})")
        print(f"    Chunk count: {len(chunks)}")

        if chunks:
            sample = chunks[0]
            has_embedding = sample.get("embedding") is not None
            content_preview = (sample.get("content") or "")[:150].replace("\n", " ")
            print(f"    Sample chunk (index={sample['chunk_index']}):")
            print(f"      content (first 150 chars): {content_preview}")
            print(f"      start_char={sample.get('start_char')}, end_char={sample.get('end_char')}")
            print(f"      embedding exists: {has_embedding}")

            meta = sample.get("metadata", {})
            print(f"      metadata keys: {list(meta.keys()) if meta else '(empty)'}")
            if meta:
                for k, v in meta.items():
                    v_str = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                    if len(v_str) > 120:
                        v_str = v_str[:120] + "..."
                    print(f"        {k}: {v_str}")

    # ─── 2. Meta-tag enrichment data ───
    print("\n" + "=" * 80)
    print("2. META-TAG ENRICHMENT DATA ON CHUNKS")
    print("=" * 80)

    META_TAG_KEYS = ["entities_mentioned", "topics", "decision_made", "speaker_roles", "temporal", "confidence_signals"]

    # Gather all chunks across project
    all_chunk_ids = []
    for sig in signals:
        chunks_resp = (
            sb.table("signal_chunks")
            .select("id, metadata")
            .eq("signal_id", sig["id"])
            .execute()
        )
        all_chunk_ids.extend(chunks_resp.data or [])

    total_chunks = len(all_chunk_ids)
    print(f"\n  Total chunks across all signals: {total_chunks}")

    if total_chunks > 0:
        # Check which meta-tag keys exist
        key_counts = {k: 0 for k in META_TAG_KEYS}
        other_keys = set()

        for chunk in all_chunk_ids:
            meta = chunk.get("metadata", {})
            if meta:
                for k in META_TAG_KEYS:
                    if k in meta:
                        key_counts[k] += 1
                for k in meta.keys():
                    if k not in META_TAG_KEYS:
                        other_keys.add(k)

        print(f"\n  Meta-tag key presence across {total_chunks} chunks:")
        for k, count in key_counts.items():
            pct = (count / total_chunks * 100) if total_chunks > 0 else 0
            print(f"    {k}: {count}/{total_chunks} ({pct:.0f}%)")

        if other_keys:
            print(f"\n  Other metadata keys found: {sorted(other_keys)}")

        # Show a sample enriched chunk if any
        enriched_sample = None
        for chunk in all_chunk_ids:
            meta = chunk.get("metadata", {})
            if meta and any(k in meta for k in META_TAG_KEYS):
                enriched_sample = chunk
                break

        if enriched_sample:
            print(f"\n  Sample enriched chunk ({enriched_sample['id'][:12]}...):")
            meta = enriched_sample.get("metadata", {})
            for k in META_TAG_KEYS:
                if k in meta:
                    v_str = json.dumps(meta[k])
                    if len(v_str) > 200:
                        v_str = v_str[:200] + "..."
                    print(f"    {k}: {v_str}")
        else:
            print("\n  No chunks have meta-tag enrichment keys.")

    # ─── 3. Signal impact per signal ───
    print("\n" + "=" * 80)
    print("3. SIGNAL IMPACT PER SIGNAL (entity_type breakdown)")
    print("=" * 80)

    for i, sig in enumerate(signals):
        sig_id = sig["id"]
        sig_name = sig.get("metadata", {}).get("filename") or sig.get("metadata", {}).get("subject") or sig.get("source", "unknown")

        impact_resp = (
            sb.table("signal_impact")
            .select("entity_type, entity_id, usage_context, chunk_id")
            .eq("signal_id", sig_id)
            .execute()
        )
        impacts = impact_resp.data or []

        # Group by entity_type
        by_type = {}
        for imp in impacts:
            et = imp["entity_type"]
            by_type.setdefault(et, []).append(imp)

        print(f"\n  Signal [{i+1}]: {sig_name}")
        print(f"    Total impact records: {len(impacts)}")
        if by_type:
            for et, items in sorted(by_type.items()):
                unique_entities = len(set(item["entity_id"] for item in items))
                unique_chunks = len(set(item["chunk_id"] for item in items))
                contexts = set(item["usage_context"] for item in items)
                print(f"    {et}: {len(items)} records, {unique_entities} unique entities, {unique_chunks} unique chunks, contexts={contexts}")
        else:
            print("    (no impact records)")

    # ─── 4. Entity-level provenance ───
    print("\n" + "=" * 80)
    print("4. ENTITY-LEVEL PROVENANCE (entities per signal)")
    print("=" * 80)

    # Entity table name mapping
    ENTITY_TABLES = {
        "feature": ("features", "name"),
        "persona": ("personas", "name"),
        "vp_step": ("vp_steps", "name"),
        "data_entity": ("data_entities", "name"),
        "insight": ("insights", "title"),
        "prd_section": ("prd_sections", "title"),  # may not exist
    }

    for i, sig in enumerate(signals):
        sig_id = sig["id"]
        sig_name = sig.get("metadata", {}).get("filename") or sig.get("metadata", {}).get("subject") or sig.get("source", "unknown")

        impact_resp = (
            sb.table("signal_impact")
            .select("entity_type, entity_id")
            .eq("signal_id", sig_id)
            .execute()
        )
        impacts = impact_resp.data or []

        # Deduplicate
        entity_set = set()
        for imp in impacts:
            entity_set.add((imp["entity_type"], imp["entity_id"]))

        print(f"\n  Signal [{i+1}]: {sig_name}")
        print(f"    Unique entities: {len(entity_set)}")

        if not entity_set:
            print("    (none)")
            continue

        # Group by type and resolve names
        by_type = {}
        for et, eid in entity_set:
            by_type.setdefault(et, []).append(eid)

        for et, eids in sorted(by_type.items()):
            table_name, name_col = ENTITY_TABLES.get(et, (None, None))
            names = []

            if table_name:
                try:
                    for eid in eids:
                        resp = (
                            sb.table(table_name)
                            .select(f"id, {name_col}")
                            .eq("id", eid)
                            .execute()
                        )
                        if resp.data:
                            names.append(resp.data[0].get(name_col, "(unnamed)"))
                        else:
                            names.append(f"(not found: {eid[:12]}...)")
                except Exception as e:
                    names = [f"(query error: {e})"]

            print(f"    {et} ({len(eids)}):")
            if names:
                for name in sorted(names):
                    print(f"      - {name}")
            else:
                for eid in eids:
                    print(f"      - {eid}")

    # ─── 5. Memory nodes ───
    print("\n" + "=" * 80)
    print("5. MEMORY NODES FOR PROJECT")
    print("=" * 80)

    mem_resp = (
        sb.table("memory_nodes")
        .select("id, node_type, summary, content, confidence, source_type, source_id, linked_entity_type, linked_entity_id, chunk_id, source_quote, speaker_name, is_active")
        .eq("project_id", PROJECT_ID)
        .eq("is_active", True)
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    mem_nodes = mem_resp.data or []

    print(f"\n  Active memory nodes: {len(mem_nodes)}")

    if mem_nodes:
        # Stats
        by_type = {}
        has_source_quote = 0
        has_speaker_name = 0
        has_chunk_id = 0
        has_source_id = 0

        for mn in mem_nodes:
            by_type.setdefault(mn["node_type"], 0)
            by_type[mn["node_type"]] += 1
            if mn.get("source_quote"):
                has_source_quote += 1
            if mn.get("speaker_name"):
                has_speaker_name += 1
            if mn.get("chunk_id"):
                has_chunk_id += 1
            if mn.get("source_id"):
                has_source_id += 1

        print(f"  By type: {by_type}")
        print(f"  Has source_quote: {has_source_quote}/{len(mem_nodes)}")
        print(f"  Has speaker_name: {has_speaker_name}/{len(mem_nodes)}")
        print(f"  Has chunk_id: {has_chunk_id}/{len(mem_nodes)}")
        print(f"  Has source_id: {has_source_id}/{len(mem_nodes)}")

        # Check if any source_ids match our signal IDs
        signal_ids = set(s["id"] for s in signals)
        linked_to_signals = sum(1 for mn in mem_nodes if mn.get("source_id") in signal_ids)
        print(f"  Linked to project signals: {linked_to_signals}/{len(mem_nodes)}")

        # Show a few samples
        print(f"\n  Sample memory nodes (up to 5):")
        for mn in mem_nodes[:5]:
            print(f"\n    [{mn['node_type']}] {mn['summary'][:100]}")
            print(f"      confidence={mn['confidence']}, source_type={mn.get('source_type')}")
            if mn.get("source_quote"):
                sq = mn["source_quote"][:120].replace("\n", " ")
                print(f"      source_quote: {sq}...")
            if mn.get("speaker_name"):
                print(f"      speaker_name: {mn['speaker_name']}")
            if mn.get("chunk_id"):
                print(f"      chunk_id: {mn['chunk_id'][:12]}...")
            if mn.get("linked_entity_type"):
                print(f"      linked_entity: {mn['linked_entity_type']} / {mn.get('linked_entity_id', 'N/A')}")
    else:
        print("  (no memory nodes)")

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)


if __name__ == "__main__":
    main()
