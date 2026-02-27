"""One-time script to enrich all entities for PersonaPulse project.

Steps:
  1. Fix titles (8 words max) for drivers and features
  2. Enrich all drivers (pain, goal, kpi)
  3. Backfill driver links (evidence overlap)
  4. Enrich all features
  5. Generate "what led to this solution" narrative from signals

Usage:
    uv run python scripts/enrich_persona_pulse.py
"""

import asyncio
import sys
import traceback
from uuid import UUID

PROJECT_ID = "43ee2e56-00f9-48e9-9dbc-4fded7c3255b"
MAX_WORDS = 8
HAIKU_MODEL = "claude-haiku-4-5-20251001"


# ── Helpers ──────────────────────────────────────────────────────────


def _needs_fix(title: str | None) -> bool:
    if not title:
        return False
    return len(title.split()) > MAX_WORDS


async def _generate_title(client, entity_kind: str, description: str, current_title: str) -> str:
    prompt = (
        f"Generate an {MAX_WORDS}-word-max noun-phrase headline for this {entity_kind}. "
        f"Return ONLY the headline, no quotes, no explanation.\n\n"
        f"Current title: {current_title}\n"
        f"Description: {description[:500]}"
    )
    response = await client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=60,
        temperature=0.0,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip().strip('"').strip("'")
    words = text.split()
    if len(words) > MAX_WORDS:
        text = " ".join(words[:MAX_WORDS]) + "..."
    return text


# ── Step 1: Fix titles ──────────────────────────────────────────────


async def step_fix_titles():
    from anthropic import AsyncAnthropic

    from app.db.supabase_client import get_supabase

    print("\n" + "=" * 60)
    print("STEP 1: Fix titles (8 words max)")
    print("=" * 60)

    anthropic = AsyncAnthropic()
    sb = get_supabase()

    # Drivers
    drivers_resp = (
        sb.table("business_drivers")
        .select("id, title, description, driver_type")
        .eq("project_id", PROJECT_ID)
        .in_("driver_type", ["goal", "pain"])
        .execute()
    )
    long_drivers = [d for d in (drivers_resp.data or []) if _needs_fix(d.get("title"))]

    # Features
    features_resp = (
        sb.table("features")
        .select("id, name, overview")
        .eq("project_id", PROJECT_ID)
        .execute()
    )
    long_features = [f for f in (features_resp.data or []) if _needs_fix(f.get("name"))]

    total = len(long_drivers) + len(long_features)
    if total == 0:
        print("  All titles already ≤8 words. Skipping.")
        return

    print(f"  Found {len(long_drivers)} drivers and {len(long_features)} features to fix.\n")

    for d in long_drivers:
        old = d["title"]
        kind = "business goal" if d["driver_type"] == "goal" else "pain point"
        new = await _generate_title(anthropic, kind, d.get("description", ""), old)
        print(f"  [{d['driver_type'].upper():>4}] {old}")
        print(f"       → {new}")
        sb.table("business_drivers").update({
            "title": new, "updated_at": "now()"
        }).eq("id", d["id"]).execute()

    for f in long_features:
        old = f["name"]
        new = await _generate_title(anthropic, "feature", f.get("overview", ""), old)
        print(f"  [FEAT] {old}")
        print(f"       → {new}")
        sb.table("features").update({
            "name": new, "updated_at": "now()"
        }).eq("id", f["id"]).execute()

    print(f"\n  ✓ Fixed {total} titles.")


# ── Step 2: Enrich all drivers ──────────────────────────────────────


async def step_enrich_drivers():
    from app.chains.enrich_goal import enrich_goal
    from app.chains.enrich_kpi import enrich_kpi
    from app.chains.enrich_pain_point import enrich_pain_point
    from app.db.supabase_client import get_supabase

    print("\n" + "=" * 60)
    print("STEP 2: Enrich all drivers")
    print("=" * 60)

    sb = get_supabase()
    pid = UUID(PROJECT_ID)

    resp = (
        sb.table("business_drivers")
        .select("id, title, driver_type, enrichment_status")
        .eq("project_id", PROJECT_ID)
        .execute()
    )
    drivers = resp.data or []
    print(f"  Found {len(drivers)} drivers total.\n")

    enrichers = {
        "pain": enrich_pain_point,
        "goal": enrich_goal,
        "kpi": enrich_kpi,
    }

    enriched = 0
    skipped = 0
    failed = 0

    for d in drivers:
        dtype = d.get("driver_type", "")
        did = UUID(d["id"])
        title = d.get("title") or d["id"][:8]
        status = d.get("enrichment_status", "none")

        if status == "enriched":
            print(f"  [{dtype.upper():>4}] {title} — already enriched, skipping")
            skipped += 1
            continue

        enricher = enrichers.get(dtype)
        if not enricher:
            print(f"  [{dtype.upper():>4}] {title} — no enricher for type, skipping")
            skipped += 1
            continue

        try:
            print(f"  [{dtype.upper():>4}] {title} — enriching...", end=" ", flush=True)
            result = await enricher(driver_id=did, project_id=pid)
            if result.get("success"):
                fields = result.get("updated_fields", [])
                print(f"✓ ({len(fields)} fields)")
                enriched += 1
            else:
                print(f"✗ ({result.get('error', 'unknown')})")
                failed += 1
        except Exception as e:
            print(f"✗ ({e})")
            failed += 1

    print(f"\n  ✓ Enriched: {enriched}, Skipped: {skipped}, Failed: {failed}")


# ── Step 3: Backfill driver links ───────────────────────────────────


def step_backfill_links():
    from app.db.business_drivers import backfill_driver_links

    print("\n" + "=" * 60)
    print("STEP 3: Backfill driver links")
    print("=" * 60)

    pid = UUID(PROJECT_ID)
    stats = backfill_driver_links(pid)
    print(f"  Drivers updated:  {stats.get('drivers_updated', 0)}")
    print(f"  Features linked:  {stats.get('features_linked', 0)}")
    print(f"  Personas linked:  {stats.get('personas_linked', 0)}")
    print(f"  Workflows linked: {stats.get('workflows_linked', 0)}")
    print("  ✓ Done.")


# ── Step 4: Enrich all features ─────────────────────────────────────


def step_enrich_features():
    from app.chains.enrich_features import enrich_feature
    from app.core.config import Settings
    from app.core.feature_enrich_inputs import get_feature_enrich_context
    from app.db.supabase_client import get_supabase

    print("\n" + "=" * 60)
    print("STEP 4: Enrich all features")
    print("=" * 60)

    pid = UUID(PROJECT_ID)
    settings = Settings()
    sb = get_supabase()

    # Get features
    resp = (
        sb.table("features")
        .select("id, name, overview, enrichment_status, confirmation_status")
        .eq("project_id", PROJECT_ID)
        .execute()
    )
    features = resp.data or []
    to_enrich = [f for f in features if f.get("enrichment_status") != "enriched"]

    print(f"  Found {len(features)} features, {len(to_enrich)} need enrichment.\n")

    if not to_enrich:
        print("  All features already enriched. Skipping.")
        return

    # Build context once for the whole project
    context = get_feature_enrich_context(project_id=pid)

    enriched = 0
    failed = 0

    for f in to_enrich:
        name = f.get("name") or f["id"][:8]
        try:
            print(f"  [FEAT] {name} — enriching...", end=" ", flush=True)
            result = enrich_feature(
                project_id=pid,
                feature=f,
                context=context,
                settings=settings,
            )
            # Save enrichment
            from app.db.features import update_feature_enrichment
            update_feature_enrichment(
                feature_id=UUID(f["id"]),
                overview=result.details.summary or f.get("overview", ""),
                target_personas=[p.model_dump() for p in (result.details.target_personas or [])] if hasattr(result.details, "target_personas") and result.details.target_personas else [],
                user_actions=[],
                system_behaviors=[],
                ui_requirements=[],
                rules=[r.rule for r in (result.details.business_rules or [])] if result.details.business_rules else [],
                integrations=[i.system for i in (result.details.integrations or [])] if result.details.integrations else [],
            )
            print("✓")
            enriched += 1
        except Exception as e:
            print(f"✗ ({e})")
            traceback.print_exc()
            failed += 1

    print(f"\n  ✓ Enriched: {enriched}, Failed: {failed}")


# ── Step 5: Generate "what led to this solution" narrative ──────────


async def step_generate_narrative():
    from app.chains.compose_need_narrative import compose_need_narrative
    from app.db.supabase_client import get_supabase

    print("\n" + "=" * 60)
    print('STEP 5: Generate "What Led to This Solution" narrative')
    print("=" * 60)

    sb = get_supabase()

    # Load project vision
    proj = sb.table("projects").select("vision").eq("id", PROJECT_ID).single().execute()
    vision = proj.data.get("vision") if proj.data else None

    # Load pains and goals
    drivers = (
        sb.table("business_drivers")
        .select("id, title, description, driver_type")
        .eq("project_id", PROJECT_ID)
        .in_("driver_type", ["pain", "goal"])
        .execute()
    )
    pains = [d for d in (drivers.data or []) if d["driver_type"] == "pain"]
    goals = [d for d in (drivers.data or []) if d["driver_type"] == "goal"]

    # Load signal excerpts (from signal chunks)
    signals_resp = (
        sb.table("signals")
        .select("id, title, source_type")
        .eq("project_id", PROJECT_ID)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )
    signal_ids = [s["id"] for s in (signals_resp.data or [])]

    excerpts = []
    if signal_ids:
        chunks_resp = (
            sb.table("signal_chunks")
            .select("content, signal_id")
            .in_("signal_id", signal_ids)
            .limit(20)
            .execute()
        )
        sig_map = {s["id"]: s for s in (signals_resp.data or [])}
        for c in (chunks_resp.data or []):
            sig = sig_map.get(c.get("signal_id"), {})
            excerpts.append({
                "excerpt": (c.get("content") or "")[:200],
                "source_type": sig.get("source_type", "signal"),
            })

    print(f"  Vision: {'Yes' if vision else 'No'}")
    print(f"  Pain points: {len(pains)}")
    print(f"  Goals: {len(goals)}")
    print(f"  Signal excerpts: {len(excerpts)}")
    print("  Generating narrative...", end=" ", flush=True)

    result = await compose_need_narrative(
        project_id=PROJECT_ID,
        vision=vision,
        pain_points=pains,
        goals=goals,
        signal_excerpts=excerpts,
    )

    if result:
        print("✓\n")
        print("  ── Narrative ──")
        print(f"  {result['text']}\n")
        if result.get("anchors"):
            print("  ── Anchors ──")
            for a in result["anchors"]:
                print(f'  • "{a["excerpt"][:100]}..."')
                print(f'    ({a["rationale"]})')
        print("\n  ✓ Cached in synthesized_memory_cache.")
    else:
        print("✗ (No narrative generated)")


# ── Main ─────────────────────────────────────────────────────────────


async def main():
    print(f"╔{'═' * 58}╗")
    print(f"║  PersonaPulse Full Enrichment Run{' ' * 24}║")
    print(f"║  Project: {PROJECT_ID}  ║")
    print(f"╚{'═' * 58}╝")

    await step_fix_titles()
    await step_enrich_drivers()
    step_backfill_links()
    step_enrich_features()
    await step_generate_narrative()

    print("\n" + "=" * 60)
    print("ALL DONE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
