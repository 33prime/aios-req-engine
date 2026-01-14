"""Document Agent for Discovery Prep.

Recommends 3 documents that would help understand project requirements.

Analyzes:
- Project state snapshot
- Features and their descriptions
- PRD sections
- Identified gaps

Recommends documents like:
- Integration requirements
- User role definitions
- Security/compliance requirements
- Existing workflow documentation
"""

import json
from uuid import UUID

from app.core.llm import get_llm
from app.core.logging import get_logger
from app.core.schemas_discovery_prep import (
    DocPriority,
    DocRecommendation,
    DocRecommendationCreate,
    DocumentAgentOutput,
)
from app.core.state_snapshot import get_state_snapshot
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


SYSTEM_PROMPT = """You are an expert requirements analyst recommending documents for a discovery call.

## Your Goal
Recommend exactly 3 documents that would help understand this project's requirements.
Focus on documents that fill knowledge gaps and accelerate the discovery process.

## Document Types to Consider
- Integration/API requirements (if integrations mentioned)
- User role definitions / Org chart (if multiple user types)
- Security/compliance requirements (if regulated industry)
- Current workflow documentation (if replacing existing system)
- Business rules / Logic documentation (if complex domain)
- Sample data / Screenshots (if visual understanding needed)
- Technical architecture (if technical constraints exist)
- Competitive analysis (if market context needed)

## Prioritization
- HIGH: Critical for understanding core requirements, blocks progress without it
- MEDIUM: Would significantly help but not blocking
- LOW: Nice to have, provides additional context

## What NOT to recommend
- Don't ask for generic documents that won't help
- Don't recommend documents already provided (check existing signals)
- Don't recommend confidential documents client can't share

## Project Context
{snapshot}

## Existing Information
{existing_context}

## Output Format
Output valid JSON only:
{{
  "documents": [
    {{
      "document_name": "Descriptive name of document",
      "priority": "high" | "medium" | "low",
      "why_important": "Brief explanation of why this document would help"
    }}
  ],
  "reasoning": "Brief explanation of why you chose these documents"
}}"""


async def recommend_documents(project_id: UUID) -> DocumentAgentOutput:
    """
    Recommend 3 documents for a project.

    Args:
        project_id: The project UUID

    Returns:
        DocumentAgentOutput with documents and reasoning
    """
    # Get state snapshot
    snapshot = get_state_snapshot(project_id, force_refresh=True)

    # Get existing context
    existing = await _get_existing_context(project_id)

    # Build prompt
    llm = get_llm(temperature=0.3)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(snapshot=snapshot, existing_context=existing)},
        {"role": "user", "content": "Recommend 3 documents that would help with this project."},
    ]

    try:
        response = await llm.ainvoke(messages)
        content = response.content

        # Strip markdown code blocks if present
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first line (```json) and last line (```)
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        # Parse JSON
        data = json.loads(content)

        # Convert to output format
        documents = [
            DocRecommendationCreate(
                document_name=d["document_name"],
                priority=DocPriority(d.get("priority", "medium")),
                why_important=d.get("why_important", ""),
            )
            for d in data.get("documents", [])[:3]  # Cap at 3
        ]

        return DocumentAgentOutput(
            documents=documents,
            reasoning=data.get("reasoning", "Generated based on project context"),
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse document agent response: {e}")
        return _get_fallback_documents()
    except Exception as e:
        logger.error(f"Document agent error: {e}")
        return _get_fallback_documents()


async def _get_existing_context(project_id: UUID) -> str:
    """Get existing information to avoid redundant recommendations."""
    supabase = get_supabase()
    context_parts = []

    # Check existing signals (what documents have been provided)
    try:
        signals = (
            supabase.table("signals")
            .select("signal_type, source_type, raw_text")
            .eq("project_id", str(project_id))
            .limit(10)
            .execute()
        ).data or []

        if signals:
            context_parts.append("Documents/Signals already provided:")
            for s in signals:
                text_preview = (s.get("raw_text") or "")[:100]
                context_parts.append(f"- [{s.get('signal_type', 'unknown')}] {text_preview}...")
    except Exception as e:
        logger.debug(f"Could not fetch signals: {e}")

    # Check features for clues about what's known
    try:
        features = (
            supabase.table("features")
            .select("name, overview")
            .eq("project_id", str(project_id))
            .limit(10)
            .execute()
        ).data or []

        if features:
            context_parts.append("\nKnown features (don't need docs for these):")
            for f in features:
                context_parts.append(f"- {f['name']}")
    except Exception as e:
        logger.debug(f"Could not fetch features: {e}")

    # Check PRD sections for what's documented
    try:
        prd = (
            supabase.table("prd_sections")
            .select("slug, label")
            .eq("project_id", str(project_id))
            .limit(10)
            .execute()
        ).data or []

        if prd:
            context_parts.append("\nPRD sections (partially documented):")
            for p in prd:
                context_parts.append(f"- {p.get('label', p['slug'])}")
    except Exception as e:
        logger.debug(f"Could not fetch PRD sections: {e}")

    if not context_parts:
        return "No existing documents or signals found. This is a new project."

    return "\n".join(context_parts)


def _get_fallback_documents() -> DocumentAgentOutput:
    """Return fallback document recommendations if generation fails."""
    return DocumentAgentOutput(
        documents=[
            DocRecommendationCreate(
                document_name="Current Workflow Documentation",
                priority=DocPriority.HIGH,
                why_important="Understanding the current process helps us identify pain points and design improvements.",
            ),
            DocRecommendationCreate(
                document_name="User Role Definitions",
                priority=DocPriority.MEDIUM,
                why_important="Knowing who uses the system and their responsibilities helps us design the right permissions and workflows.",
            ),
            DocRecommendationCreate(
                document_name="Sample Data or Screenshots",
                priority=DocPriority.LOW,
                why_important="Visual examples help us understand the domain and existing data structures.",
            ),
        ],
        reasoning="Fallback recommendations covering workflow, users, and visual context.",
    )
