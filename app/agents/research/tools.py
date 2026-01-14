"""Tools for the Deep Research Agent.

These tools enable the agent to:
1. Search the web for competitors and market information
2. Fetch and analyze web pages
3. Search and analyze G2/Capterra reviews
4. Save findings to the database
5. Generate synthesis artifacts
"""

import json
import re
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import httpx
from openai import OpenAI
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.supabase_client import get_supabase
from app.db.competitor_refs import create_competitor_ref, update_competitor_ref

logger = get_logger(__name__)


# === TOOL DEFINITIONS (for Claude) ===

TOOL_DEFINITIONS = [
    {
        "name": "web_search",
        "description": "Search the web for information. Use this to find competitors, market trends, news, and research. Returns summarized search results with URLs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query. Be specific - include industry, product type, and what you're looking for."
                },
                "search_type": {
                    "type": "string",
                    "enum": ["general", "competitors", "reviews", "news", "pricing"],
                    "description": "Type of search to optimize results"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "fetch_page",
        "description": "Fetch and extract content from a web page. Use this to get detailed information from a specific URL like a competitor's homepage, pricing page, or feature page.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch"
                },
                "extract_type": {
                    "type": "string",
                    "enum": ["full", "features", "pricing", "about"],
                    "description": "What type of content to focus on extracting"
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "search_g2",
        "description": "Search G2 for software products in a category. Returns product listings with ratings and basic info.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Software category to search (e.g., 'sales engagement', 'CRM', 'automotive software')"
                },
                "keywords": {
                    "type": "string",
                    "description": "Additional keywords to filter results"
                }
            },
            "required": ["category"]
        }
    },
    {
        "name": "fetch_reviews",
        "description": "Fetch user reviews for a specific product from G2, Capterra, or other review sites. Returns actual user quotes with sentiment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Name of the product to get reviews for"
                },
                "source": {
                    "type": "string",
                    "enum": ["g2", "capterra", "trustpilot", "any"],
                    "description": "Review source to search"
                },
                "max_reviews": {
                    "type": "integer",
                    "description": "Maximum number of reviews to fetch (default 10)"
                }
            },
            "required": ["product_name"]
        }
    },
    {
        "name": "save_competitor",
        "description": "Save or update a competitor in the database. Use this when you've gathered enough information about a competitor.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Competitor name"
                },
                "website": {
                    "type": "string",
                    "description": "Competitor website URL"
                },
                "category": {
                    "type": "string",
                    "enum": ["direct_competitor", "adjacent", "emerging", "enterprise_alternative"],
                    "description": "How this competitor relates to us"
                },
                "description": {
                    "type": "string",
                    "description": "Brief description of the competitor"
                },
                "strengths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key strengths"
                },
                "weaknesses": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Key weaknesses"
                },
                "key_features": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Main features they offer"
                },
                "pricing_model": {
                    "type": "string",
                    "description": "How they price (per_seat, flat_rate, usage_based, freemium)"
                },
                "target_market": {
                    "type": "string",
                    "description": "Who they target (SMB, mid-market, enterprise)"
                }
            },
            "required": ["name", "website", "category", "description"]
        }
    },
    {
        "name": "save_user_voice",
        "description": "Save a user review or quote that provides valuable insight.",
        "input_schema": {
            "type": "object",
            "properties": {
                "quote": {
                    "type": "string",
                    "description": "The actual user quote"
                },
                "source_type": {
                    "type": "string",
                    "enum": ["g2", "capterra", "trustpilot", "reddit", "twitter", "forum", "other"],
                    "description": "Where this came from"
                },
                "source_url": {
                    "type": "string",
                    "description": "URL to the source"
                },
                "competitor_name": {
                    "type": "string",
                    "description": "Competitor this review is about (if applicable)"
                },
                "sentiment": {
                    "type": "string",
                    "enum": ["positive", "negative", "neutral", "mixed"],
                    "description": "Overall sentiment"
                },
                "themes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Themes mentioned (ease_of_use, mobile, integration, etc.)"
                },
                "pain_points": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Pain points mentioned"
                },
                "rating": {
                    "type": "number",
                    "description": "Rating if available (1-5 scale)"
                },
                "reviewer_role": {
                    "type": "string",
                    "description": "Role of the reviewer if known"
                }
            },
            "required": ["quote", "source_type", "sentiment"]
        }
    },
    {
        "name": "save_market_gap",
        "description": "Save an identified market gap or opportunity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "gap_type": {
                    "type": "string",
                    "enum": ["feature_gap", "market_segment", "integration", "pricing", "ux", "technical"],
                    "description": "Type of gap"
                },
                "title": {
                    "type": "string",
                    "description": "Short title for the gap"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the gap"
                },
                "evidence": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Evidence supporting this gap"
                },
                "opportunity_size": {
                    "type": "string",
                    "enum": ["small", "medium", "large"],
                    "description": "Size of the opportunity"
                },
                "confidence": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Confidence in this gap"
                },
                "recommended_action": {
                    "type": "string",
                    "description": "What should we do about it"
                }
            },
            "required": ["gap_type", "title", "description"]
        }
    },
    {
        "name": "generate_feature_matrix",
        "description": "Generate a feature comparison matrix based on all gathered competitor data. Call this during synthesis phase.",
        "input_schema": {
            "type": "object",
            "properties": {
                "include_all_features": {
                    "type": "boolean",
                    "description": "Include all discovered features, not just our features"
                }
            }
        }
    },
    {
        "name": "complete_phase",
        "description": "Mark a research phase as complete and move to the next phase.",
        "input_schema": {
            "type": "object",
            "properties": {
                "phase": {
                    "type": "string",
                    "enum": ["discovery", "deep_dives", "user_voice", "feature_analysis", "synthesis"],
                    "description": "Phase to mark complete"
                },
                "summary": {
                    "type": "string",
                    "description": "Brief summary of what was accomplished in this phase"
                }
            },
            "required": ["phase", "summary"]
        }
    }
]


# === TOOL IMPLEMENTATIONS ===

class ToolContext(BaseModel):
    """Context passed to all tool implementations."""

    project_id: UUID
    run_id: UUID
    state_snapshot: str
    project_features: list[dict[str, Any]] = Field(default_factory=list)
    # Mutable state
    competitors_saved: list[str] = Field(default_factory=list)
    user_voices_saved: int = 0
    market_gaps_saved: int = 0


async def execute_tool(
    tool_name: str,
    tool_input: dict[str, Any],
    context: ToolContext
) -> dict[str, Any]:
    """Execute a tool and return the result."""

    logger.info(f"Executing tool: {tool_name}", extra={"input": tool_input})

    try:
        if tool_name == "web_search":
            return await _web_search(tool_input, context)
        elif tool_name == "fetch_page":
            return await _fetch_page(tool_input, context)
        elif tool_name == "search_g2":
            return await _search_g2(tool_input, context)
        elif tool_name == "fetch_reviews":
            return await _fetch_reviews(tool_input, context)
        elif tool_name == "save_competitor":
            return await _save_competitor(tool_input, context)
        elif tool_name == "save_user_voice":
            return await _save_user_voice(tool_input, context)
        elif tool_name == "save_market_gap":
            return await _save_market_gap(tool_input, context)
        elif tool_name == "generate_feature_matrix":
            return await _generate_feature_matrix(tool_input, context)
        elif tool_name == "complete_phase":
            return await _complete_phase(tool_input, context)
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        logger.error(f"Tool {tool_name} failed: {e}")
        return {"error": str(e)}


async def _web_search(input: dict, context: ToolContext) -> dict:
    """Execute web search using Perplexity."""
    settings = get_settings()
    query = input["query"]
    search_type = input.get("search_type", "general")

    # Enhance query based on type
    enhanced_query = query
    if search_type == "competitors":
        enhanced_query = f"top competitors alternatives to {query} software 2025"
    elif search_type == "reviews":
        enhanced_query = f"{query} reviews ratings user feedback"
    elif search_type == "pricing":
        enhanced_query = f"{query} pricing plans cost"
    elif search_type == "news":
        enhanced_query = f"{query} latest news 2025"

    client = OpenAI(
        api_key=settings.PERPLEXITY_API_KEY,
        base_url="https://api.perplexity.ai"
    )

    try:
        response = client.chat.completions.create(
            model=settings.PERPLEXITY_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a market research analyst. Provide detailed, factual information with specific company names, features, and data points. Always cite sources."
                },
                {"role": "user", "content": enhanced_query}
            ],
            temperature=0.2,
            max_tokens=4000,
        )

        content = response.choices[0].message.content or ""

        return {
            "query": query,
            "enhanced_query": enhanced_query,
            "results": content,
            "search_type": search_type,
        }

    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}


async def _fetch_page(input: dict, context: ToolContext) -> dict:
    """Fetch and extract content from a web page."""
    settings = get_settings()
    url = input["url"]
    extract_type = input.get("extract_type", "full")

    # Use Jina AI Reader for clean extraction
    jina_url = f"https://r.jina.ai/{url}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                jina_url,
                headers={"Accept": "text/plain"}
            )
            response.raise_for_status()
            content = response.text

            # Truncate if too long
            if len(content) > 15000:
                content = content[:15000] + "\n\n[Content truncated...]"

            return {
                "url": url,
                "extract_type": extract_type,
                "content": content,
                "length": len(content),
            }

        except Exception as e:
            return {"error": f"Failed to fetch {url}: {str(e)}"}


async def _search_g2(input: dict, context: ToolContext) -> dict:
    """Search G2 for products in a category."""
    settings = get_settings()
    category = input["category"]
    keywords = input.get("keywords", "")

    # Use Perplexity to search G2
    query = f"site:g2.com {category} software {keywords} top rated products list"

    client = OpenAI(
        api_key=settings.PERPLEXITY_API_KEY,
        base_url="https://api.perplexity.ai"
    )

    try:
        response = client.chat.completions.create(
            model=settings.PERPLEXITY_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are researching software on G2. List the top products with their G2 ratings, number of reviews, and key features. Be specific with names and data."
                },
                {"role": "user", "content": query}
            ],
            temperature=0.2,
            max_tokens=3000,
        )

        return {
            "category": category,
            "keywords": keywords,
            "results": response.choices[0].message.content or "",
        }

    except Exception as e:
        return {"error": f"G2 search failed: {str(e)}"}


async def _fetch_reviews(input: dict, context: ToolContext) -> dict:
    """Fetch user reviews for a product."""
    settings = get_settings()
    product_name = input["product_name"]
    source = input.get("source", "any")
    max_reviews = input.get("max_reviews", 10)

    # Build search query
    source_filter = ""
    if source == "g2":
        source_filter = "site:g2.com"
    elif source == "capterra":
        source_filter = "site:capterra.com"
    elif source == "trustpilot":
        source_filter = "site:trustpilot.com"

    query = f"{source_filter} {product_name} reviews user feedback pros cons"

    client = OpenAI(
        api_key=settings.PERPLEXITY_API_KEY,
        base_url="https://api.perplexity.ai"
    )

    try:
        response = client.chat.completions.create(
            model=settings.PERPLEXITY_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": f"""You are extracting user reviews. Find actual user quotes and feedback.
For each review, extract:
- The actual quote (exact words from users)
- Rating (1-5 stars if available)
- User role if mentioned
- Key themes (ease_of_use, mobile, integration, support, etc.)
- Pros and cons

Return up to {max_reviews} reviews. Focus on recent, detailed reviews."""
                },
                {"role": "user", "content": query}
            ],
            temperature=0.2,
            max_tokens=4000,
        )

        return {
            "product_name": product_name,
            "source": source,
            "reviews": response.choices[0].message.content or "",
        }

    except Exception as e:
        return {"error": f"Review fetch failed: {str(e)}"}


async def _save_competitor(input: dict, context: ToolContext) -> dict:
    """Save competitor to database."""
    supabase = get_supabase()

    # Map category to reference_type
    category_map = {
        "direct_competitor": "competitor",
        "adjacent": "competitor",
        "emerging": "competitor",
        "enterprise_alternative": "competitor",
    }
    reference_type = category_map.get(input["category"], "competitor")

    # Build research notes from additional fields
    notes_parts = []
    if input.get("pricing_model"):
        notes_parts.append(f"Pricing: {input['pricing_model']}")
    if input.get("target_market"):
        notes_parts.append(f"Target: {input['target_market']}")
    if input.get("key_features"):
        notes_parts.append(f"Features: {', '.join(input['key_features'][:5])}")
    research_notes = "\n".join(notes_parts) if notes_parts else None

    try:
        # Check if competitor already exists
        existing = supabase.table("competitor_references").select("id").eq(
            "project_id", str(context.project_id)
        ).eq("name", input["name"]).maybe_single().execute()

        if existing.data:
            # Update existing
            update_competitor_ref(
                ref_id=UUID(existing.data["id"]),
                project_id=context.project_id,
                url=input.get("website"),
                category=input["category"],
                strengths=input.get("strengths", []),
                weaknesses=input.get("weaknesses", []),
                features_to_study=input.get("key_features", []),
                research_notes=research_notes,
            )
            context.competitors_saved.append(input["name"])
            return {"status": "updated", "name": input["name"]}
        else:
            # Create new
            create_competitor_ref(
                project_id=context.project_id,
                reference_type=reference_type,
                name=input["name"],
                url=input.get("website"),
                category=input["category"],
                strengths=input.get("strengths", []),
                weaknesses=input.get("weaknesses", []),
                features_to_study=input.get("key_features", []),
                research_notes=research_notes,
            )
            context.competitors_saved.append(input["name"])
            return {"status": "created", "name": input["name"]}

    except Exception as e:
        return {"error": f"Failed to save competitor: {str(e)}"}


async def _save_user_voice(input: dict, context: ToolContext) -> dict:
    """Save user voice/review to database."""
    supabase = get_supabase()

    try:
        data = {
            "id": str(uuid4()),
            "project_id": str(context.project_id),
            "source_type": input["source_type"],
            "quote": input["quote"],
            "sentiment": input["sentiment"],
            "themes": input.get("themes", []),
            "pain_points_mentioned": input.get("pain_points", []),
        }

        if input.get("source_url"):
            data["source_url"] = input["source_url"]
        if input.get("competitor_name"):
            data["competitor_name"] = input["competitor_name"]
        if input.get("rating"):
            data["rating"] = input["rating"]
        if input.get("reviewer_role"):
            data["reviewer_role"] = input["reviewer_role"]

        supabase.table("user_voices").insert(data).execute()
        context.user_voices_saved += 1

        return {"status": "saved", "quote_preview": input["quote"][:100] + "..."}

    except Exception as e:
        # Table might not exist yet - that's ok
        logger.warning(f"Could not save user voice (table may not exist): {e}")
        return {"status": "skipped", "reason": "Table not yet created"}


async def _save_market_gap(input: dict, context: ToolContext) -> dict:
    """Save market gap to database."""
    supabase = get_supabase()

    try:
        data = {
            "id": str(uuid4()),
            "project_id": str(context.project_id),
            "gap_type": input["gap_type"],
            "title": input["title"],
            "description": input["description"],
            "evidence": input.get("evidence", []),
            "confidence": input.get("confidence", "medium"),
            "opportunity_size": input.get("opportunity_size"),
            "recommended_action": input.get("recommended_action"),
        }

        supabase.table("market_gaps").insert(data).execute()
        context.market_gaps_saved += 1

        return {"status": "saved", "title": input["title"]}

    except Exception as e:
        # Table might not exist yet
        logger.warning(f"Could not save market gap (table may not exist): {e}")
        return {"status": "skipped", "reason": "Table not yet created"}


async def _generate_feature_matrix(input: dict, context: ToolContext) -> dict:
    """Generate feature comparison matrix."""
    supabase = get_supabase()

    try:
        # Get saved competitors
        competitors = supabase.table("competitor_references").select(
            "name, features_to_study, strengths"
        ).eq("project_id", str(context.project_id)).execute().data or []

        if not competitors:
            return {"error": "No competitors saved yet. Run discovery phase first."}

        # Build matrix structure
        competitor_names = [c["name"] for c in competitors]
        our_features = [f["name"] for f in context.project_features]

        # Collect all features mentioned
        all_features = set(our_features)
        for comp in competitors:
            all_features.update(comp.get("features_to_study", []))

        matrix = {
            "competitors": competitor_names,
            "our_features": our_features,
            "all_features": list(all_features),
            "competitor_features": {
                c["name"]: c.get("features_to_study", []) for c in competitors
            }
        }

        return {"matrix": matrix, "competitor_count": len(competitors)}

    except Exception as e:
        return {"error": f"Failed to generate matrix: {str(e)}"}


async def _complete_phase(input: dict, context: ToolContext) -> dict:
    """Mark a phase as complete."""
    phase = input["phase"]
    summary = input["summary"]

    return {
        "phase_completed": phase,
        "summary": summary,
        "stats": {
            "competitors_saved": len(context.competitors_saved),
            "user_voices_saved": context.user_voices_saved,
            "market_gaps_saved": context.market_gaps_saved,
        }
    }
