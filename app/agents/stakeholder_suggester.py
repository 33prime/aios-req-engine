"""Stakeholder Suggestion System.

Suggests who in the client's organization likely has the information
needed for specific topics or questions.

Uses:
- Topic-to-role mapping for common question types
- Project stakeholder database to match to real people
- AI-assisted matching when explicit mappings aren't available
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


class StakeholderSuggestion(BaseModel):
    """A suggested stakeholder for a topic."""

    stakeholder_id: Optional[UUID] = None
    name: Optional[str] = None
    role: str
    topic: str
    reason: str
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    is_matched: bool = False  # True if matched to existing stakeholder


# Topic-to-role mapping for common question/document types
TOPIC_ROLE_MAP = {
    # Business and strategic topics
    "budget": ["CFO", "Finance Director", "Budget Owner", "VP Finance"],
    "financial": ["CFO", "Finance Director", "Controller", "VP Finance"],
    "roi": ["CFO", "Finance Director", "Business Sponsor", "VP Finance"],
    "strategy": ["CEO", "VP Strategy", "Business Development", "COO"],
    "business goals": ["CEO", "Business Sponsor", "VP Strategy", "Product Owner"],
    "kpis": ["Business Sponsor", "Product Owner", "VP Operations", "Analytics Lead"],
    "metrics": ["Product Owner", "Analytics Lead", "VP Operations", "Business Analyst"],
    # Technical topics
    "technical": ["CTO", "Tech Lead", "Engineering Manager", "IT Director"],
    "architecture": ["CTO", "Tech Lead", "Solutions Architect", "Engineering Manager"],
    "integration": ["Tech Lead", "Integration Engineer", "IT Director", "Solutions Architect"],
    "api": ["Tech Lead", "Engineering Manager", "Integration Engineer", "Developer"],
    "security": ["CISO", "Security Lead", "IT Director", "Compliance Officer"],
    "infrastructure": ["IT Director", "DevOps Lead", "CTO", "SysAdmin"],
    "database": ["Database Admin", "Tech Lead", "Engineering Manager", "Data Engineer"],
    # Process and operations
    "process": ["Operations Manager", "Process Owner", "COO", "Business Analyst"],
    "workflow": ["Operations Manager", "Process Owner", "Product Owner", "Team Lead"],
    "operations": ["COO", "Operations Manager", "VP Operations", "Process Owner"],
    "compliance": ["Compliance Officer", "Legal Counsel", "Risk Manager", "CISO"],
    "regulatory": ["Compliance Officer", "Legal Counsel", "Risk Manager", "VP Legal"],
    # User and customer topics
    "users": ["Product Manager", "Customer Success Lead", "UX Lead", "Support Manager"],
    "customer": ["Customer Success Lead", "Product Manager", "Sales Lead", "Support Manager"],
    "support": ["Support Manager", "Customer Success Lead", "Service Desk Lead"],
    "training": ["Training Manager", "HR Lead", "Operations Manager", "Change Manager"],
    # Design and experience
    "design": ["Design Lead", "UX Lead", "Brand Manager", "Creative Director"],
    "ux": ["UX Lead", "Product Designer", "Design Lead", "Product Manager"],
    "brand": ["Brand Manager", "Marketing Lead", "Creative Director", "CMO"],
    # Product and requirements
    "requirements": ["Product Owner", "Product Manager", "Business Analyst", "Project Manager"],
    "features": ["Product Owner", "Product Manager", "Engineering Manager", "Tech Lead"],
    "roadmap": ["Product Manager", "Product Owner", "VP Product", "CEO"],
    "priorities": ["Product Owner", "Product Manager", "Business Sponsor", "CEO"],
    "scope": ["Product Owner", "Project Manager", "Business Sponsor", "Product Manager"],
    # Data topics
    "data": ["Data Analyst", "Database Admin", "Data Engineer", "Business Analyst"],
    "analytics": ["Analytics Lead", "Data Analyst", "Business Intelligence", "Product Manager"],
    "reporting": ["Business Analyst", "Analytics Lead", "Finance Director", "Operations Manager"],
    # Legal and HR
    "legal": ["Legal Counsel", "VP Legal", "Compliance Officer", "Contract Manager"],
    "hr": ["HR Director", "HR Manager", "People Ops Lead", "Talent Lead"],
    "contracts": ["Legal Counsel", "Contract Manager", "Procurement Lead", "VP Legal"],
    # Project management
    "timeline": ["Project Manager", "Program Manager", "Product Owner", "Business Sponsor"],
    "milestones": ["Project Manager", "Program Manager", "Product Manager", "Business Sponsor"],
    "resources": ["Resource Manager", "Project Manager", "HR Director", "Operations Manager"],
}


def _get_topics_from_text(text: str) -> list[str]:
    """Extract relevant topics from text by checking against topic map keys."""
    text_lower = text.lower()
    matched_topics = []

    for topic in TOPIC_ROLE_MAP.keys():
        if topic in text_lower:
            matched_topics.append(topic)

    return matched_topics if matched_topics else ["requirements"]  # Default topic


async def get_stakeholders(project_id: UUID) -> list[dict]:
    """Get existing stakeholders for a project."""
    supabase = get_supabase()

    try:
        result = (
            supabase.table("stakeholders")
            .select("id, name, role, stakeholder_type, is_economic_buyer, is_primary_contact")
            .eq("project_id", str(project_id))
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.warning(f"Could not fetch stakeholders: {e}")
        return []


async def suggest_stakeholders(
    project_id: UUID,
    topics: list[str],
) -> list[StakeholderSuggestion]:
    """
    Suggest stakeholders who likely have information on given topics.

    Args:
        project_id: Project UUID
        topics: List of topics/question areas

    Returns:
        List of StakeholderSuggestion with matched or suggested roles
    """
    # Get existing stakeholders
    existing = await get_stakeholders(project_id)

    suggestions = []
    seen_roles = set()

    for topic in topics:
        topic_lower = topic.lower()

        # Get suggested roles for this topic
        roles = []
        for map_topic, map_roles in TOPIC_ROLE_MAP.items():
            if map_topic in topic_lower or topic_lower in map_topic:
                roles = map_roles
                break

        if not roles:
            roles = ["Subject Matter Expert", "Domain Expert", "Team Lead"]

        # Try to match to existing stakeholders
        matched = False
        for stakeholder in existing:
            stakeholder_role = (stakeholder.get("role") or "").lower()
            stakeholder_name = stakeholder.get("name", "")

            for role in roles:
                if role.lower() in stakeholder_role or stakeholder_role in role.lower():
                    # Found a match
                    role_key = f"{stakeholder['id']}:{topic}"
                    if role_key not in seen_roles:
                        suggestions.append(
                            StakeholderSuggestion(
                                stakeholder_id=UUID(stakeholder["id"]),
                                name=stakeholder_name,
                                role=stakeholder.get("role") or role,
                                topic=topic,
                                reason=f"'{stakeholder_name}' as {stakeholder.get('role')} typically handles {topic} decisions",
                                confidence=0.85,
                                is_matched=True,
                            )
                        )
                        seen_roles.add(role_key)
                        matched = True
                        break
            if matched:
                break

        # If no match, suggest the generic role
        if not matched and roles:
            role_key = f"generic:{roles[0]}:{topic}"
            if role_key not in seen_roles:
                suggestions.append(
                    StakeholderSuggestion(
                        stakeholder_id=None,
                        name=None,
                        role=roles[0],
                        topic=topic,
                        reason=f"This role typically has knowledge about {topic}",
                        confidence=0.6,
                        is_matched=False,
                    )
                )
                seen_roles.add(role_key)

    return suggestions


async def suggest_stakeholder_for_question(
    project_id: UUID,
    question: str,
) -> list[StakeholderSuggestion]:
    """
    Suggest who can best answer a specific question.

    Args:
        project_id: Project UUID
        question: The question text

    Returns:
        List of stakeholder suggestions
    """
    # Extract topics from question
    topics = _get_topics_from_text(question)

    return await suggest_stakeholders(project_id, topics)


async def suggest_stakeholder_for_document(
    project_id: UUID,
    document_name: str,
    document_description: Optional[str] = None,
) -> list[StakeholderSuggestion]:
    """
    Suggest who can provide a specific document.

    Args:
        project_id: Project UUID
        document_name: Name of the requested document
        document_description: Optional description

    Returns:
        List of stakeholder suggestions
    """
    # Extract topics from document name and description
    text = document_name
    if document_description:
        text += " " + document_description

    topics = _get_topics_from_text(text)

    return await suggest_stakeholders(project_id, topics)


async def get_stakeholder_suggestions_for_prep(
    project_id: UUID,
    questions: list[str],
    documents: list[str],
) -> dict[str, list[StakeholderSuggestion]]:
    """
    Get stakeholder suggestions for a full prep bundle.

    Args:
        project_id: Project UUID
        questions: List of question texts
        documents: List of document names

    Returns:
        Dict mapping item type+text to suggestions
    """
    result = {}

    for question in questions:
        suggestions = await suggest_stakeholder_for_question(project_id, question)
        if suggestions:
            result[f"question:{question[:50]}"] = suggestions

    for doc in documents:
        suggestions = await suggest_stakeholder_for_document(project_id, doc)
        if suggestions:
            result[f"document:{doc[:50]}"] = suggestions

    return result
