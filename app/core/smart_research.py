"""
Smart Research Decision Logic

Determines when research should be run based on signal content,
existing project context, and research freshness.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from app.core.schemas_evidence import ResearchRecommendation, ResearchTrigger
from app.db.supabase_client import get_supabase


async def should_run_research(
    project_id: UUID,
    signal_id: UUID,
    signal_content: str
) -> ResearchRecommendation:
    """
    Intelligently determine if research is needed for this signal.

    Returns:
        ResearchRecommendation with should_run flag and reasoning
    """
    triggers = []
    new_domains = []
    missing_topics = []
    stale_topics = []

    # Get project context
    supabase = get_supabase()
    try:
        response = supabase.table("projects").select("*").eq("id", str(project_id)).execute()
        if not response.data:
            return ResearchRecommendation(should_run=False, triggers=[])
    except Exception:
        return ResearchRecommendation(should_run=False, triggers=[])

    # Check 1: New domain/industry detection
    domains = await _detect_domains(signal_content)
    project_domains = await _get_project_domains(project_id)

    for domain in domains:
        if domain not in project_domains:
            new_domains.append(domain)
            triggers.append({
                "trigger": ResearchTrigger.NEW_DOMAIN,
                "description": f"First mention of '{domain}' in project",
                "priority": "high"
            })

    # Check 2: Missing context
    topics = await _extract_topics(signal_content)
    for topic in topics:
        has_research = await _has_research_for_topic(project_id, topic)
        if not has_research:
            missing_topics.append(topic)
            triggers.append({
                "trigger": ResearchTrigger.MISSING_CONTEXT,
                "description": f"No research exists for '{topic}'",
                "priority": "medium"
            })

    # Check 3: Competitive mentions
    if await _mentions_competitors(signal_content):
        has_competitive = await _has_competitive_research(project_id)
        if not has_competitive:
            triggers.append({
                "trigger": ResearchTrigger.COMPETITIVE_GAP,
                "description": "Signal mentions competitors but no competitive research exists",
                "priority": "high"
            })

    # Check 4: Stale research (>30 days old)
    stale = await _get_stale_topics(project_id, topics)
    if stale:
        stale_topics.extend(stale)
        triggers.append({
            "trigger": ResearchTrigger.STALE_DATA,
            "description": f"Research for {len(stale)} topics is >30 days old",
            "priority": "medium"
        })

    # Generate suggested queries if research is needed
    suggested_queries = []
    if triggers:
        suggested_queries = await _generate_research_queries(
            new_domains, missing_topics, stale_topics, signal_content
        )

    return ResearchRecommendation(
        should_run=len(triggers) > 0,
        triggers=triggers,
        suggested_queries=suggested_queries,
        estimated_duration="2-3 minutes" if len(suggested_queries) <= 5 else "5-7 minutes",
        new_domains=new_domains,
        missing_topics=missing_topics,
        stale_topics=stale_topics
    )


# Helper functions

async def _detect_domains(content: str) -> List[str]:
    """Extract domain/industry mentions from signal content."""
    # Keywords that indicate domains
    domain_keywords = {
        "healthcare": ["health", "medical", "patient", "doctor", "hospital", "clinic"],
        "fintech": ["payment", "banking", "financial", "transaction", "stripe", "paypal"],
        "ecommerce": ["shop", "cart", "checkout", "product", "inventory", "order"],
        "saas": ["subscription", "tenant", "workspace", "organization", "billing"],
        "education": ["student", "course", "learning", "teacher", "classroom"],
        "real_estate": ["property", "listing", "rental", "lease", "mortgage"],
    }

    content_lower = content.lower()
    detected = []

    for domain, keywords in domain_keywords.items():
        if any(keyword in content_lower for keyword in keywords):
            detected.append(domain)

    return detected


async def _get_project_domains(project_id: UUID) -> List[str]:
    """Get domains already covered in project research."""
    supabase = get_supabase()
    try:
        response = supabase.table("signal_chunks").select("metadata").eq(
            "project_id", str(project_id)
        ).execute()

        domains = set()
        for row in response.data:
            metadata = row.get("metadata", {})
            if metadata and isinstance(metadata, dict):
                domain = metadata.get("domain")
                if domain:
                    domains.add(domain)

        return list(domains)
    except Exception:
        return []


async def _extract_topics(content: str) -> List[str]:
    """Extract key topics from signal content."""
    # Simple topic extraction based on keywords
    # In production, could use NLP/LLM for better extraction
    topics = []

    content_lower = content.lower()

    topic_patterns = {
        "authentication": ["login", "signup", "password", "auth", "sso", "oauth"],
        "payments": ["payment", "billing", "subscription", "stripe", "checkout"],
        "notifications": ["notification", "email", "sms", "push", "alert"],
        "analytics": ["analytics", "metrics", "dashboard", "report", "insights"],
        "mobile": ["mobile", "ios", "android", "app", "responsive"],
        "ai": ["ai", "machine learning", "ml", "artificial intelligence", "gpt"],
    }

    for topic, patterns in topic_patterns.items():
        if any(pattern in content_lower for pattern in patterns):
            topics.append(topic)

    return topics


async def _has_research_for_topic(project_id: UUID, topic: str) -> bool:
    """Check if research exists for a topic."""
    supabase = get_supabase()
    try:
        # Check metadata topic or content match
        response = supabase.table("signal_chunks").select("id").eq(
            "project_id", str(project_id)
        ).eq("chunk_type", "research").execute()

        if not response.data:
            return False

        # Check if any chunk matches the topic
        for chunk in response.data:
            metadata = chunk.get("metadata", {})
            if metadata and metadata.get("topic") == topic:
                return True
            content = chunk.get("content", "")
            if topic.lower() in content.lower():
                return True

        return False
    except Exception:
        return False


async def _mentions_competitors(content: str) -> bool:
    """Check if signal mentions competitors."""
    competitor_keywords = [
        "competitor", "competitive", "vs", "versus", "alternative",
        "compared to", "better than", "similar to", "like"
    ]

    content_lower = content.lower()
    return any(keyword in content_lower for keyword in competitor_keywords)


async def _has_competitive_research(project_id: UUID) -> bool:
    """Check if competitive research exists."""
    supabase = get_supabase()
    try:
        response = supabase.table("signal_chunks").select("metadata").eq(
            "project_id", str(project_id)
        ).eq("chunk_type", "research").execute()

        if not response.data:
            return False

        # Check if any chunk has competitive research type
        for chunk in response.data:
            metadata = chunk.get("metadata", {})
            if metadata and metadata.get("research_type") == "competitive":
                return True

        return False
    except Exception:
        return False


async def _get_stale_topics(
    project_id: UUID,
    topics: List[str]
) -> List[str]:
    """Get topics with research older than 30 days."""
    stale = []
    cutoff = datetime.utcnow() - timedelta(days=30)
    supabase = get_supabase()

    for topic in topics:
        try:
            response = supabase.table("signal_chunks").select(
                "created_at, metadata"
            ).eq("project_id", str(project_id)).eq("chunk_type", "research").execute()

            if not response.data:
                stale.append(topic)
                continue

            # Find latest research for this topic
            latest_date = None
            for chunk in response.data:
                metadata = chunk.get("metadata", {})
                if metadata and metadata.get("topic") == topic:
                    created_at = chunk.get("created_at")
                    if created_at:
                        # Parse datetime string if needed
                        if isinstance(created_at, str):
                            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        if not latest_date or created_at > latest_date:
                            latest_date = created_at

            if latest_date and latest_date < cutoff:
                stale.append(topic)
            elif not latest_date:
                stale.append(topic)

        except Exception:
            continue

    return stale


async def _generate_research_queries(
    new_domains: List[str],
    missing_topics: List[str],
    stale_topics: List[str],
    signal_content: str
) -> List[str]:
    """Generate suggested research queries."""
    queries = []

    # New domains
    for domain in new_domains:
        queries.append(f"Market overview and trends in {domain}")
        queries.append(f"Leading competitors in {domain}")

    # Missing topics
    for topic in missing_topics[:3]:  # Limit to top 3
        queries.append(f"Best practices for {topic}")
        queries.append(f"Common {topic} solutions and tools")

    # Stale topics
    for topic in stale_topics[:2]:  # Limit to top 2
        queries.append(f"Latest developments in {topic}")

    # Limit total queries
    return queries[:8]
