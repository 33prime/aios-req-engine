"""Fast path router for chat — handles instant responses without LLM calls.

Patterns:
- Acknowledgements → canned response
- Simple create commands → direct tool execution
- Card button commands → structured command parsing

Post-creation cascade:
- fire_fast_path_cascades() runs embedding + linking after direct entity insert.
  This closes the intelligence gap where fast-path entities bypass the pipeline.
"""

import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FastPathResult:
    """Result from fast path routing — bypasses LLM entirely."""

    text: str
    tool_calls: list[dict] | None = None
    cards: list[dict] | None = None


# ── Acknowledgement Pattern ───────────────────────────────────────

_ACK_PATTERN = re.compile(
    r"^(thanks|thank you|ok|okay|got it|yes|no|sure|perfect"
    r"|great|cool|do it|sounds good|👍)\.?!?\s*$",
    re.I,
)

_ACK_RESPONSES = [
    "You got it!",
    "Got it!",
    "Sure thing!",
    "Done!",
    "Understood!",
]

# ── Simple Create Pattern ─────────────────────────────────────────

_SIMPLE_CREATE = re.compile(
    r'^(?:add|create)\s+(?:a\s+)?'
    r'(feature|persona|constraint|stakeholder|business_driver|workflow)\s+'
    r'(?:called|named)\s+"?(.+?)"?\s*$',
    re.I,
)

# Entity type normalization
_ENTITY_TYPE_MAP = {
    "feature": "feature",
    "persona": "persona",
    "constraint": "constraint",
    "stakeholder": "stakeholder",
    "business_driver": "business_driver",
    "workflow": "workflow",
}


async def try_fast_path(
    message: str,
    page_context: str | None,
    project_id: Any,
) -> FastPathResult | None:
    """Try to handle message via fast path. Returns None if no match.

    Fast path bypasses: context assembly, retrieval, prompt compilation, LLM call.
    """
    stripped = message.strip()

    # 1. Acknowledgements
    if _ACK_PATTERN.match(stripped):
        # Rotate response based on message hash for variety
        idx = hash(stripped.lower()) % len(_ACK_RESPONSES)
        return FastPathResult(text=_ACK_RESPONSES[idx])

    # 2. Simple create commands
    create_match = _SIMPLE_CREATE.match(stripped)
    if create_match:
        entity_type = _ENTITY_TYPE_MAP.get(create_match.group(1).lower())
        entity_name = create_match.group(2).strip().strip('"\'')
        if entity_type and entity_name:
            # Build the tool call for write.create
            name_field = "description" if entity_type == "business_driver" else "name"
            tool_call = {
                "tool_name": "write",
                "tool_input": {
                    "action": "create",
                    "entity_type": entity_type,
                    "data": {name_field: entity_name},
                },
            }
            label = entity_type.replace("_", " ")
            return FastPathResult(
                text=f'Created {label}: "{entity_name}"',
                tool_calls=[tool_call],
                cards=[{
                    "type": "proposal",
                    "data": {
                        "title": f"New {label}",
                        "body": (
                            f'"{entity_name}" has been added. '
                            "You can enrich it with more details."
                        ),
                        "actions": [{
                            "label": "View details",
                            "action": "navigate",
                            "entity_type": entity_type,
                        }],
                    },
                }],
            )

    return None


async def fire_fast_path_cascades(
    project_id: str | UUID,
    entity_type: str,
    entity_id: str,
) -> None:
    """Fire post-creation cascades for fast-path entities.

    Fast-path entities bypass the signal pipeline, so they miss:
    - Embedding (multi-vector)
    - Co-occurrence linking
    - Semantic link resolution
    - Cache invalidation

    Call this AFTER the tool execution returns the entity_id.
    All operations are fire-and-forget — errors are logged, never raised.
    """
    from app.db.entity_embeddings import ENTITY_TABLE_MAP

    pid = UUID(str(project_id))
    table = ENTITY_TABLE_MAP.get(entity_type)
    if not table:
        return

    try:
        from app.db.supabase_client import get_supabase

        sb = get_supabase()
        response = sb.table(table).select("*").eq("id", entity_id).single().execute()
        if not response.data:
            return
        entity_data = response.data

        # 1. Multi-vector embedding (fire-and-forget)
        try:
            from app.db.entity_embeddings import embed_entity_multivector

            enrichment = entity_data.get("enrichment_intel") or {}
            await embed_entity_multivector(
                entity_type=entity_type,
                entity_id=UUID(entity_id),
                entity_data=entity_data,
                project_id=pid,
                enrichment=enrichment,
            )
        except Exception:
            logger.debug(f"Fast-path embedding failed for {entity_type}/{entity_id}", exc_info=True)

        # 2. Co-occurrence linking (fire-and-forget)
        try:
            from app.db.patch_applicator import _link_entities_by_cooccurrence

            _link_entities_by_cooccurrence(pid, [{
                "entity_type": entity_type,
                "entity_id": entity_id,
                "operation": "create",
                "name": entity_data.get("name") or entity_data.get("title") or "",
            }])
        except Exception:
            logger.debug(f"Fast-path co-occurrence linking failed for {entity_type}/{entity_id}", exc_info=True)

        # 3. Cache invalidation
        try:
            from app.context.project_awareness import invalidate_awareness_cache

            invalidate_awareness_cache(str(pid))
        except Exception:
            pass

        logger.debug(f"Fast-path cascades fired for {entity_type}/{entity_id}")

    except Exception:
        logger.debug(f"Fast-path cascades failed for {entity_type}/{entity_id}", exc_info=True)
