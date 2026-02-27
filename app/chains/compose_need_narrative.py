"""Compose the 'What Drove the Need' narrative for the BRD page.

Single Sonnet call given project's top pains, goals, vision, and signal excerpts.
Cached in synthesized_memory_cache under key 'need_narrative'.
"""

from __future__ import annotations

import json
import logging
import time

from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = """You are a requirements engineering narrative writer.
Given a project's pain points, goals, vision, and signal excerpts,
compose a concise 3-5 sentence narrative that tells the story of WHY this project exists.

The narrative should flow: pain discovered → realization → goals formed → value potential.
Write in third person, professional tone. Do NOT use bullet points.
Be specific — reference actual pains and goals by name when possible.
Keep it under 120 words."""

NEED_NARRATIVE_TOOL = {
    "name": "submit_need_narrative",
    "description": "Submit the 'What Drove the Need' narrative with supporting evidence anchors.",
    "input_schema": {
        "type": "object",
        "properties": {
            "narrative": {
                "type": "string",
                "description": "3-5 sentence narrative telling the story of why this project exists.",
            },
            "anchors": {
                "type": "array",
                "description": "2-3 signal excerpts that ground the narrative.",
                "items": {
                    "type": "object",
                    "properties": {
                        "excerpt": {"type": "string"},
                        "source_type": {"type": "string"},
                        "rationale": {"type": "string"},
                    },
                    "required": ["excerpt", "source_type", "rationale"],
                },
            },
        },
        "required": ["narrative", "anchors"],
    },
}


async def compose_need_narrative(
    project_id: str,
    vision: str | None,
    pain_points: list[dict],
    goals: list[dict],
    signal_excerpts: list[dict],
) -> dict | None:
    """Generate and cache the need narrative.

    Returns dict with keys: text, anchors, generated_at.
    Returns None if generation fails or no context available.
    """
    if not pain_points and not goals:
        return None

    try:
        from anthropic import Anthropic

        client = Anthropic()

        # Build context
        pains_text = "\n".join(
            f"- {p.get('title') or p.get('description', '')[:80]}" for p in pain_points[:6]
        )
        goals_text = "\n".join(
            f"- {g.get('title') or g.get('description', '')[:80]}" for g in goals[:6]
        )
        signals_text = "\n".join(
            f'- "{s.get("excerpt", "")[:200]}" (source: {s.get("source_type", "signal")})'
            for s in signal_excerpts[:5]
        )

        user_prompt = f"""Project Vision: {vision or 'Not yet defined'}

Pain Points:
{pains_text or 'None identified yet'}

Business Goals:
{goals_text or 'None identified yet'}

Signal Excerpts:
{signals_text or 'No signal evidence yet'}

Compose the narrative."""

        t0 = time.time()
        response = client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.3,
            tools=[NEED_NARRATIVE_TOOL],
            tool_choice={"type": "tool", "name": "submit_need_narrative"},
        )
        elapsed_ms = int((time.time() - t0) * 1000)

        # Parse response
        narrative = None
        anchors = []
        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and block.name == "submit_need_narrative":
                data = block.input
                if isinstance(data, str):
                    data = json.loads(data)
                narrative = data.get("narrative", "")
                anchors = data.get("anchors", [])
                break

        if not narrative:
            logger.warning(f"Need narrative generation returned empty for project {project_id}")
            return None

        # Format anchors
        formatted_anchors = [
            {
                "excerpt": a.get("excerpt", ""),
                "source_type": a.get("source_type", "signal"),
                "rationale": a.get("rationale", ""),
            }
            for a in anchors[:3]
        ]

        from datetime import datetime, timezone

        generated_at = datetime.now(timezone.utc).isoformat()

        result = {
            "text": narrative,
            "anchors": formatted_anchors,
            "generated_at": generated_at,
        }

        # Cache in synthesized_memory_cache
        try:
            db = get_supabase()
            payload = json.dumps({"need_narrative": result})
            # Update existing row or insert new
            existing = db.table("synthesized_memory_cache").select("id").eq(
                "project_id", project_id
            ).maybe_single().execute()
            if existing and existing.data:
                db.table("synthesized_memory_cache").update({
                    "content": payload,
                    "is_stale": False,
                    "synthesized_at": generated_at,
                    "updated_at": generated_at,
                }).eq("id", existing.data["id"]).execute()
            else:
                db.table("synthesized_memory_cache").insert({
                    "project_id": project_id,
                    "content": payload,
                    "is_stale": False,
                    "synthesized_at": generated_at,
                }).execute()
        except Exception:
            logger.warning(f"Failed to cache need narrative for project {project_id}")

        logger.info(
            f"Need narrative generated for project {project_id} "
            f"in {elapsed_ms}ms ({len(narrative)} chars)"
        )
        return result

    except Exception:
        logger.exception(f"Failed to compose need narrative for project {project_id}")
        return None


def get_cached_need_narrative(project_id: str) -> dict | None:
    """Retrieve cached need narrative from synthesized_memory_cache."""
    try:
        db = get_supabase()
        r = db.table("synthesized_memory_cache").select(
            "content"
        ).eq("project_id", project_id).maybe_single().execute()

        if r and r.data and r.data.get("content"):
            val = r.data["content"]
            if isinstance(val, str):
                val = json.loads(val)
            # Content wraps narrative under 'need_narrative' key
            if isinstance(val, dict) and "need_narrative" in val:
                return val["need_narrative"]
            return val
    except Exception:
        logger.debug(f"No cached need narrative for project {project_id}")
    return None
