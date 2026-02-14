"""Discovery Readiness Assessment.

Pure data query — no LLM, no cost. Checks what project data exists
and scores how effective a discovery pipeline run would be.
"""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.business_drivers import list_business_drivers
from app.db.company_info import get_company_info
from app.db.competitor_refs import list_competitor_refs
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

# Scoring weights
WEIGHTS = {
    "company_name": 15,
    "company_website": 20,
    "industry": 10,
    "known_competitors": 20,
    "pain_keywords": 10,
    "project_vision": 5,
    "processed_signals": 10,
    "personas": 5,
    "features": 5,
}

# Base cost estimate components (USD)
BASE_COST = 0.92
PDL_COST = 0.03
FORUM_SAVINGS = 0.02
COMPETITOR_PDL_SAVINGS = 0.06  # ~2 competitor PDL lookups saved
TARGETED_SEARCH_SAVINGS = 0.02


def assess_discovery_readiness(project_id: UUID) -> dict[str, Any]:
    """Assess how ready a project is for discovery pipeline.

    Returns a readiness report with score, what exists, what's missing,
    and actionable suggestions.
    """
    supabase = get_supabase()

    # --- Load project data ---
    project = supabase.table("projects").select(
        "id, name, client_name, metadata, vision"
    ).eq("id", str(project_id)).maybe_single().execute()

    if not project.data:
        return {
            "score": 0,
            "effectiveness_label": "Poor",
            "have": [],
            "missing": [],
            "actions": [],
            "category_scores": {},
            "cost_estimate": BASE_COST,
            "potential_savings": 0.0,
        }

    project_data = project.data
    project_meta = project_data.get("metadata") or {}

    # Company info
    company_info = get_company_info(project_id)

    # Competitors
    competitors = list_competitor_refs(project_id, limit=100)

    # Business drivers
    drivers = list_business_drivers(project_id, limit=100)
    pain_drivers = [d for d in drivers if d.get("driver_type") == "pain"]
    goal_drivers = [d for d in drivers if d.get("driver_type") == "goal"]

    # Signals count
    signals_result = supabase.table("signals").select(
        "id", count="exact"
    ).eq("project_id", str(project_id)).execute()
    signal_count = signals_result.count or 0

    # Personas count
    personas_result = supabase.table("personas").select(
        "id", count="exact"
    ).eq("project_id", str(project_id)).execute()
    persona_count = personas_result.count or 0

    # Features count
    features_result = supabase.table("features").select(
        "id", count="exact"
    ).eq("project_id", str(project_id)).execute()
    feature_count = features_result.count or 0

    # --- Score each category ---
    have: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    category_scores: dict[str, dict[str, Any]] = {}
    potential_savings = 0.0

    # Company name
    company_name = (
        (company_info or {}).get("name")
        or project_meta.get("company_name")
        or project_data.get("client_name")
    )
    if company_name:
        have.append({"item": "Company name", "value": company_name, "weight": WEIGHTS["company_name"]})
        category_scores["company_name"] = {"score": WEIGHTS["company_name"], "max": WEIGHTS["company_name"]}
    else:
        missing.append({
            "item": "Company name",
            "impact": "HIGH",
            "reason": "Discovery cannot run without a company name — all searches depend on it",
            "weight": WEIGHTS["company_name"],
        })
        category_scores["company_name"] = {"score": 0, "max": WEIGHTS["company_name"]}

    # Company website
    company_website = (company_info or {}).get("website") or project_meta.get("company_website")
    if company_website:
        have.append({"item": "Company website", "value": company_website, "weight": WEIGHTS["company_website"]})
        category_scores["company_website"] = {"score": WEIGHTS["company_website"], "max": WEIGHTS["company_website"]}
        potential_savings += PDL_COST
    else:
        missing.append({
            "item": "Company website",
            "impact": "HIGH",
            "reason": "Without the website, discovery must search for it and may match the wrong company",
            "weight": WEIGHTS["company_website"],
        })
        category_scores["company_website"] = {"score": 0, "max": WEIGHTS["company_website"]}

    # Industry
    industry = (company_info or {}).get("industry") or project_meta.get("industry")
    if industry:
        have.append({"item": "Industry", "value": industry, "weight": WEIGHTS["industry"]})
        category_scores["industry"] = {"score": WEIGHTS["industry"], "max": WEIGHTS["industry"]}
    else:
        missing.append({
            "item": "Industry",
            "impact": "MEDIUM",
            "reason": "Market research and trend searches will be skipped without an industry",
            "weight": WEIGHTS["industry"],
        })
        category_scores["industry"] = {"score": 0, "max": WEIGHTS["industry"]}

    # Known competitors
    competitor_count = len(competitors)
    if competitor_count > 0:
        names = [c.get("name", "?") for c in competitors[:5]]
        have.append({
            "item": "Known competitors",
            "value": f"{competitor_count} known ({', '.join(names)})",
            "weight": WEIGHTS["known_competitors"],
        })
        category_scores["known_competitors"] = {"score": WEIGHTS["known_competitors"], "max": WEIGHTS["known_competitors"]}
        potential_savings += COMPETITOR_PDL_SAVINGS
    else:
        missing.append({
            "item": "Known competitors",
            "impact": "HIGH",
            "reason": "Discovery must guess competitors from search results instead of profiling known ones",
            "weight": WEIGHTS["known_competitors"],
        })
        category_scores["known_competitors"] = {"score": 0, "max": WEIGHTS["known_competitors"]}

    # Pain keywords
    if len(pain_drivers) > 0:
        pain_descs = [d.get("description", "?")[:40] for d in pain_drivers[:3]]
        have.append({
            "item": "Pain point keywords",
            "value": f"{len(pain_drivers)} pain drivers ({'; '.join(pain_descs)})",
            "weight": WEIGHTS["pain_keywords"],
        })
        category_scores["pain_keywords"] = {"score": WEIGHTS["pain_keywords"], "max": WEIGHTS["pain_keywords"]}
        potential_savings += FORUM_SAVINGS + TARGETED_SEARCH_SAVINGS
    else:
        missing.append({
            "item": "Pain point keywords",
            "impact": "MEDIUM",
            "reason": "Forum searches will use generic industry terms instead of specific client pain points",
            "weight": WEIGHTS["pain_keywords"],
        })
        category_scores["pain_keywords"] = {"score": 0, "max": WEIGHTS["pain_keywords"]}

    # Project vision
    vision = project_data.get("vision")
    if vision:
        have.append({"item": "Project vision", "value": vision[:60] + ("..." if len(vision) > 60 else ""), "weight": WEIGHTS["project_vision"]})
        category_scores["project_vision"] = {"score": WEIGHTS["project_vision"], "max": WEIGHTS["project_vision"]}
    else:
        missing.append({
            "item": "Project vision",
            "impact": "LOW",
            "reason": "Discovery can proceed without a vision, but synthesis quality improves with one",
            "weight": WEIGHTS["project_vision"],
        })
        category_scores["project_vision"] = {"score": 0, "max": WEIGHTS["project_vision"]}

    # Processed signals
    if signal_count >= 3:
        have.append({"item": "Processed signals", "value": f"{signal_count} signals", "weight": WEIGHTS["processed_signals"]})
        category_scores["processed_signals"] = {"score": WEIGHTS["processed_signals"], "max": WEIGHTS["processed_signals"]}
    elif signal_count > 0:
        partial = round(WEIGHTS["processed_signals"] * signal_count / 3)
        have.append({"item": "Processed signals", "value": f"{signal_count} signal(s) (3+ recommended)", "weight": partial})
        category_scores["processed_signals"] = {"score": partial, "max": WEIGHTS["processed_signals"]}
    else:
        missing.append({
            "item": "Processed signals (3+)",
            "impact": "MEDIUM",
            "reason": "Discovery call recordings provide pain keywords, competitor mentions, and context for targeted searches",
            "weight": WEIGHTS["processed_signals"],
        })
        category_scores["processed_signals"] = {"score": 0, "max": WEIGHTS["processed_signals"]}

    # Personas
    if persona_count >= 1:
        have.append({"item": "Personas", "value": f"{persona_count} persona(s)", "weight": WEIGHTS["personas"]})
        category_scores["personas"] = {"score": WEIGHTS["personas"], "max": WEIGHTS["personas"]}
    else:
        missing.append({
            "item": "Personas (1+)",
            "impact": "LOW",
            "reason": "Discovery driver synthesis maps drivers to personas when available",
            "weight": WEIGHTS["personas"],
        })
        category_scores["personas"] = {"score": 0, "max": WEIGHTS["personas"]}

    # Features
    if feature_count >= 1:
        have.append({"item": "Features", "value": f"{feature_count} feature(s)", "weight": WEIGHTS["features"]})
        category_scores["features"] = {"score": WEIGHTS["features"], "max": WEIGHTS["features"]}
    else:
        missing.append({
            "item": "Features (1+)",
            "impact": "LOW",
            "reason": "Discovery driver synthesis maps drivers to features when available",
            "weight": WEIGHTS["features"],
        })
        category_scores["features"] = {"score": 0, "max": WEIGHTS["features"]}

    # --- Compute total score ---
    total_score = sum(cs["score"] for cs in category_scores.values())

    if total_score >= 80:
        label = "Excellent"
    elif total_score >= 60:
        label = "Good"
    elif total_score >= 30:
        label = "Fair"
    else:
        label = "Poor"

    # --- Build actions ---
    actions = _build_actions(missing, company_website, pain_drivers, competitors, signal_count)

    # Cost estimate
    cost_estimate = round(BASE_COST - potential_savings, 2)

    return {
        "score": total_score,
        "effectiveness_label": label,
        "have": have,
        "missing": missing,
        "actions": actions,
        "category_scores": category_scores,
        "cost_estimate": cost_estimate,
        "potential_savings": round(potential_savings, 2),
    }


def _build_actions(
    missing: list[dict],
    company_website: str | None,
    pain_drivers: list[dict],
    competitors: list[dict],
    signal_count: int,
) -> list[dict[str, Any]]:
    """Build prioritized action list from missing items."""
    actions: list[dict[str, Any]] = []

    missing_items = {m["item"] for m in missing}

    if "Company name" in missing_items:
        actions.append({
            "action": "Set the company name",
            "impact": "Required — discovery cannot run without it",
            "how": "Update project settings or company info",
            "priority": 1,
        })

    if "Company website" in missing_items:
        actions.append({
            "action": "Set the company website",
            "impact": "Ensures correct company profile, saves $0.03",
            "how": "Update company info in project settings or ask the client",
            "priority": 2,
        })

    if "Known competitors" in missing_items:
        actions.append({
            "action": "Add at least one known competitor",
            "impact": "Profiles the right companies instead of guessing from search results",
            "how": "Add in BRD view or tell the assistant about competitors",
            "priority": 3,
        })

    if signal_count < 3:
        actions.append({
            "action": "Upload a discovery call recording",
            "impact": "Extracts pain points and competitor mentions for targeted searches",
            "how": "Drag and drop the recording into Sources",
            "priority": 4,
        })

    if "Pain point keywords" in missing_items and signal_count >= 1:
        actions.append({
            "action": "Run /run-foundation to extract pain points from signals",
            "impact": "Provides specific pain keywords for forum and review searches",
            "how": "Type /run-foundation in the assistant",
            "priority": 5,
        })

    if "Industry" in missing_items:
        actions.append({
            "action": "Set the industry",
            "impact": "Enables market trend and industry report searches",
            "how": "Update company info or project metadata",
            "priority": 6,
        })

    return sorted(actions, key=lambda a: a["priority"])
