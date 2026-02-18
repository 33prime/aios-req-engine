"""Prototype review signal extractor.

Loads session verdicts + feedback + chat → dual output:
  - entity_patches[] (BRD updates from review findings)
  - code_change_requirements[] (prototype pipeline updates)

Usage:
    from app.chains.extract_prototype_review import extract_prototype_review

    result = await extract_prototype_review(session_id, project_id)
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.schemas_entity_patch import EntityPatch, EntityPatchList

logger = logging.getLogger(__name__)


class CodeChangeRequirement(BaseModel):
    """A code change required based on prototype review feedback."""

    feature_name: str
    change_type: str  # "fix", "add", "remove", "redesign"
    description: str
    priority: str = "medium"
    source_feedback_ids: list[str] = Field(default_factory=list)


class PrototypeReviewResult(BaseModel):
    """Combined extraction result from a prototype review session."""

    entity_patches: EntityPatchList = Field(default_factory=EntityPatchList)
    code_changes: list[CodeChangeRequirement] = Field(default_factory=list)
    session_summary: str = ""


async def extract_prototype_review(
    session_id: UUID,
    project_id: UUID,
) -> PrototypeReviewResult:
    """Extract BRD patches and code change requirements from a prototype session.

    Loads session verdicts, feedback, and overlay data, then uses Haiku
    to produce structured patches.

    Args:
        session_id: Prototype session UUID
        project_id: Project UUID

    Returns:
        PrototypeReviewResult with entity_patches and code_changes
    """
    # Load session data
    try:
        session_data = _load_session_data(session_id)
    except Exception as e:
        logger.error(f"Failed to load session data: {e}")
        return PrototypeReviewResult()

    if not session_data.get("feedback") and not session_data.get("verdicts"):
        return PrototypeReviewResult()

    # Build context text
    context_text = _build_review_context(session_data)

    # Call LLM for extraction
    try:
        raw_output = await _call_review_extraction_llm(context_text)
        return _parse_review_output(raw_output, session_id)
    except Exception as e:
        logger.warning(f"Prototype review extraction failed: {e}")
        return PrototypeReviewResult()


def _load_session_data(session_id: UUID) -> dict[str, Any]:
    """Load all review data for a session."""
    from app.db.supabase_client import get_supabase

    sb = get_supabase()

    # Load session
    session = (
        sb.table("prototype_sessions")
        .select("*")
        .eq("id", str(session_id))
        .single()
        .execute()
    ).data

    if not session:
        return {}

    prototype_id = session.get("prototype_id")

    # Load feedback for this session
    feedback = (
        sb.table("prototype_feedback")
        .select("id, source, content, feedback_type, priority, feature_id, affects_features")
        .eq("session_id", str(session_id))
        .execute()
    ).data or []

    # Load verdicts from overlays
    verdicts = []
    if prototype_id:
        overlays = (
            sb.table("prototype_feature_overlays")
            .select("id, handoff_feature_name, feature_id, consultant_verdict, consultant_notes, client_verdict, client_notes, status, confidence")
            .eq("prototype_id", str(prototype_id))
            .execute()
        ).data or []

        for overlay in overlays:
            if overlay.get("consultant_verdict") or overlay.get("client_verdict"):
                verdicts.append(overlay)

    return {
        "session": session,
        "feedback": feedback,
        "verdicts": verdicts,
    }


def _build_review_context(session_data: dict) -> str:
    """Build text context from session data for LLM."""
    lines = []

    # Verdicts
    verdicts = session_data.get("verdicts", [])
    if verdicts:
        lines.append("## Feature Verdicts")
        for v in verdicts:
            name = v.get("handoff_feature_name", "Unknown Feature")
            consultant = v.get("consultant_verdict", "-")
            client = v.get("client_verdict", "-")
            lines.append(f"- {name}: consultant={consultant}, client={client}")
            if v.get("consultant_notes"):
                lines.append(f"  Notes: {v['consultant_notes']}")
            if v.get("client_notes"):
                lines.append(f"  Client notes: {v['client_notes']}")

    # Feedback
    feedback = session_data.get("feedback", [])
    if feedback:
        lines.append("\n## Session Feedback")
        for f in feedback:
            source = f.get("source", "unknown")
            ftype = f.get("feedback_type", "observation")
            priority = f.get("priority", "medium")
            content = f.get("content", "")
            lines.append(f"- [{source}/{ftype}/{priority}] {content}")

    return "\n".join(lines) if lines else ""


async def _call_review_extraction_llm(context_text: str) -> str:
    """Call Haiku for prototype review extraction."""
    from anthropic import AsyncAnthropic
    from app.core.config import Settings

    settings = Settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    system_prompt = """You are extracting structured updates from a prototype review session.

Output a JSON object with two arrays:

```json
{
  "entity_patches": [
    {
      "operation": "create|merge|update|stale",
      "entity_type": "feature|persona|constraint|business_driver",
      "target_entity_id": "id or null",
      "payload": {},
      "confidence": "high|medium",
      "source_authority": "prototype"
    }
  ],
  "code_changes": [
    {
      "feature_name": "Feature Name",
      "change_type": "fix|add|remove|redesign",
      "description": "What needs to change",
      "priority": "high|medium|low"
    }
  ],
  "session_summary": "One-sentence summary"
}
```

Rules:
- Verdicts of "aligned" → merge with supporting evidence
- Verdicts of "needs_adjustment" → update with specific changes
- Verdicts of "off_track" → stale the feature or create constraint
- Client feedback with type "requirement" → create/merge features
- Client feedback with type "concern" → create constraints
- All patches have source_authority: "prototype"
- Code changes describe what the prototype code needs
- Be conservative — only extract clearly stated requirements"""

    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=3000,
        system=system_prompt,
        messages=[{"role": "user", "content": f"{context_text}\n\nExtract patches and code changes. Return JSON only."}],
        temperature=0.0,
    )

    return response.content[0].text


def _parse_review_output(raw_output: str, session_id: UUID) -> PrototypeReviewResult:
    """Parse LLM output into PrototypeReviewResult."""
    text = raw_output.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse prototype review JSON")
        return PrototypeReviewResult()

    if not isinstance(data, dict):
        return PrototypeReviewResult()

    # Parse entity patches
    patches = []
    for item in data.get("entity_patches", []):
        try:
            if not item.get("source_authority"):
                item["source_authority"] = "prototype"
            patches.append(EntityPatch(**item))
        except Exception as e:
            logger.debug(f"Skipped invalid review patch: {e}")

    # Parse code changes
    code_changes = []
    for item in data.get("code_changes", []):
        try:
            code_changes.append(CodeChangeRequirement(**item))
        except Exception as e:
            logger.debug(f"Skipped invalid code change: {e}")

    return PrototypeReviewResult(
        entity_patches=EntityPatchList(
            patches=patches,
            extraction_model="claude-haiku-4-5-20251001",
        ),
        code_changes=code_changes,
        session_summary=data.get("session_summary", ""),
    )
