"""Haiku-powered knowledge type classification for gap clusters.

Sub-phase 6 of the Intelligence Loop. Single Haiku call classifies each
gap cluster into one of 4 knowledge types:
  - document: client likely has a doc/artifact
  - meeting: needs conversation to resolve
  - portal: resolvable via client portal input
  - tribal: held by specific people

~200ms. Follows generate_gap_intelligence.py pattern.
"""

import json
import time

from app.core.config import get_settings
from app.core.llm_usage import log_llm_usage
from app.core.logging import get_logger
from app.core.schemas_briefing import GapCluster, KnowledgeType

logger = get_logger(__name__)

HAIKU_MODEL = "claude-haiku-4-5-20251001"

CLASSIFY_SYSTEM = """You classify intelligence gap clusters by the most effective way to close them.

## Knowledge Types

- **document**: The client likely has a document, artifact, or file that contains the answer. Examples: rubrics, org charts, compliance checklists, process manuals, API specs.
- **meeting**: Needs a live conversation to resolve — the answer requires discussion, negotiation, or real-time exploration. Examples: workflow disagreements, priority debates, cross-team alignment.
- **portal**: Resolvable via structured async input — the client can answer through a form, checklist, or portal questionnaire. Examples: confirming entity details, selecting priorities, yes/no validations.
- **tribal**: The knowledge is held by specific people and isn't written down anywhere. Requires targeted 1:1 conversations with named individuals. Examples: legacy system knowledge, institutional history, political dynamics.

## Rules
- One type per cluster. Pick the MOST effective path.
- extraction_path = one sentence describing HOW to close the gap (e.g., "Request the compliance checklist from the legal team").
- Return valid JSON array only. No markdown fences."""

CLASSIFY_USER = """Classify these gap clusters:

{clusters_json}

Return ONLY a JSON array:
[
  {{
    "cluster_id": "...",
    "knowledge_type": "document|meeting|portal|tribal",
    "extraction_path": "One sentence: how to close this gap"
  }}
]"""


async def classify_gap_knowledge(
    clusters: list[GapCluster],
    project_id: str | None = None,
) -> None:
    """Classify knowledge types for gap clusters via Haiku.

    Mutates clusters in-place: sets knowledge_type and extraction_path.
    Falls back to MEETING on failure.
    """
    if not clusters:
        return

    from anthropic import AsyncAnthropic

    # Serialize clusters to compact JSON
    compact = []
    for c in clusters:
        gap_types = list({g.gap_type.value for g in c.gaps})
        entity_names = [g.entity_name for g in c.gaps[:5]]
        source_names = [s.name for s in c.sources[:3]]
        compact.append({
            "cluster_id": c.cluster_id,
            "theme": c.theme,
            "gap_types": gap_types,
            "entity_names": entity_names,
            "total_gaps": c.total_gaps,
            "sources": source_names,
        })

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    user_message = CLASSIFY_USER.format(clusters_json=json.dumps(compact, indent=2))

    try:
        start = time.time()
        response = await client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=512,
            temperature=0.2,
            system=[
                {
                    "type": "text",
                    "text": CLASSIFY_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
        )
        duration_ms = int((time.time() - start) * 1000)

        usage = response.usage
        cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_create = getattr(usage, "cache_creation_input_tokens", 0) or 0

        log_llm_usage(
            workflow="intelligence_loop",
            model=HAIKU_MODEL,
            provider="anthropic",
            tokens_input=usage.input_tokens,
            tokens_output=usage.output_tokens,
            duration_ms=duration_ms,
            chain="classify_gap_knowledge",
            project_id=project_id,
            tokens_cache_read=cache_read,
            tokens_cache_create=cache_create,
        )

        # Parse response
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        classifications = json.loads(text)
        if isinstance(classifications, str):
            # Anthropic string bug guard
            classifications = json.loads(classifications)

        # Apply to clusters
        class_map = {c["cluster_id"]: c for c in classifications}
        for cluster in clusters:
            cls = class_map.get(cluster.cluster_id)
            if cls:
                try:
                    cluster.knowledge_type = KnowledgeType(cls["knowledge_type"])
                except ValueError:
                    cluster.knowledge_type = KnowledgeType.MEETING
                cluster.extraction_path = cls.get("extraction_path", "")
            else:
                cluster.knowledge_type = KnowledgeType.MEETING

        logger.info(
            f"Knowledge classification: {len(classifications)} clusters "
            f"({duration_ms}ms)"
        )

    except Exception as e:
        logger.warning(f"Knowledge classification failed, defaulting to MEETING: {e}")
        for cluster in clusters:
            if not cluster.knowledge_type:
                cluster.knowledge_type = KnowledgeType.MEETING
