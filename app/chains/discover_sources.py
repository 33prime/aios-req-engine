"""Phase 1: Source Mapping — SerpAPI query builder + result categorizer.

Generates search queries based on company info and categorizes results
into source types for downstream phases.
"""

import asyncio
import logging
from typing import Any

from app.core.serpapi_service import search_google_safe

logger = logging.getLogger(__name__)

# Cost: ~$0.01 per query
SEARCH_COST_PER_QUERY = 0.01


def build_search_queries(
    company_name: str,
    industry: str | None = None,
    focus_areas: list[str] | None = None,
) -> list[dict[str, str]]:
    """Build categorized search queries from company info.

    Returns list of {query, category} dicts.
    """
    queries = [
        {"query": f'"{company_name}" about', "category": "company"},
        {"query": f'"{company_name}" pricing', "category": "company"},
        {"query": f'"{company_name}" competitors', "category": "competitor"},
        {"query": f'"{company_name}" vs', "category": "competitor"},
        {"query": f'"site:g2.com" "{company_name}"', "category": "review"},
        {"query": f'"site:capterra.com" "{company_name}"', "category": "review"},
        {"query": f'"{company_name}" reviews', "category": "review"},
    ]

    if industry:
        queries.extend([
            {"query": f'"{industry}" market report 2026', "category": "industry"},
            {"query": f'"{industry}" trends 2026', "category": "industry"},
        ])

        # Add pain-focused forum queries
        pain_keywords = " ".join(focus_areas[:3]) if focus_areas else industry
        queries.append(
            {"query": f'"site:reddit.com" "{industry}" {pain_keywords}', "category": "forum"}
        )

    return queries


def categorize_url(url: str, title: str, query_category: str) -> str:
    """Determine source type from URL and query context."""
    url_lower = url.lower()
    if "g2.com" in url_lower:
        return "review"
    if "capterra.com" in url_lower:
        return "review"
    if "reddit.com" in url_lower:
        return "forum"
    if "gartner.com" in url_lower or "forrester.com" in url_lower:
        return "industry"
    return query_category


async def run_source_mapping(
    company_name: str,
    industry: str | None = None,
    focus_areas: list[str] | None = None,
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Execute Phase 1: Source Mapping.

    Returns:
        Tuple of (source_registry, cost_entries)
        source_registry: dict keyed by category -> list of source dicts
        cost_entries: list of cost tracking dicts
    """
    queries = build_search_queries(company_name, industry, focus_areas)
    cost_entries: list[dict[str, Any]] = []

    # Run all searches concurrently
    async def search_one(q: dict[str, str]) -> list[dict[str, Any]]:
        results = await search_google_safe(q["query"], num_results=10)
        cost_entries.append({
            "phase": "source_mapping",
            "service": "serpapi",
            "query": q["query"][:80],
            "cost_usd": SEARCH_COST_PER_QUERY,
        })
        tagged = []
        for r in results:
            source_type = categorize_url(r["url"], r["title"], q["category"])
            tagged.append({
                "url": r["url"],
                "title": r["title"],
                "snippet": r.get("snippet", ""),
                "source_type": source_type,
                "relevance_score": 1.0 - (r.get("position", 1) - 1) * 0.1,
            })
        return tagged

    tasks = [search_one(q) for q in queries]
    all_results = await asyncio.gather(*tasks)

    # Build source registry with deduplication
    source_registry: dict[str, list[dict[str, Any]]] = {
        "company": [],
        "competitor": [],
        "industry": [],
        "review": [],
        "forum": [],
    }
    seen_urls: set[str] = set()

    for batch in all_results:
        for item in batch:
            if item["url"] not in seen_urls:
                seen_urls.add(item["url"])
                cat = item["source_type"]
                if cat in source_registry:
                    source_registry[cat].append(item)

    total_urls = sum(len(v) for v in source_registry.values())
    logger.info(
        f"Source mapping complete: {total_urls} unique URLs across "
        f"{len([k for k, v in source_registry.items() if v])} categories"
    )

    return source_registry, cost_entries
