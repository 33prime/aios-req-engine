"""Document Agent for Discovery Prep.

Recommends 3 documents that would help understand project requirements.

Analyzes:
- Project state snapshot (including company/industry info)
- Business drivers (pains, goals, KPIs) that need evidence
- Knowledge gaps in features, personas, workflows
- Existing signals to avoid redundant requests

Recommends documents like:
- Current workflow documentation
- Integration/API requirements
- User role definitions
- Security/compliance requirements
- Sample data / Screenshots
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
Recommend exactly 3 documents that would ACCELERATE understanding of this project's requirements.
Focus on documents that fill knowledge gaps and provide evidence for business drivers.

## Document Selection Strategy

### By Industry Context
- **Healthcare/Fintech**: Compliance requirements, data handling policies, audit requirements
- **E-commerce/Retail**: Product catalog structure, order fulfillment workflow, inventory systems
- **SaaS/B2B**: User roles/permissions matrix, integration requirements, pricing tiers
- **Internal Tools**: Org chart, current process documentation, system architecture

### By Knowledge Gap
- **Missing workflows**: Request current process documentation or flowcharts
- **Unclear users**: Request user role definitions or persona research
- **Unknown integrations**: Request technical architecture or API documentation
- **Vague success metrics**: Request KPI dashboards or business reports

### GOOD Document Recommendations (specific, actionable):
- "Current order fulfillment process flowchart" (specific workflow)
- "User permission matrix showing roles and access levels" (specific format)
- "Screenshot of current dashboard showing key metrics" (visual + specific)

### BAD Document Recommendations (avoid these):
- "Requirements document" (too vague - what requirements?)
- "Project plan" (not about requirements)
- "All documentation" (not specific)

## Prioritization Guidelines
- **HIGH**: Blocks understanding of core requirements; we can't proceed well without it
- **MEDIUM**: Would significantly improve our understanding but not blocking
- **LOW**: Nice to have; would add context but not critical

## What NOT to Recommend
- Documents already provided (check existing signals)
- Documents the client likely can't share (competitor internals, confidential financials)
- Generic documents that won't help this specific project
- Marketing materials or sales decks

## Company/Industry Context
{industry_context}

## Project Context
{snapshot}

## Knowledge Gaps
{gaps}

## Existing Information (don't request these again)
{existing_context}

## Output Format
Output valid JSON only:
{{
  "documents": [
    {{
      "document_name": "Specific, descriptive document name",
      "priority": "high" | "medium" | "low",
      "why_important": "One sentence explaining what this document will help us understand"
    }}
  ],
  "reasoning": "Brief explanation of why you chose these documents and what gaps they fill"
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

    # Get industry context for targeted recommendations
    industry_context = await _get_industry_context(project_id)

    # Get knowledge gaps
    gaps = await _get_knowledge_gaps(project_id)

    # Get existing context to avoid redundant requests
    existing = await _get_existing_context(project_id)

    # Build prompt
    llm = get_llm(temperature=0.3)
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT.format(
                snapshot=snapshot,
                industry_context=industry_context,
                gaps=gaps,
                existing_context=existing,
            ),
        },
        {
            "role": "user",
            "content": "Recommend 3 specific documents that would help us understand this project's requirements better.",
        },
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


async def _get_industry_context(project_id: UUID) -> str:
    """Get industry and company context for targeted recommendations."""
    supabase = get_supabase()
    lines = []

    try:
        # Get company info
        company = (
            supabase.table("company_info")
            .select("name, industry, stage, size, company_type")
            .eq("project_id", str(project_id))
            .maybe_single()
            .execute()
        ).data

        if company:
            if company.get("industry"):
                lines.append(f"Industry: {company['industry']}")
            if company.get("company_type"):
                lines.append(f"Company Type: {company['company_type']}")
            if company.get("stage"):
                lines.append(f"Stage: {company['stage']}")
            if company.get("size"):
                lines.append(f"Size: {company['size']}")

    except Exception as e:
        logger.debug(f"Could not fetch company info: {e}")

    # Get project info
    try:
        project = (
            supabase.table("projects")
            .select("name, description, metadata")
            .eq("id", str(project_id))
            .single()
            .execute()
        ).data

        if project:
            meta = project.get("metadata") or {}
            if meta.get("industry") and "Industry:" not in "\n".join(lines):
                lines.append(f"Industry: {meta['industry']}")
            if meta.get("project_type"):
                lines.append(f"Project Type: {meta['project_type']}")

    except Exception as e:
        logger.debug(f"Could not fetch project info: {e}")

    if not lines:
        return "Industry context not specified - recommend general-purpose documents"

    return "\n".join(lines)


async def _get_knowledge_gaps(project_id: UUID) -> str:
    """Get knowledge gaps that documents could help fill."""
    supabase = get_supabase()
    gaps = []

    # Check business drivers - what's missing or unconfirmed?
    try:
        drivers = (
            supabase.table("business_drivers")
            .select("driver_type, description, status")
            .eq("project_id", str(project_id))
            .execute()
        ).data or []

        has_pains = any(d.get("driver_type") == "pain" for d in drivers)
        has_goals = any(d.get("driver_type") == "goal" for d in drivers)
        has_kpis = any(d.get("driver_type") == "kpi" for d in drivers)

        if not has_pains:
            gaps.append("[GAP] No pain points - could use current process documentation showing problems")
        if not has_goals:
            gaps.append("[GAP] No business goals - could use strategic planning docs or OKRs")
        if not has_kpis:
            gaps.append("[GAP] No success metrics - could use current KPI dashboards or reports")

    except Exception as e:
        logger.debug(f"Could not fetch business drivers: {e}")

    # Check constraints - any technical/compliance gaps?
    try:
        constraints = (
            supabase.table("constraints")
            .select("name, constraint_type")
            .eq("project_id", str(project_id))
            .execute()
        ).data or []

        has_technical = any(c.get("constraint_type") == "technical" for c in constraints)
        has_compliance = any(c.get("constraint_type") == "compliance" for c in constraints)
        has_integration = any(c.get("constraint_type") == "integration" for c in constraints)

        if not constraints:
            gaps.append("[GAP] No constraints identified - could use technical architecture docs")
        if not has_compliance:
            gaps.append("[GAP] No compliance constraints - may need security/compliance requirements if regulated")
        if not has_integration:
            gaps.append("[GAP] No integration requirements - could use system architecture or API docs")

    except Exception as e:
        logger.debug(f"Could not fetch constraints: {e}")

    # Check personas - do we understand users?
    try:
        personas = (
            supabase.table("personas")
            .select("name")
            .eq("project_id", str(project_id))
            .execute()
        ).data or []

        if not personas:
            gaps.append("[GAP] No personas - could use user research, org chart, or role definitions")

    except Exception as e:
        logger.debug(f"Could not fetch personas: {e}")

    # Check features - are there complex features that need more context?
    try:
        features = (
            supabase.table("features")
            .select("name, overview")
            .eq("project_id", str(project_id))
            .execute()
        ).data or []

        if not features:
            gaps.append("[GAP] No features defined - could use existing product screenshots or specs")

    except Exception as e:
        logger.debug(f"Could not fetch features: {e}")

    if not gaps:
        return "Project is well-defined. Recommend documents that provide deeper context or validation."

    return "\n".join(gaps)


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
            context_parts.append("Documents/Signals already provided (DON'T request these again):")
            for s in signals:
                signal_type = s.get("signal_type", "unknown")
                source_type = s.get("source_type", "")
                text_preview = (s.get("raw_text") or "")[:80].replace("\n", " ")
                line = f"- [{signal_type}]"
                if source_type:
                    line += f" ({source_type})"
                line += f" {text_preview}..."
                context_parts.append(line)
    except Exception as e:
        logger.debug(f"Could not fetch signals: {e}")

    # Check if we have workflow information already
    try:
        vp_steps = (
            supabase.table("vp_steps")
            .select("name")
            .eq("project_id", str(project_id))
            .execute()
        ).data or []

        if vp_steps:
            context_parts.append(f"\nValue path already has {len(vp_steps)} steps - workflow is partially understood")

    except Exception as e:
        logger.debug(f"Could not fetch vp_steps: {e}")

    if not context_parts:
        return "No existing documents or signals found - this is a new project, any relevant documents welcome."

    return "\n".join(context_parts)


def _get_fallback_documents() -> DocumentAgentOutput:
    """Return fallback document recommendations if generation fails."""
    return DocumentAgentOutput(
        documents=[
            DocRecommendationCreate(
                document_name="Current process flowchart or workflow documentation",
                priority=DocPriority.HIGH,
                why_important="Understanding how things work today helps us identify where we can add the most value.",
            ),
            DocRecommendationCreate(
                document_name="User roles and permissions matrix",
                priority=DocPriority.MEDIUM,
                why_important="Knowing who does what helps us design appropriate access controls and workflows.",
            ),
            DocRecommendationCreate(
                document_name="Screenshots of current tools or systems",
                priority=DocPriority.LOW,
                why_important="Visual context helps us understand the domain and current user experience.",
            ),
        ],
        reasoning="Fallback recommendations covering workflow understanding, user roles, and visual context.",
    )
