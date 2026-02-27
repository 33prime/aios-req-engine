"""One-time script to regenerate titles for entities with >8 words.

Usage:
    uv run python scripts/fix_titles.py <project_id>

Loads all business_drivers (goals + pains) and features with long titles,
calls Haiku to generate 8-word-max noun-phrase headlines, and updates the DB.
"""

import asyncio
import sys
from uuid import UUID

from app.core.config import Settings
from app.db.supabase_client import get_supabase

MAX_WORDS = 8
HAIKU_MODEL = "claude-haiku-4-5-20251001"


def _needs_fix(title: str | None) -> bool:
    """Check if a title exceeds the word limit."""
    if not title:
        return False
    return len(title.split()) > MAX_WORDS


async def _generate_title(client, entity_kind: str, description: str, current_title: str) -> str:
    """Generate a concise title using Haiku."""
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
    # Enforce word limit on output too
    words = text.split()
    if len(words) > MAX_WORDS:
        text = " ".join(words[:MAX_WORDS]) + "..."
    return text


async def fix_titles(project_id: str) -> None:
    """Fix long titles for all entities in a project."""
    from anthropic import AsyncAnthropic

    settings = Settings()
    anthropic = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    sb = get_supabase()

    print(f"Fixing titles for project {project_id}...")
    print(f"Max words: {MAX_WORDS}\n")

    # Load business drivers (goals + pains only)
    drivers_resp = (
        sb.table("business_drivers")
        .select("id, title, description, driver_type")
        .eq("project_id", project_id)
        .in_("driver_type", ["goal", "pain"])
        .execute()
    )
    long_drivers = [d for d in (drivers_resp.data or []) if _needs_fix(d.get("title"))]

    # Load features
    features_resp = (
        sb.table("features")
        .select("id, name, overview")
        .eq("project_id", project_id)
        .execute()
    )
    long_features = [f for f in (features_resp.data or []) if _needs_fix(f.get("name"))]

    total = len(long_drivers) + len(long_features)
    if total == 0:
        print("No entities need title fixes.")
        return

    print(f"Found {len(long_drivers)} drivers and {len(long_features)} features to fix.\n")

    # Fix drivers
    for d in long_drivers:
        old_title = d["title"]
        kind = "business goal" if d["driver_type"] == "goal" else "pain point"
        new_title = await _generate_title(anthropic, kind, d.get("description", ""), old_title)

        print(f"  [{d['driver_type'].upper()}] {d['id'][:8]}...")
        print(f"    Before: {old_title}")
        print(f"    After:  {new_title}")

        sb.table("business_drivers").update({
            "title": new_title,
            "updated_at": "now()",
        }).eq("id", d["id"]).execute()

    # Fix features
    for f in long_features:
        old_name = f["name"]
        new_name = await _generate_title(anthropic, "feature", f.get("overview", ""), old_name)

        print(f"  [FEATURE] {f['id'][:8]}...")
        print(f"    Before: {old_name}")
        print(f"    After:  {new_name}")

        sb.table("features").update({
            "name": new_name,
            "updated_at": "now()",
        }).eq("id", f["id"]).execute()

    print(f"\nDone. Updated {total} entities.")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/fix_titles.py <project_id>")
        sys.exit(1)

    project_id = sys.argv[1]
    # Validate UUID
    try:
        UUID(project_id)
    except ValueError:
        print(f"Invalid project_id: {project_id}")
        sys.exit(1)

    asyncio.run(fix_titles(project_id))


if __name__ == "__main__":
    main()
