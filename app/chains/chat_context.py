"""Smart context builder for chat assistant."""

from typing import Any, Dict
from uuid import UUID

from app.core.logging import get_logger
from app.core.state_snapshot import get_state_snapshot
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


async def build_smart_context(project_id: UUID, request: Any) -> Dict[str, Any]:
    """
    Build smart, focused context based on:
    - User's message intent
    - Current tab/focus
    - Recent activity

    Args:
        project_id: Project UUID
        request: Chat request with message and context

    Returns:
        Dictionary with relevant project context
    """
    supabase = get_supabase()

    try:
        # Get project basics
        project_response = supabase.table("projects").select("*").eq("id", str(project_id)).single().execute()
        project = project_response.data if project_response.data else {}

        # Get counts summary
        summary = await get_counts_summary(supabase, project_id)

        # Detect intent from message (returns dict with primary, confidence, entity_focus, etc.)
        intent_data = detect_intent(request.message)
        intent = intent_data["primary"]

        # Get state snapshot (500-token cached context)
        state_snapshot = get_state_snapshot(project_id)

        context = {
            "project": {
                "id": str(project_id),
                "name": project.get("name", "Unknown"),
                "prd_mode": project.get("prd_mode", "initial"),
                "baseline_ready": project.get("baseline_ready", False),
            },
            "state_snapshot": state_snapshot,  # 500-token context for agents
            "summary": summary,
            "intent": intent_data,  # Include full intent analysis
        }

        # Generate proactive suggestions
        suggestions = await generate_proactive_suggestions(project_id, context)
        if suggestions:
            context["suggestions"] = suggestions

        # Smart loading based on intent
        if intent in ["proposal", "proposals"]:
            # User asking about proposals
            context["needs_attention"] = await get_items_needing_attention(supabase, project_id)
            logger.info(f"Context includes proposals focus for intent: {intent}")

        elif intent in ["research", "evidence"]:
            # User asking about research
            context["research_available"] = True
            logger.info(f"Context includes research focus for intent: {intent}")

        elif intent in ["status", "summary", "overview", "analysis"]:
            # User wants overview or analysis
            context["needs_attention"] = await get_items_needing_attention(supabase, project_id)
            logger.info(f"Context includes status overview for intent: {intent}")

        # If user is focused on specific entity, load full details
        if request.context and request.context.get("focused_entity_id"):
            focused_entity = await load_focused_entity(
                supabase, request.context["focused_entity_type"], request.context["focused_entity_id"]
            )

            if focused_entity:
                context["focused_entity"] = {
                    "type": request.context["focused_entity_type"],
                    "id": request.context["focused_entity_id"],
                    "data": focused_entity,
                }
                logger.info(
                    f"Context includes focused entity: {request.context['focused_entity_type']} {request.context['focused_entity_id']}"
                )

        return context

    except Exception as e:
        logger.error(f"Error building context: {e}", exc_info=True)
        # Return minimal context on error
        return {
            "project": {"id": str(project_id), "name": "Unknown", "prd_mode": "initial", "baseline_ready": False},
            "summary": {},
        }


async def get_counts_summary(supabase: Any, project_id: UUID) -> Dict[str, int]:
    """
    Get summary counts for the project.

    Args:
        supabase: Supabase client
        project_id: Project UUID

    Returns:
        Dictionary with entity counts
    """
    try:
        # Get counts in parallel
        features_response = (
            supabase.table("features").select("id", count="exact").eq("project_id", str(project_id)).execute()
        )
        personas_response = (
            supabase.table("personas").select("id", count="exact").eq("project_id", str(project_id)).execute()
        )
        vp_response = supabase.table("vp_steps").select("id", count="exact").eq("project_id", str(project_id)).execute()

        # Get confirmation_items count
        confirmations_response = (
            supabase.table("confirmation_items")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .eq("status", "open")
            .execute()
        )

        # Get pending proposals count
        proposals_response = (
            supabase.table("batch_proposals")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .eq("status", "pending")
            .execute()
        )

        # Get business drivers count
        drivers_response = (
            supabase.table("business_drivers")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .execute()
        )

        # Get stakeholders count
        stakeholders_response = (
            supabase.table("stakeholders")
            .select("id", count="exact")
            .eq("project_id", str(project_id))
            .execute()
        )

        return {
            "features": features_response.count or 0,
            "personas": personas_response.count or 0,
            "vp_steps": vp_response.count or 0,
            "confirmations_open": confirmations_response.count or 0,
            "proposals_pending": proposals_response.count or 0,
            "business_drivers": drivers_response.count or 0,
            "stakeholders": stakeholders_response.count or 0,
        }

    except Exception as e:
        logger.error(f"Error getting counts summary: {e}", exc_info=True)
        return {}


async def get_items_needing_attention(supabase: Any, project_id: UUID) -> Dict[str, Any]:
    """
    Get items that need consultant attention.

    Args:
        supabase: Supabase client
        project_id: Project UUID

    Returns:
        Dictionary with items needing attention
    """
    try:
        # Get pending proposals that need review
        pending_proposals_response = (
            supabase.table("batch_proposals")
            .select("id, title, summary, total_changes")
            .eq("project_id", str(project_id))
            .eq("status", "pending")
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )

        # Get detailed client confirmations context
        client_confirmations = await get_client_confirmations_context(supabase, project_id)

        return {
            "pending_proposals": pending_proposals_response.data or [],
            "client_confirmations": client_confirmations,
        }

    except Exception as e:
        logger.error(f"Error getting items needing attention: {e}", exc_info=True)
        return {}


async def get_client_confirmations_context(supabase: Any, project_id: UUID) -> Dict[str, Any]:
    """
    Get detailed context about pending client confirmations.

    This provides the AI Assistant with rich context about what needs
    client input, grouped by theme, with recommendations for outreach.

    Args:
        supabase: Supabase client
        project_id: Project UUID

    Returns:
        Dictionary with confirmation context including counts, groupings,
        and recommended actions
    """
    try:
        # Get all open confirmation items
        confirmations_response = (
            supabase.table("confirmation_items")
            .select("*")
            .eq("project_id", str(project_id))
            .eq("status", "open")
            .order("priority", desc=False)  # high first
            .execute()
        )

        confirmations = confirmations_response.data or []

        if not confirmations:
            return {
                "count": 0,
                "needs_outreach": False,
                "items": [],
            }

        # Count by priority
        high_priority = sum(1 for c in confirmations if c.get("priority") == "high")
        medium_priority = sum(1 for c in confirmations if c.get("priority") == "medium")
        low_priority = sum(1 for c in confirmations if c.get("priority") == "low")

        # Count by suggested method
        needs_meeting = sum(1 for c in confirmations if c.get("suggested_method") == "meeting")
        can_email = sum(1 for c in confirmations if c.get("suggested_method") == "email")

        # Group by kind/category
        by_kind = {}
        for c in confirmations:
            kind = c.get("kind", "other")
            if kind not in by_kind:
                by_kind[kind] = []
            by_kind[kind].append({
                "id": c["id"],
                "title": c.get("title", "Untitled"),
                "ask": c.get("ask", ""),
                "priority": c.get("priority", "medium"),
                "suggested_method": c.get("suggested_method", "email"),
                "confidence": c.get("created_from", {}).get("confidence"),
            })

        # Calculate oldest item age
        oldest_days = 0
        if confirmations:
            from datetime import datetime, timezone
            oldest_created = min(c.get("created_at", "") for c in confirmations if c.get("created_at"))
            if oldest_created:
                try:
                    oldest_date = datetime.fromisoformat(oldest_created.replace("Z", "+00:00"))
                    oldest_days = (datetime.now(timezone.utc) - oldest_date).days
                except:
                    pass

        # Generate recommendation
        if needs_meeting >= 3 or high_priority >= 2:
            recommendation = f"Schedule a client call to cover {needs_meeting} complex items. {can_email} simple items can go via email."
        elif len(confirmations) <= 3 and needs_meeting == 0:
            recommendation = f"Send a quick email to resolve {len(confirmations)} simple questions."
        else:
            recommendation = f"{needs_meeting} items need discussion (meeting recommended), {can_email} can be handled via email."

        return {
            "count": len(confirmations),
            "high_priority": high_priority,
            "medium_priority": medium_priority,
            "low_priority": low_priority,
            "needs_meeting": needs_meeting,
            "can_email": can_email,
            "oldest_days": oldest_days,
            "by_kind": by_kind,
            "recommendation": recommendation,
            "needs_outreach": len(confirmations) > 0,
            "items": [
                {
                    "id": c["id"],
                    "title": c.get("title"),
                    "ask": c.get("ask"),
                    "priority": c.get("priority"),
                    "suggested_method": c.get("suggested_method"),
                }
                for c in confirmations[:10]  # Limit to 10 most important
            ],
        }

    except Exception as e:
        logger.error(f"Error getting client confirmations context: {e}", exc_info=True)
        return {"count": 0, "needs_outreach": False, "items": []}


async def load_focused_entity(supabase: Any, entity_type: str, entity_id: str) -> Dict[str, Any] | None:
    """
    Load full details of the focused entity.

    Args:
        supabase: Supabase client
        entity_type: Type of entity (vp_step, insight, feature, persona, etc.)
        entity_id: Entity UUID

    Returns:
        Entity data or None if not found
    """
    try:
        # Map entity types to table names
        table_map = {
            "vp_step": "vp_steps",
            "insight": "insights",
            "feature": "features",
            "persona": "personas",
            "confirmation": "confirmations",
        }

        table_name = table_map.get(entity_type)

        if not table_name:
            logger.warning(f"Unknown entity type: {entity_type}")
            return None

        # Fetch entity
        response = supabase.table(table_name).select("*").eq("id", entity_id).single().execute()

        return response.data if response.data else None

    except Exception as e:
        logger.error(f"Error loading focused entity {entity_type}:{entity_id}: {e}", exc_info=True)
        return None


async def assess_prototype_readiness(project_id: UUID) -> Dict[str, Any]:
    """
    Assess whether a project is ready for prototype implementation.

    IMPORTANT: Readiness is based on CONFIRMED entities only.
    - confirmed_client: Direct client input (emails, transcripts, files)
    - confirmed_consultant: Consultant-validated (uploads, manual confirmation)
    - ai_generated: Not counted toward readiness (60% threshold)

    Analyzes (confirmed entities only):
    - Features: 40% - MVP coverage, confirmation status, confidence levels
    - Value Path: 35% - Step coverage and detail level
    - Personas: 25% - Existence and completeness

    NOTE: PRD sections are no longer used in scoring.

    Args:
        project_id: Project UUID

    Returns:
        Dictionary with score, blockers, warnings, recommendations, breakdown, and counts
    """
    supabase = get_supabase()

    # Confirmation statuses that count as "confirmed"
    CONFIRMED_STATUSES = {"confirmed_client", "confirmed_consultant"}

    def is_confirmed(entity: dict) -> bool:
        """Check if entity has a confirmed status."""
        # Check confirmation_status first, then fall back to status
        status = entity.get("confirmation_status") or entity.get("status", "ai_generated")
        return status in CONFIRMED_STATUSES

    try:
        # Load all project entities (no PRD sections - deprecated)
        features_response = supabase.table("features").select("*").eq("project_id", str(project_id)).execute()
        personas_response = supabase.table("personas").select("*").eq("project_id", str(project_id)).execute()
        vp_response = supabase.table("vp_steps").select("*").eq("project_id", str(project_id)).execute()

        features = features_response.data or []
        personas = personas_response.data or []
        vp_steps = vp_response.data or []

        # Filter to confirmed entities (for readiness scoring)
        confirmed_features = [f for f in features if is_confirmed(f)]
        confirmed_personas = [p for p in personas if is_confirmed(p)]
        confirmed_vp_steps = [v for v in vp_steps if is_confirmed(v)]

        # Assess each category using CONFIRMED entities only
        features_assessment = _assess_features(confirmed_features, total_count=len(features))
        personas_assessment = _assess_personas(confirmed_personas, total_count=len(personas))
        vp_assessment = _assess_value_path(confirmed_vp_steps, total_count=len(vp_steps))

        # Calculate overall score (weighted average - matches baseline_scoring.py)
        # Features: 40%, VP Steps: 35%, Personas: 25%
        overall_score = int(
            features_assessment["score"] * 0.4 +
            vp_assessment["score"] * 0.35 +
            personas_assessment["score"] * 0.25
        )

        # Collect all blockers and warnings
        blockers = []
        warnings = []
        recommendations = []

        for assessment in [features_assessment, personas_assessment, vp_assessment]:
            blockers.extend(assessment.get("blockers", []))
            warnings.extend(assessment.get("warnings", []))
            recommendations.extend(assessment.get("recommendations", []))

        return {
            "score": overall_score,
            "blockers": blockers,
            "warnings": warnings,
            "recommendations": recommendations,
            "breakdown": {
                "features": features_assessment,
                "personas": personas_assessment,
                "vp_coverage": vp_assessment,
            },
            # Include counts for frontend display (confirmed vs total)
            "counts": {
                "features": len(features),
                "features_confirmed": len(confirmed_features),
                "personas": len(personas),
                "personas_confirmed": len(confirmed_personas),
                "vp_steps": len(vp_steps),
                "vp_steps_confirmed": len(confirmed_vp_steps),
            }
        }

    except Exception as e:
        logger.error(f"Error assessing prototype readiness: {e}", exc_info=True)
        return {
            "score": 0,
            "blockers": ["Error assessing readiness"],
            "warnings": [],
            "recommendations": ["Please try again"],
            "breakdown": {},
            "counts": {}
        }


def _assess_features(features: list, total_count: int = 0) -> Dict[str, Any]:
    """
    Assess features readiness.

    Args:
        features: List of CONFIRMED features only
        total_count: Total features including unconfirmed (for display)
    """
    # Use total_count for display messages if provided
    display_total = total_count if total_count > 0 else len(features)

    if not features:
        if display_total > 0:
            return {
                "score": 0,
                "blockers": [f"No confirmed features (0/{display_total} confirmed)"],
                "warnings": [],
                "recommendations": ["Confirm features from client signals or consultant review"],
                "issues": [f"0/{display_total} features confirmed"]
            }
        return {
            "score": 0,
            "blockers": ["No features defined"],
            "warnings": [],
            "recommendations": ["Add MVP features to get started"],
            "issues": ["No features defined"]
        }

    mvp_features = [f for f in features if f.get("is_mvp")]
    high_confidence = [f for f in features if f.get("confidence") == "high"]

    # Scoring based on CONFIRMED features
    score = 0
    if mvp_features:
        score += 30
    if len(mvp_features) >= 3:
        score += 20
    if len(features) >= 3:  # At least 3 confirmed features
        score += 25
    if len(high_confidence) >= len(mvp_features) * 0.5:
        score += 25

    blockers = []
    warnings = []
    recommendations = []
    issues = []

    if not mvp_features:
        blockers.append("No confirmed MVP features marked")
        recommendations.append("Mark critical features as MVP")
    elif len(mvp_features) < 3:
        warnings.append(f"Only {len(mvp_features)} confirmed MVP features (recommend 3-7)")
        recommendations.append("Consider adding more MVP features")

    if len(features) < 3:
        warnings.append(f"Only {len(features)}/{display_total} features confirmed (need 3+)")
        recommendations.append("Confirm more features from signals")

    if len(high_confidence) < len(mvp_features) * 0.3:
        warnings.append("Low confidence in MVP features")
        recommendations.append("Gather more research to increase confidence")

    return {
        "score": score,
        "blockers": blockers,
        "warnings": warnings,
        "recommendations": recommendations,
        "issues": issues,
        "confirmed": len(features),
        "total": display_total,
    }


def _assess_personas(personas: list, total_count: int = 0) -> Dict[str, Any]:
    """
    Assess personas readiness.

    Args:
        personas: List of CONFIRMED personas only
        total_count: Total personas including unconfirmed (for display)
    """
    display_total = total_count if total_count > 0 else len(personas)

    if not personas:
        if display_total > 0:
            return {
                "score": 0,
                "blockers": [f"No confirmed personas (0/{display_total} confirmed)"],
                "warnings": [],
                "recommendations": ["Confirm personas from client signals or consultant review"],
                "issues": [f"0/{display_total} personas confirmed"]
            }
        return {
            "score": 0,
            "blockers": ["No personas defined"],
            "warnings": [],
            "recommendations": ["Define at least 1 primary persona"],
            "issues": ["No personas defined"]
        }

    # Check completeness
    complete_personas = []
    for persona in personas:
        required_fields = ["name", "role", "goals", "pain_points"]
        if all(persona.get(field) for field in required_fields):
            complete_personas.append(persona)

    score = min(100, len(complete_personas) * 50)  # 1 persona = 50pts, 2+ = 100pts

    blockers = []
    warnings = []
    recommendations = []
    issues = []

    if len(personas) == 1:
        warnings.append(f"Only 1 confirmed persona ({len(personas)}/{display_total} confirmed)")
        recommendations.append("Consider adding a secondary persona")

    if len(personas) < 2 and display_total >= 2:
        warnings.append(f"Only {len(personas)}/{display_total} personas confirmed (need 2+)")
        recommendations.append("Confirm more personas from signals")

    incomplete = len(personas) - len(complete_personas)
    if incomplete > 0:
        warnings.append(f"{incomplete} incomplete persona(s)")
        recommendations.append("Fill in goals and pain points for all personas")

    return {
        "score": score,
        "blockers": blockers,
        "warnings": warnings,
        "recommendations": recommendations,
        "issues": issues,
        "confirmed": len(personas),
        "total": display_total,
    }


def _assess_value_path(vp_steps: list, total_count: int = 0) -> Dict[str, Any]:
    """
    Assess Value Path readiness.

    Args:
        vp_steps: List of CONFIRMED VP steps only
        total_count: Total VP steps including unconfirmed (for display)
    """
    display_total = total_count if total_count > 0 else len(vp_steps)

    if not vp_steps:
        if display_total > 0:
            return {
                "score": 0,
                "blockers": [f"No confirmed Value Path steps (0/{display_total} confirmed)"],
                "warnings": [],
                "recommendations": ["Confirm VP steps from client signals or consultant review"],
                "issues": [f"0/{display_total} VP steps confirmed"]
            }
        return {
            "score": 0,
            "blockers": ["No Value Path steps defined"],
            "warnings": [],
            "recommendations": ["Define the happy path with 3-7 steps"],
            "issues": ["No Value Path steps"]
        }

    # Check for detail completeness
    detailed_steps = []
    for step in vp_steps:
        has_description = bool(step.get("description"))
        has_ui_overview = bool(step.get("ui_overview"))
        has_value_created = bool(step.get("value_created"))

        if has_description and (has_ui_overview or has_value_created):
            detailed_steps.append(step)

    score = 0
    if len(vp_steps) >= 3:
        score += 40
    if len(vp_steps) >= 5:
        score += 20
    if len(detailed_steps) >= len(vp_steps) * 0.7:
        score += 40

    blockers = []
    warnings = []
    recommendations = []
    issues = []

    if len(vp_steps) < 3:
        blockers.append(f"Only {len(vp_steps)}/{display_total} confirmed VP steps (need 3+)")
        recommendations.append("Confirm more steps or add new ones")
    elif len(vp_steps) > 10:
        warnings.append(f"{len(vp_steps)} confirmed steps may be too granular for MVP")
        recommendations.append("Consider consolidating to 3-7 key steps")

    if len(detailed_steps) < len(vp_steps) * 0.5:
        warnings.append("Many confirmed steps lack detail")
        recommendations.append("Add UI overview and value created for each step")

    return {
        "score": score,
        "blockers": blockers,
        "warnings": warnings,
        "recommendations": recommendations,
        "issues": issues,
        "confirmed": len(vp_steps),
        "total": display_total,
    }


def _assess_evidence(features: list, vp_steps: list, signal_count: int) -> Dict[str, Any]:
    """Assess research evidence backing."""
    if signal_count == 0:
        return {
            "score": 0,
            "blockers": [],
            "warnings": ["No research uploaded"],
            "recommendations": ["Upload research to strengthen decisions"],
            "issues": ["No research signals"]
        }

    # Check evidence linking
    features_with_evidence = sum(1 for f in features if f.get("evidence") and len(f.get("evidence", [])) > 0)
    vp_with_evidence = sum(1 for v in vp_steps if v.get("evidence") and len(v.get("evidence", [])) > 0)

    total_entities = len(features) + len(vp_steps)
    total_with_evidence = features_with_evidence + vp_with_evidence

    if total_entities == 0:
        evidence_ratio = 0
    else:
        evidence_ratio = total_with_evidence / total_entities

    score = int(min(100, signal_count * 2 + evidence_ratio * 60))

    blockers = []
    warnings = []
    recommendations = []
    issues = []

    if signal_count < 5:
        warnings.append(f"Only {signal_count} research chunks (recommend 10+)")
        recommendations.append("Upload more research documents")

    if evidence_ratio < 0.3:
        warnings.append(f"Only {int(evidence_ratio * 100)}% of decisions have evidence")
        recommendations.append("Link research to features and VP steps")

    return {
        "score": score,
        "blockers": blockers,
        "warnings": warnings,
        "recommendations": recommendations,
        "issues": issues
    }


async def generate_proactive_suggestions(project_id: UUID, context: dict, recent_action: str | None = None) -> list[str]:
    """
    Generate proactive suggestions based on project state and recent actions.

    Args:
        project_id: Project UUID
        context: Current context dict with summary, intent, etc.
        recent_action: Recent action taken (e.g., "applied_proposal", "created_features")

    Returns:
        List of suggestion strings
    """
    suggestions = []
    summary = context.get("summary", {})

    try:
        # After applying proposals or changes
        if recent_action in ["applied_proposal", "created_features", "updated_features"]:
            # Check if readiness improved
            assessment = await assess_prototype_readiness(project_id)
            score = assessment["score"]

            if score >= 80:
                suggestions.append(f"🎉 Project readiness is now at {score}%! You're ready to start prototyping.")
            elif score >= 60:
                suggestions.append(f"📈 Readiness improved to {score}%. Address {len(assessment['warnings'])} warnings to reach 80%+")

            # Suggest related improvements
            if assessment.get("warnings"):
                top_warning = assessment["warnings"][0]
                if "evidence" in top_warning.lower():
                    suggestions.append("💡 Consider linking research evidence to strengthen your decisions")
                elif "persona" in top_warning.lower():
                    suggestions.append("💡 Add more personas to better understand your users")
                elif "confidence" in top_warning.lower():
                    suggestions.append("💡 Gather more research to increase feature confidence")

        # Low feature count
        if summary.get("features", 0) == 0:
            suggestions.append("🚀 Start by proposing MVP features - I can help generate them from your requirements")
        elif summary.get("features", 0) < 3:
            suggestions.append("📝 Consider adding more features to reach the recommended 3-7 MVP features")

        # Missing personas
        if summary.get("personas", 0) == 0:
            suggestions.append("👥 Define at least one persona to guide feature decisions")

        # Incomplete Value Path
        vp_count = summary.get("vp_steps", 0)
        if vp_count == 0:
            suggestions.append("🛤️ Define your Value Path (happy path) with 3-7 key steps")
        elif vp_count < 3:
            suggestions.append(f"🛤️ Value Path has {vp_count} steps - consider adding more to cover the full journey")

        # Pending proposals to review
        proposals_pending = summary.get("proposals_pending", 0)
        if proposals_pending > 0:
            suggestions.append(f"📋 {proposals_pending} proposal{'s' if proposals_pending > 1 else ''} pending review - check Overview tab")

        # Open confirmations - provide richer suggestions
        confirmations = summary.get("confirmations_open", 0)
        if confirmations > 0:
            # Try to get detailed context for better suggestion
            try:
                supabase = get_supabase()
                conf_context = await get_client_confirmations_context(supabase, project_id)
                if conf_context.get("recommendation"):
                    suggestions.append(f"📋 {confirmations} items need client input: {conf_context['recommendation']}")
                elif conf_context.get("high_priority", 0) > 0:
                    suggestions.append(f"⚠️ {conf_context['high_priority']} high-priority items need client confirmation")
                else:
                    suggestions.append(f"❓ {confirmations} open confirmations need client input")
            except:
                suggestions.append(f"❓ {confirmations} open confirmations need client input")

        # Intent-based suggestions
        intent_data = context.get("intent", {})
        if intent_data.get("primary") == "proposal" and intent_data.get("batch_likely"):
            suggestions.append("💡 I can generate batch proposals with research evidence - just describe what you need")

        # Limit to top 3 most relevant suggestions
        return suggestions[:3]

    except Exception as e:
        logger.error(f"Error generating proactive suggestions: {e}", exc_info=True)
        return []


def detect_intent(message: str) -> dict:
    """
    Enhanced keyword-based intent detection with confidence and context.

    Args:
        message: User's message

    Returns:
        Dictionary with:
        - primary: Intent category (insights, research, status, prd, proposal, analysis, query)
        - confidence: Confidence score (0.0-1.0)
        - entity_focus: Entity type focus if detected (feature, prd, vp, persona, research, None)
        - batch_likely: Whether batch operation is likely
        - keywords: Matched keywords
    """
    message_lower = message.lower()
    matched_keywords = []
    entity_focus = None
    batch_likely = False

    # Define keyword patterns with confidence weights
    patterns = {
        "proposal": {
            "keywords": ["add", "create", "new", "propose", "suggest", "generate", "batch", "change"],
            "confidence": 0.9,
        },
        "research": {
            "keywords": ["research", "evidence", "competitor", "market", "study", "data", "finding", "signal"],
            "confidence": 0.85,
        },
        "status": {
            "keywords": ["status", "summary", "overview", "what's", "show me", "attention", "needs", "ready"],
            "confidence": 0.8,
        },
        "analysis": {
            "keywords": ["analyze", "assess", "evaluate", "review", "check", "readiness", "gaps", "issue", "problem"],
            "confidence": 0.8,
        },
        "features": {
            "keywords": ["feature", "capability", "functionality", "mvp"],
            "confidence": 0.75,
        },
        "query": {
            "keywords": ["what", "how", "why", "when", "where", "explain", "tell me"],
            "confidence": 0.6,
        },
    }

    # Detect entity focus
    if any(word in message_lower for word in ["feature", "features", "functionality"]):
        entity_focus = "feature"
        matched_keywords.append("features")
    if any(word in message_lower for word in ["prd", "requirement", "section"]):
        entity_focus = "prd"
        matched_keywords.append("prd")
    if any(word in message_lower for word in ["value path", "vp", "step", "journey", "happy path"]):
        entity_focus = "vp"
        matched_keywords.append("value path")
    if any(word in message_lower for word in ["persona", "user", "customer"]):
        entity_focus = "persona"
        matched_keywords.append("personas")
    if any(word in message_lower for word in ["research", "evidence", "signal"]):
        entity_focus = "research"
        matched_keywords.append("research")

    # Detect batch operations
    batch_indicators = ["multiple", "several", "batch", "all", "many", "bunch of"]
    if any(indicator in message_lower for indicator in batch_indicators):
        batch_likely = True
        matched_keywords.extend([ind for ind in batch_indicators if ind in message_lower])

    # Score each intent pattern
    intent_scores = {}
    for intent_name, pattern in patterns.items():
        matches = [kw for kw in pattern["keywords"] if kw in message_lower]
        if matches:
            # Base confidence from pattern + boost for multiple keyword matches
            score = pattern["confidence"] + (len(matches) - 1) * 0.05
            intent_scores[intent_name] = min(1.0, score)
            matched_keywords.extend(matches)

    # Determine primary intent
    if intent_scores:
        primary = max(intent_scores, key=intent_scores.get)
        confidence = intent_scores[primary]
    else:
        primary = "general"
        confidence = 0.5

    # Adjust confidence based on message length and clarity
    word_count = len(message.split())
    if word_count < 3:
        confidence *= 0.7  # Short messages are less clear
    elif word_count > 20:
        confidence *= 0.9  # Very long messages may be less focused

    return {
        "primary": primary,
        "confidence": round(confidence, 2),
        "entity_focus": entity_focus,
        "batch_likely": batch_likely,
        "keywords": list(set(matched_keywords)),  # Remove duplicates
    }
