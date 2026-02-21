"""Per-chunk Haiku meta-tagging for rich structured metadata.

Runs in parallel with embedding during document processing to generate
searchable tags: entities mentioned, topics, sentiment, decisions, speakers.

Tags are stored in each chunk's metadata JSONB under the `meta_tags` key.
The GIN index on signal_chunks.metadata covers these fields for fast queries.
"""

import asyncio
from typing import Any

from anthropic import AsyncAnthropic

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

META_TAG_TOOL = {
    "name": "submit_chunk_tags",
    "description": "Submit structured metadata tags for a document chunk.",
    "input_schema": {
        "type": "object",
        "properties": {
            "entities_mentioned": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Names of people, companies, products, or systems mentioned in this chunk.",
            },
            "entity_types_discussed": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "feature", "persona", "workflow", "constraint",
                        "stakeholder", "business_driver", "data_entity",
                        "competitor", "vp_step", "solution_flow_step",
                        "unlock", "prototype_feedback",
                    ],
                },
                "description": "Which BRD entity types are discussed in this chunk.",
            },
            "topics": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-5 snake_case topic slugs (e.g. 'payment_processing', 'user_onboarding').",
            },
            "sentiment": {
                "type": "string",
                "enum": ["positive", "negative", "neutral", "mixed"],
                "description": "Overall sentiment of this chunk.",
            },
            "decision_made": {
                "type": "boolean",
                "description": "True if this chunk contains an explicit decision or commitment.",
            },
            "speaker_roles": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": "Map of speaker name to their role/title if identifiable (e.g. {'Sarah': 'PM', 'John': 'CTO'}).",
            },
            "confidence_signals": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["definitive", "tentative", "speculative", "contradictory"],
                },
                "description": "How confident the statements in this chunk are.",
            },
            "temporal": {
                "type": "string",
                "enum": ["current_state", "future_plan", "past_reference", "mixed"],
                "description": "Whether the chunk discusses current state, future plans, or past events.",
            },
        },
        "required": ["entity_types_discussed", "topics", "sentiment", "decision_made", "temporal"],
    },
}

SYSTEM_PROMPT = (
    "You are a document analysis tagger. Given a chunk from a business/requirements document, "
    "extract structured metadata tags. Be precise — only tag what is explicitly present in the text. "
    "Use snake_case for topic slugs. Keep entities_mentioned to actual named entities, not generic terms."
)


async def meta_tag_single_chunk(
    chunk_content: str,
    chunk_index: int,
    section_title: str | None,
    document_type: str,
    client: AsyncAnthropic,
) -> dict[str, Any]:
    """Tag a single chunk with structured metadata via Haiku.

    Returns empty dict on failure (non-blocking).
    """
    section_context = f" (Section: {section_title})" if section_title else ""
    user_msg = (
        f"Document type: {document_type}\n"
        f"Chunk {chunk_index + 1}{section_context}:\n\n"
        f"{chunk_content[:3000]}"
    )

    for attempt in range(2):
        try:
            response = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                temperature=0.0,
                system=[{
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }],
                messages=[{"role": "user", "content": user_msg}],
                tools=[META_TAG_TOOL],
                tool_choice={"type": "tool", "name": "submit_chunk_tags"},
            )

            for block in response.content:
                if block.type == "tool_use" and block.name == "submit_chunk_tags":
                    return block.input

            return {}

        except Exception as e:
            if attempt == 0:
                logger.debug(f"Meta-tag retry for chunk {chunk_index}: {e}")
                await asyncio.sleep(1)
            else:
                logger.warning(f"Meta-tag failed for chunk {chunk_index}: {e}")
                return {}

    return {}


async def meta_tag_chunks_parallel(
    chunks: list[dict[str, Any]],
    document_type: str,
) -> list[dict[str, Any]]:
    """Tag all chunks in parallel via Haiku.

    Args:
        chunks: List of chunk dicts with 'content' and optionally 'section_path'
        document_type: Classification result (e.g. 'meeting_transcript', 'requirements_doc')

    Returns:
        List of tag dicts (same length as chunks). Empty dict for failed chunks.
    """
    if not chunks:
        return []

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    tasks = [
        meta_tag_single_chunk(
            chunk_content=chunk.get("content", chunk.get("original_content", "")),
            chunk_index=i,
            section_title=chunk.get("section_path"),
            document_type=document_type,
            client=client,
        )
        for i, chunk in enumerate(chunks)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    tags = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning(f"Meta-tag exception for chunk {i}: {result}")
            tags.append({})
        else:
            tags.append(result)

    logger.info(f"Meta-tagged {sum(1 for t in tags if t)} / {len(chunks)} chunks")
    return tags
