"""API endpoints for evidence quality tracking."""

from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.chains.analyze_gaps import analyze_gaps
from app.agents.stakeholder_suggester import suggest_stakeholders
from app.core.logging import get_logger
from app.db.evidence import get_evidence_quality
from app.db.stakeholders import list_stakeholders

logger = get_logger(__name__)

router = APIRouter()


class ConfirmationStatusCount(BaseModel):
    """Count and percentage for a confirmation status."""

    count: int
    percentage: int


class EvidenceBreakdown(BaseModel):
    """Breakdown by confirmation status."""

    confirmed_client: ConfirmationStatusCount
    confirmed_consultant: ConfirmationStatusCount
    needs_client: ConfirmationStatusCount
    ai_generated: ConfirmationStatusCount


class EntityTypeBreakdown(BaseModel):
    """Counts by confirmation status for a single entity type."""

    confirmed_client: int = 0
    confirmed_consultant: int = 0
    needs_client: int = 0
    ai_generated: int = 0


class EvidenceQualityResponse(BaseModel):
    """Response for evidence quality endpoint."""

    breakdown: EvidenceBreakdown
    by_entity_type: dict[str, EntityTypeBreakdown]
    total_entities: int
    strong_evidence_percentage: int
    summary: str


@router.get("/projects/{project_id}/evidence/quality")
async def get_project_evidence_quality(project_id: UUID) -> EvidenceQualityResponse:
    """
    Get evidence quality breakdown for a project.

    Returns:
    - Breakdown by confirmation status (client, consultant, needs_client, ai_generated)
    - Percentage with strong evidence (client + consultant confirmed)
    - Entity counts per tier
    - Human-readable summary

    Strong evidence is defined as entities confirmed by either client or consultant.

    Args:
        project_id: Project UUID

    Returns:
        EvidenceQualityResponse with quality metrics

    Raises:
        HTTPException 500: If database error
    """
    try:
        result = get_evidence_quality(project_id)

        # Transform breakdown
        breakdown_raw = result["breakdown"]
        breakdown = EvidenceBreakdown(
            confirmed_client=ConfirmationStatusCount(**breakdown_raw.get("confirmed_client", {"count": 0, "percentage": 0})),
            confirmed_consultant=ConfirmationStatusCount(**breakdown_raw.get("confirmed_consultant", {"count": 0, "percentage": 0})),
            needs_client=ConfirmationStatusCount(**breakdown_raw.get("needs_client", {"count": 0, "percentage": 0})),
            ai_generated=ConfirmationStatusCount(**breakdown_raw.get("ai_generated", {"count": 0, "percentage": 0})),
        )

        # Transform by_entity_type
        by_entity_type = {}
        for entity_type, counts in result.get("by_entity_type", {}).items():
            by_entity_type[entity_type] = EntityTypeBreakdown(**counts)

        logger.info(
            f"Retrieved evidence quality for project {project_id}",
            extra={
                "project_id": str(project_id),
                "total_entities": result["total_entities"],
                "strong_percentage": result["strong_evidence_percentage"],
            },
        )

        return EvidenceQualityResponse(
            breakdown=breakdown,
            by_entity_type=by_entity_type,
            total_entities=result["total_entities"],
            strong_evidence_percentage=result["strong_evidence_percentage"],
            summary=result["summary"],
        )

    except Exception as e:
        logger.exception(f"Failed to get evidence quality for project {project_id}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve evidence quality",
        ) from e


# =============================================================================
# Requirements Intelligence — Models
# =============================================================================


class InformationGap(BaseModel):
    id: str
    gap_type: str
    severity: str
    title: str
    description: str
    how_to_fix: str


class SuggestedSource(BaseModel):
    source_type: str
    title: str
    description: str
    why_valuable: str
    likely_owner_role: str
    priority: str
    related_gaps: list[str]


class StakeholderIntel(BaseModel):
    stakeholder_id: str | None = None
    name: str | None = None
    role: str
    organization: str | None = None
    stakeholder_type: str | None = None
    influence_level: str | None = None
    is_known: bool
    is_primary_contact: bool = False
    likely_knowledge: list[str] = []
    domain_expertise: list[str] = []
    concerns: list[str] = []
    priorities: list[str] = []
    engagement_tip: str | None = None


class TribalKnowledgeItem(BaseModel):
    title: str
    description: str
    why_undocumented: str
    best_asked_of: str
    conversation_starters: list[str]
    related_gaps: list[str]


class IntelligenceCounts(BaseModel):
    gaps: int
    sources: int
    stakeholders_known: int
    stakeholders_suggested: int
    tribal: int


class RequirementsIntelligenceResponse(BaseModel):
    summary: str
    phase: str
    total_readiness: float
    information_gaps: list[InformationGap]
    suggested_sources: list[SuggestedSource]
    stakeholder_intelligence: list[StakeholderIntel]
    tribal_knowledge: list[TribalKnowledgeItem]
    counts: IntelligenceCounts


# =============================================================================
# Deterministic Mapping Tables
# =============================================================================

GATE_SOURCE_MAP: dict[str, list[dict]] = {
    "core_pain": [
        {
            "source_type": "data_export",
            "title": "Customer Support Logs",
            "description": "Tickets showing recurring user frustrations",
            "why_valuable": "Reveals real pain points with frequency data — the system can extract features from these",
            "likely_owner_role": "Support Manager",
            "priority": "high",
        },
        {
            "source_type": "recording",
            "title": "User Interview Recordings",
            "description": "Audio or video of interviews with end users",
            "why_valuable": "First-hand accounts of pain points in users' own words",
            "likely_owner_role": "UX Researcher",
            "priority": "high",
        },
        {
            "source_type": "data_export",
            "title": "Complaint Tracking Spreadsheet",
            "description": "Internal tracking of client complaints or issues",
            "why_valuable": "Shows the most common and severe problems with quantifiable data",
            "likely_owner_role": "Customer Success Lead",
            "priority": "medium",
        },
    ],
    "primary_persona": [
        {
            "source_type": "document",
            "title": "User Segmentation Report",
            "description": "Report describing user segments and their behaviors",
            "why_valuable": "Defines who the users actually are — the system can map segments to personas",
            "likely_owner_role": "Marketing Lead",
            "priority": "high",
        },
        {
            "source_type": "data_export",
            "title": "CRM Data Export",
            "description": "Customer records with roles, company sizes, and usage patterns",
            "why_valuable": "Hard data on who uses the product and how",
            "likely_owner_role": "Sales Operations",
            "priority": "medium",
        },
        {
            "source_type": "document",
            "title": "Employee Directory with Roles",
            "description": "Internal org chart or role descriptions",
            "why_valuable": "Identifies internal stakeholder types and their relationships",
            "likely_owner_role": "HR / Operations",
            "priority": "low",
        },
    ],
    "wow_moment": [
        {
            "source_type": "recording",
            "title": "Competitor Demo Recordings",
            "description": "Recordings of competitor product demonstrations",
            "why_valuable": "Shows what users find impressive — helps define the aspirational experience",
            "likely_owner_role": "Product Manager",
            "priority": "medium",
        },
        {
            "source_type": "data_export",
            "title": "Customer Wish-list Feedback",
            "description": "Feature requests and wish-list items from customers",
            "why_valuable": "Reveals what users dream about — the gap between current and desired experience",
            "likely_owner_role": "Product Manager",
            "priority": "high",
        },
        {
            "source_type": "document",
            "title": "Product Vision Document",
            "description": "Strategic vision for the product's future",
            "why_valuable": "Captures the intended emotional and functional experience",
            "likely_owner_role": "Product Owner",
            "priority": "medium",
        },
    ],
    "design_preferences": [
        {
            "source_type": "document",
            "title": "Existing Brand Guidelines",
            "description": "Brand style guide with colors, fonts, and visual language",
            "why_valuable": "Ensures design alignment with existing brand identity",
            "likely_owner_role": "Brand Manager",
            "priority": "high",
        },
        {
            "source_type": "artifact",
            "title": "Current UI Screenshots",
            "description": "Screenshots of existing product or competitor UIs",
            "why_valuable": "Shows current design language and expected patterns",
            "likely_owner_role": "Design Lead",
            "priority": "medium",
        },
        {
            "source_type": "document",
            "title": "Style Guide or Design System",
            "description": "Component library or design system documentation",
            "why_valuable": "Defines reusable patterns and design constraints",
            "likely_owner_role": "Design Lead",
            "priority": "medium",
        },
    ],
    "business_case": [
        {
            "source_type": "document",
            "title": "Business Case Template",
            "description": "Internal template or completed business case",
            "why_valuable": "Shows how the organization justifies investment — critical for alignment",
            "likely_owner_role": "Project Sponsor",
            "priority": "high",
        },
        {
            "source_type": "document",
            "title": "ROI Analysis Document",
            "description": "Return on investment calculations or projections",
            "why_valuable": "Quantifies expected value — anchors prioritization decisions",
            "likely_owner_role": "Finance / Business Analyst",
            "priority": "high",
        },
        {
            "source_type": "document",
            "title": "Strategic Plan",
            "description": "Company or department strategic plan",
            "why_valuable": "Shows how this project fits into broader organizational goals",
            "likely_owner_role": "Executive Sponsor",
            "priority": "medium",
        },
    ],
    "budget_constraints": [
        {
            "source_type": "document",
            "title": "Budget Approval Documents",
            "description": "Budget allocation or approval paperwork",
            "why_valuable": "Defines the real financial boundaries for the project",
            "likely_owner_role": "Finance Manager",
            "priority": "high",
        },
        {
            "source_type": "document",
            "title": "Procurement Guidelines",
            "description": "Internal procurement process and vendor requirements",
            "why_valuable": "Reveals hidden constraints around vendor selection and contracting",
            "likely_owner_role": "Procurement Lead",
            "priority": "medium",
        },
        {
            "source_type": "document",
            "title": "Previous Project Budgets",
            "description": "Budget breakdowns from similar past projects",
            "why_valuable": "Provides realistic benchmarks for cost estimation",
            "likely_owner_role": "PMO / Project Manager",
            "priority": "low",
        },
    ],
    "full_requirements": [
        {
            "source_type": "document",
            "title": "Legacy System Documentation",
            "description": "Technical docs for systems being replaced or integrated with",
            "why_valuable": "Reveals integration constraints and migration requirements",
            "likely_owner_role": "Technical Lead",
            "priority": "high",
        },
        {
            "source_type": "artifact",
            "title": "Process Flow Diagrams",
            "description": "Current business process flows and workflows",
            "why_valuable": "Maps how work actually gets done — critical for requirements completeness",
            "likely_owner_role": "Business Analyst",
            "priority": "high",
        },
        {
            "source_type": "document",
            "title": "Integration Specifications",
            "description": "API docs, data formats, or integration requirements",
            "why_valuable": "Defines technical boundaries and compatibility requirements",
            "likely_owner_role": "Solutions Architect",
            "priority": "medium",
        },
    ],
}

TRIBAL_KNOWLEDGE_MAP: dict[str, list[dict]] = {
    "core_pain": [
        {
            "title": "Why Past Solutions Failed",
            "description": "Understanding of previous attempts to solve this problem and why they didn't work",
            "why_undocumented": "Organizational history and politics around failed initiatives rarely make it into documents",
            "best_asked_of": "Long-tenured team lead or department head",
            "conversation_starters": [
                "Have you tried solving this problem before? What happened?",
                "What's the history behind the current process?",
            ],
        },
    ],
    "primary_persona": [
        {
            "title": "The Real Decision-Making Chain",
            "description": "Who actually makes decisions vs. who is formally responsible",
            "why_undocumented": "Informal power structures and influence networks exist outside org charts",
            "best_asked_of": "Senior project manager or executive assistant",
            "conversation_starters": [
                "When a decision needs to be made, who do people actually go to?",
                "Who are the unofficial influencers on this team?",
            ],
        },
    ],
    "wow_moment": [
        {
            "title": "What Competitors Promised But Couldn't Deliver",
            "description": "Intelligence about competitor weaknesses and failed promises",
            "why_undocumented": "Competitive intelligence from sales cycles is shared verbally, not written down",
            "best_asked_of": "Sales lead or account manager",
            "conversation_starters": [
                "What do competitors promise that they can't actually deliver?",
                "Where do users get most frustrated with alternative solutions?",
            ],
        },
    ],
    "business_case": [
        {
            "title": "Unwritten Budget Rules",
            "description": "How budget approvals actually work vs. the official process",
            "why_undocumented": "Internal politics and budget allocation norms are cultural knowledge",
            "best_asked_of": "Finance contact or experienced project sponsor",
            "conversation_starters": [
                "What's the real process for getting budget approved here?",
                "Are there timing considerations for budget requests?",
            ],
        },
    ],
    "budget_constraints": [
        {
            "title": "Unwritten Budget Rules",
            "description": "How budget approvals actually work vs. the official process",
            "why_undocumented": "Internal politics and budget allocation norms are cultural knowledge",
            "best_asked_of": "Finance contact or experienced project sponsor",
            "conversation_starters": [
                "What's the real process for getting budget approved here?",
                "Are there funding windows or cycles we should be aware of?",
            ],
        },
    ],
    "full_requirements": [
        {
            "title": "Workarounds Nobody Talks About",
            "description": "Shadow IT and manual processes that bypass official systems",
            "why_undocumented": "People don't document their workarounds — they just do them",
            "best_asked_of": "Frontline staff or operations team",
            "conversation_starters": [
                "What do you do when the system doesn't do what you need?",
                "Are there any spreadsheets or tools you use outside the main system?",
            ],
        },
    ],
}

# Generic tribal knowledge items included for all projects
GENERIC_TRIBAL_KNOWLEDGE: list[dict] = [
    {
        "title": "Political Dynamics",
        "description": "Who supports or blocks change in the organization",
        "why_undocumented": "Political relationships and alliances are never written down",
        "best_asked_of": "Trusted internal champion or long-tenured employee",
        "conversation_starters": [
            "Who are the biggest advocates for this project internally?",
            "Is there anyone who might be concerned about this initiative?",
        ],
        "related_gaps": [],
    },
    {
        "title": "Historical Context",
        "description": "Why things are the way they are — the organizational history behind current processes",
        "why_undocumented": "Institutional memory lives in people, not documents",
        "best_asked_of": "Long-tenured team member or department head",
        "conversation_starters": [
            "How did the current process come to be?",
            "What's changed in the last few years that led to this need?",
        ],
        "related_gaps": [],
    },
]

GATE_TOPIC_MAP: dict[str, list[str]] = {
    "core_pain": ["support", "users", "customer", "process"],
    "primary_persona": ["users", "customer", "hr", "data"],
    "wow_moment": ["design", "ux", "features", "roadmap"],
    "design_preferences": ["design", "brand", "ux"],
    "business_case": ["budget", "roi", "strategy", "business goals"],
    "budget_constraints": ["budget", "financial", "contracts"],
    "full_requirements": ["requirements", "technical", "integration", "process"],
}


# =============================================================================
# Requirements Intelligence — Helpers
# =============================================================================


def _extract_gap_topics(priority_gaps: list[dict]) -> list[str]:
    """Extract topic keywords from gaps for stakeholder suggestion."""
    topics: list[str] = []
    for gap in priority_gaps:
        gate = gap.get("gate")
        if gate and gate in GATE_TOPIC_MAP:
            topics.extend(GATE_TOPIC_MAP[gate])
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for t in topics:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique


def _build_information_gaps(priority_gaps: list[dict]) -> list[InformationGap]:
    """Convert raw priority gaps to InformationGap models."""
    result: list[InformationGap] = []
    for gap in priority_gaps:
        gate = gap.get("gate", "")
        gap_type = gap.get("type", "evidence")
        gap_id = f"{gap_type}:{gate}" if gate else f"{gap_type}:{len(result)}"
        title = gate.replace("_", " ").title() if gate else gap.get("description", "Gap")[:50]
        result.append(
            InformationGap(
                id=gap_id,
                gap_type=gap_type,
                severity=gap.get("severity", "medium"),
                title=title,
                description=gap.get("description", ""),
                how_to_fix=gap.get("how_to_fix", ""),
            )
        )
    return result


def _build_suggested_sources(gap_result: dict) -> list[SuggestedSource]:
    """Build suggested sources from deterministic mapping of gap gates."""
    sources: list[SuggestedSource] = []
    seen_titles: set[str] = set()

    for gap in gap_result.get("priority_gaps", []):
        gate = gap.get("gate")
        if not gate or gate not in GATE_SOURCE_MAP:
            continue
        gap_id = f"{gap.get('type', 'foundation')}:{gate}"
        for src in GATE_SOURCE_MAP[gate]:
            if src["title"] in seen_titles:
                continue
            seen_titles.add(src["title"])
            sources.append(
                SuggestedSource(
                    source_type=src["source_type"],
                    title=src["title"],
                    description=src["description"],
                    why_valuable=src["why_valuable"],
                    likely_owner_role=src["likely_owner_role"],
                    priority=src["priority"],
                    related_gaps=[gap_id],
                )
            )
    return sources


def _build_tribal_knowledge(gap_result: dict) -> list[TribalKnowledgeItem]:
    """Build tribal knowledge items from deterministic mapping of gap gates."""
    items: list[TribalKnowledgeItem] = []
    seen_titles: set[str] = set()

    for gap in gap_result.get("priority_gaps", []):
        gate = gap.get("gate")
        if not gate or gate not in TRIBAL_KNOWLEDGE_MAP:
            continue
        gap_id = f"{gap.get('type', 'foundation')}:{gate}"
        for tk in TRIBAL_KNOWLEDGE_MAP[gate]:
            if tk["title"] in seen_titles:
                continue
            seen_titles.add(tk["title"])
            items.append(
                TribalKnowledgeItem(
                    title=tk["title"],
                    description=tk["description"],
                    why_undocumented=tk["why_undocumented"],
                    best_asked_of=tk["best_asked_of"],
                    conversation_starters=tk["conversation_starters"],
                    related_gaps=[gap_id],
                )
            )

    # Add generic tribal knowledge
    for tk in GENERIC_TRIBAL_KNOWLEDGE:
        if tk["title"] not in seen_titles:
            items.append(TribalKnowledgeItem(**tk))

    return items


def _build_stakeholder_intelligence(
    known_stakeholders: list[dict],
    suggestions: list,
    priority_gaps: list[dict],
) -> list[StakeholderIntel]:
    """Merge known stakeholders + suggestions into intelligence list."""
    result: list[StakeholderIntel] = []

    # Known stakeholders first
    for s in known_stakeholders:
        result.append(
            StakeholderIntel(
                stakeholder_id=str(s.get("id", "")),
                name=s.get("name"),
                role=s.get("role") or "Unknown",
                organization=s.get("organization"),
                stakeholder_type=s.get("stakeholder_type"),
                influence_level=s.get("influence_level"),
                is_known=True,
                is_primary_contact=s.get("is_primary_contact", False),
                likely_knowledge=s.get("expertise_areas", []) or [],
                domain_expertise=s.get("domain_expertise", []) or [],
                concerns=s.get("concerns", []) or [],
                priorities=s.get("priorities", []) or [],
                engagement_tip=s.get("engagement_notes"),
            )
        )

    # Suggested stakeholders
    seen_roles: set[str] = set()
    for s in suggestions:
        role = (s.role if hasattr(s, "role") else s.get("role")) or "Unknown"
        if role in seen_roles:
            continue
        seen_roles.add(role)

        # If matched to existing, skip (already in known list)
        is_matched = s.is_matched if hasattr(s, "is_matched") else s.get("is_matched", False)
        if is_matched:
            continue

        name = s.name if hasattr(s, "name") else s.get("name")
        sid = s.stakeholder_id if hasattr(s, "stakeholder_id") else s.get("stakeholder_id")
        topic = s.topic if hasattr(s, "topic") else s.get("topic", "")
        reason = s.reason if hasattr(s, "reason") else s.get("reason", "")

        result.append(
            StakeholderIntel(
                stakeholder_id=str(sid) if sid else None,
                name=name,
                role=role,
                organization=None,
                stakeholder_type=None,
                influence_level=None,
                is_known=False,
                is_primary_contact=False,
                likely_knowledge=[topic] if topic else [],
                domain_expertise=[],
                concerns=[],
                priorities=[],
                engagement_tip=reason or None,
            )
        )

    return result


# =============================================================================
# Requirements Intelligence — Endpoint
# =============================================================================


@router.get("/projects/{project_id}/evidence/intelligence")
async def get_requirements_intelligence(
    project_id: UUID,
) -> RequirementsIntelligenceResponse:
    """
    Aggregate gap analysis, stakeholder data, and deterministic source/tribal-knowledge
    mappings into a requirements intelligence view. No new LLM calls.
    """
    try:
        # 1. Run gap analysis (existing, no LLM)
        gap_result = await analyze_gaps(project_id)

        # 2. Fetch known stakeholders
        stakeholders = list_stakeholders(project_id)

        # 3. Extract topics from gaps, get stakeholder suggestions
        gap_topics = _extract_gap_topics(gap_result.get("priority_gaps", []))
        suggestions = await suggest_stakeholders(project_id, gap_topics) if gap_topics else []

        # 4. Build suggested sources from deterministic mapping
        suggested_sources = _build_suggested_sources(gap_result)

        # 5. Build tribal knowledge from deterministic mapping
        tribal = _build_tribal_knowledge(gap_result)

        # 6. Build stakeholder intelligence (merge known + suggested)
        stakeholder_intel = _build_stakeholder_intelligence(
            stakeholders, suggestions, gap_result.get("priority_gaps", [])
        )

        # 7. Build information gaps
        info_gaps = _build_information_gaps(gap_result.get("priority_gaps", []))

        known_count = sum(1 for s in stakeholder_intel if s.is_known)
        suggested_count = sum(1 for s in stakeholder_intel if not s.is_known)

        logger.info(
            f"Requirements intelligence for project {project_id}",
            extra={
                "project_id": str(project_id),
                "gaps": len(info_gaps),
                "sources": len(suggested_sources),
                "stakeholders_known": known_count,
                "stakeholders_suggested": suggested_count,
            },
        )

        return RequirementsIntelligenceResponse(
            summary=gap_result.get("summary", ""),
            phase=gap_result.get("phase", "unknown"),
            total_readiness=gap_result.get("total_readiness", 0.0),
            information_gaps=info_gaps,
            suggested_sources=suggested_sources,
            stakeholder_intelligence=stakeholder_intel,
            tribal_knowledge=tribal,
            counts=IntelligenceCounts(
                gaps=len(info_gaps),
                sources=len(suggested_sources),
                stakeholders_known=known_count,
                stakeholders_suggested=suggested_count,
                tribal=len(tribal),
            ),
        )

    except Exception as e:
        logger.exception(f"Failed to get requirements intelligence for project {project_id}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve requirements intelligence",
        ) from e
