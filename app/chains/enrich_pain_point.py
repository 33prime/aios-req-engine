"""
Pain Point Enrichment Chain

Extracts detailed pain analysis for pain business drivers:
- Severity (critical, high, medium, low)
- Frequency (constant, daily, weekly, monthly, rare)
- Affected users
- Business impact (quantified)
- Current workaround

This chain helps prioritize pain points and understand their true cost.
"""

from typing import Any, Literal
from uuid import UUID

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.business_drivers import get_business_driver, update_business_driver, list_business_drivers
from app.db.signals import list_project_signals, list_signal_chunks

logger = get_logger(__name__)


class PainPointEnrichment(BaseModel):
    """Enriched pain point data extracted from signals."""

    severity: Literal["critical", "high", "medium", "low"] | None = Field(
        None,
        description='Impact severity: critical (blocking), high (major friction), medium (inconvenience), low (minor)',
    )
    frequency: Literal["constant", "daily", "weekly", "monthly", "rare"] | None = Field(
        None,
        description='How often this pain occurs: constant (always), daily, weekly, monthly, rare (< monthly)',
    )
    affected_users: str | None = Field(
        None,
        description='Who experiences this pain (e.g., "All warehouse staff", "10% of checkout customers", "Enterprise clients only")',
    )
    business_impact: str | None = Field(
        None,
        description='Quantified business impact (e.g., "~$50K/month in lost sales", "2 hours/day of manual work", "15% cart abandonment")',
    )
    current_workaround: str | None = Field(
        None,
        description='How users currently work around this pain (e.g., "Manual Excel exports via email", "Call support for each order", "None - feature gap")',
    )
    vision_alignment: Literal["high", "medium", "low", "unrelated"] | None = Field(
        None,
        description='How strongly this pain relates to the project vision: high (directly addresses core vision), medium (supports indirectly), low (tangential), unrelated (no connection)',
    )
    related_actor_names: list[str] = Field(
        default_factory=list,
        description='Names of personas/roles most affected by this pain. Use exact names from the provided persona list.',
    )
    related_workflow_labels: list[str] = Field(
        default_factory=list,
        description='Labels of workflow steps where this pain occurs. Use exact labels from the provided workflow list.',
    )
    should_merge_with: str | None = Field(
        None,
        description='If this pain point is very similar/duplicate to another existing pain, provide the ID of the pain it should be merged with. Only suggest merging if they describe the exact same problem.',
    )
    confidence: float = Field(
        0.0,
        description="Confidence in this enrichment (0.0-1.0)",
    )
    reasoning: str | None = Field(
        None,
        description="Brief explanation of how these values were determined",
    )


async def enrich_pain_point(
    driver_id: UUID,
    project_id: UUID,
    depth: str = "standard",
) -> dict[str, Any]:
    """
    Enrich a pain point business driver with detailed analysis.

    Args:
        driver_id: Business driver UUID (must be driver_type='pain')
        project_id: Project UUID
        depth: Enrichment depth ('quick', 'standard', 'deep')

    Returns:
        Dict with:
        - success: bool
        - enrichment: PainPointEnrichment | None
        - driver_id: UUID
        - updated_fields: list of field names that were updated
        - error: str | None
    """
    settings = get_settings()

    result = {
        "success": False,
        "enrichment": None,
        "driver_id": str(driver_id),
        "updated_fields": [],
        "error": None,
    }

    try:
        # Get the pain driver
        driver = get_business_driver(driver_id)
        if not driver:
            result["error"] = f"Business driver {driver_id} not found"
            return result

        if driver.get("driver_type") != "pain":
            result["error"] = f"Driver is type '{driver.get('driver_type')}', not 'pain'"
            return result

        description = driver.get("description", "")
        evidence = driver.get("evidence", []) or []
        source_signal_ids = driver.get("source_signal_ids", []) or []

        logger.info(f"Enriching pain point '{description[:50]}' for project {project_id}")

        # Get existing pain points for merge detection
        existing_pains = list_business_drivers(project_id, driver_type="pain", limit=50)
        # Exclude the current driver
        other_pains = [pain for pain in existing_pains if pain.get("id") != str(driver_id)]

        # Gather context from signals
        signal_context = []

        # 1. Get evidence signals
        for evidence_item in evidence[:5]:
            signal_id = evidence_item.get("signal_id")
            text = evidence_item.get("text", "")

            if text:
                signal_context.append({
                    "source": f"Evidence from signal {str(signal_id)[:8]}",
                    "text": text[:1000],
                })

        # 2. Get source signals
        for signal_id_str in source_signal_ids[:3]:
            try:
                signal_id = UUID(signal_id_str)
                chunks = list_signal_chunks(signal_id)
                if chunks:
                    chunk_text = chunks[0].get("content", "")[:1500]
                    signal_context.append({
                        "source": f"Source signal {str(signal_id)[:8]}",
                        "text": chunk_text,
                    })
            except Exception as e:
                logger.warning(f"Failed to load signal {signal_id_str}: {e}")

        # 3. If depth is 'deep', get additional project signals
        if depth == "deep":
            try:
                signal_response = list_project_signals(project_id, limit=10)
                signals = signal_response.get("signals", [])[:5]

                for signal in signals:
                    content = signal.get("content", "")[:1000]
                    if content:
                        signal_context.append({
                            "source": f"Project signal: {signal.get('title', 'Untitled')[:30]}",
                            "text": content,
                        })
            except Exception as e:
                logger.warning(f"Failed to load project signals: {e}")

        # Build context summary
        if not signal_context:
            signal_context_str = "No signal context available."
        else:
            signal_context_str = "\n\n".join([
                f"### {ctx['source']}\n{ctx['text']}"
                for ctx in signal_context[:8]
            ])

        # Build existing pains summary for merge detection
        existing_pains_str = ""
        if other_pains:
            existing_pains_str = "\n**Existing Pain Points in this project:**\n"
            for pain in other_pains[:10]:  # Limit to 10 for context size
                pain_id = pain.get("id", "")
                pain_desc = pain.get("description", "")
                pain_severity = pain.get("severity", "")
                pain_impact = pain.get("business_impact", "")
                existing_pains_str += f"- ID: {pain_id}, Description: {pain_desc}"
                if pain_severity or pain_impact:
                    existing_pains_str += f" (Severity: {pain_severity}, Impact: {pain_impact})"
                existing_pains_str += "\n"
        else:
            existing_pains_str = "\n**No other pain points exist yet.**\n"

        # Gather project context for relationship assessment
        from app.db.supabase_client import get_supabase as _get_supabase
        _supabase = _get_supabase()

        project_vision = ""
        try:
            proj = _supabase.table("projects").select("vision").eq("id", str(project_id)).maybe_single().execute()
            if proj and proj.data:
                project_vision = proj.data.get("vision") or ""
        except Exception:
            pass

        persona_names_list: list[str] = []
        try:
            personas_res = _supabase.table("personas").select("name").eq("project_id", str(project_id)).execute()
            persona_names_list = [p["name"] for p in (personas_res.data or [])]
        except Exception:
            pass

        workflow_labels_list: list[str] = []
        try:
            vp_res = _supabase.table("vp_steps").select("label").eq("project_id", str(project_id)).order("step_index").execute()
            workflow_labels_list = [s["label"] for s in (vp_res.data or []) if s.get("label")]
        except Exception:
            pass

        vision_section = f'\n**Project Vision:** "{project_vision}"\n' if project_vision else ""
        personas_section = f"\n**Known Personas:** {', '.join(persona_names_list)}\n" if persona_names_list else ""
        workflows_section = f"\n**Known Workflow Steps:** {', '.join(workflow_labels_list)}\n" if workflow_labels_list else ""

        # Build the enrichment prompt
        parser = PydanticOutputParser(pydantic_object=PainPointEnrichment)

        system_prompt = f"""You are a pain point analysis specialist. Your job is to assess the severity and impact of user/business pain points, assess their relationship to the project, and detect duplicates.

Given a pain point description and related context, extract:

1. **Severity**: How impactful is this pain?
   - critical: Blocking users, preventing core functionality, causing major revenue loss
   - high: Significant friction, major inconvenience, clear competitive disadvantage
   - medium: Noticeable inconvenience, affects some users, workarounds exist
   - low: Minor annoyance, edge case, cosmetic issue

2. **Frequency**: How often does this pain occur?
   - constant: Always present, every interaction
   - daily: Multiple times per day or every day
   - weekly: Several times per week
   - monthly: A few times per month
   - rare: Less than monthly

3. **Affected users**: Who experiences this?
   - Be specific (e.g., "All warehouse staff", "10% of customers in checkout", "Enterprise clients only")
   - Include scale if mentioned (e.g., "200+ daily active users")

4. **Business impact**: Quantified cost/impact
   - Financial: "~$50K/month in lost sales", "$5K/year in manual labor"
   - Time: "2 hours/day of manual work", "30 minutes per order"
   - Metrics: "15% cart abandonment", "20% support ticket volume"
   - Use estimates with ~ if not exact

5. **Current workaround**: How do users cope today?
   - Be specific about the workaround process
   - If no workaround exists, state "None - feature gap" or "None - users give up"

6. **Vision alignment**: Given the project vision, how strongly does this pain relate to the vision?
   - high: Directly addresses the core vision
   - medium: Supports the vision indirectly
   - low: Tangential connection
   - unrelated: No clear connection
   - Leave null if no vision is provided

7. **Related actors**: Which personas/roles are most affected? List exact names from the provided persona list.

8. **Related workflows**: Which workflow steps does this pain occur in? List exact labels from the provided workflow list.

**CRITICAL - Duplicate Detection:**
- Review the list of existing pain points carefully
- If this pain describes the EXACT SAME problem as an existing pain (same user frustration, same root cause), set `should_merge_with` to the ID of that existing pain
- Only suggest merging if they are truly duplicates
- Similar but distinct pains (e.g., "slow checkout" vs "confusing checkout") should NOT be merged

**Important**:
- Only extract values explicitly mentioned or strongly implied
- If unclear, leave as null
- Be honest about severity - not everything is "critical"
- Quantify impact whenever possible
- Set confidence based on evidence quality

{parser.get_format_instructions()}"""

        user_prompt = f"""**Pain Point to Enrich:**
{description}
{existing_pains_str}
{vision_section}{personas_section}{workflows_section}
**Signal Context:**
{signal_context_str}

**Task:**
Extract pain point enrichment details from the above context. Review existing pains and suggest merging if this is a duplicate. Be objective in assessing severity and frequency. Assess vision alignment and identify related actors/workflows."""

        # Call LLM with Claude Sonnet 4
        model = ChatAnthropic(
            model="claude-sonnet-4-6",
            temperature=0.1,
            api_key=settings.ANTHROPIC_API_KEY,
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        logger.debug(f"Calling Claude Sonnet 4 for pain point enrichment (depth={depth})")
        response = await model.ainvoke(messages)
        enrichment = parser.parse(response.content)

        logger.info(
            f"Pain point enrichment complete: severity={enrichment.severity}, "
            f"frequency={enrichment.frequency}, confidence={enrichment.confidence}"
        )

        # Update the driver with enrichment data
        updates: dict[str, Any] = {}
        updated_fields = []

        if enrichment.severity and not driver.get("severity"):
            updates["severity"] = enrichment.severity
            updated_fields.append("severity")

        if enrichment.frequency and not driver.get("frequency"):
            updates["frequency"] = enrichment.frequency
            updated_fields.append("frequency")

        if enrichment.affected_users and not driver.get("affected_users"):
            updates["affected_users"] = enrichment.affected_users
            updated_fields.append("affected_users")

        if enrichment.business_impact and not driver.get("business_impact"):
            updates["business_impact"] = enrichment.business_impact
            updated_fields.append("business_impact")

        if enrichment.current_workaround and not driver.get("current_workaround"):
            updates["current_workaround"] = enrichment.current_workaround
            updated_fields.append("current_workaround")

        if enrichment.vision_alignment:
            updates["vision_alignment"] = enrichment.vision_alignment
            updated_fields.append("vision_alignment")

        # Resolve actor names → persona IDs and merge with existing
        if enrichment.related_actor_names and persona_names_list:
            from app.core.similarity import SimilarityMatcher
            persona_matcher = SimilarityMatcher(entity_type="persona")
            personas_data = _supabase.table("personas").select("id, name").eq("project_id", str(project_id)).execute().data or []
            existing_pids = list(driver.get("linked_persona_ids") or [])
            for actor_name in enrichment.related_actor_names:
                match = persona_matcher.find_best_match(actor_name, personas_data, "name", "id")
                if match.is_match and match.matched_item:
                    pid = match.matched_item["id"]
                    if pid not in existing_pids:
                        existing_pids.append(pid)
            if existing_pids:
                updates["linked_persona_ids"] = existing_pids
                updated_fields.append("linked_persona_ids")

        # Resolve workflow labels → vp_step IDs and merge
        if enrichment.related_workflow_labels and workflow_labels_list:
            from app.core.similarity import SimilarityMatcher
            wf_matcher = SimilarityMatcher(entity_type="feature")
            steps_data = _supabase.table("vp_steps").select("id, label").eq("project_id", str(project_id)).execute().data or []
            existing_vids = list(driver.get("linked_vp_step_ids") or [])
            for wf_label in enrichment.related_workflow_labels:
                match = wf_matcher.find_best_match(wf_label, steps_data, "label", "id")
                if match.is_match and match.matched_item:
                    vid = match.matched_item["id"]
                    if vid not in existing_vids:
                        existing_vids.append(vid)
            if existing_vids:
                updates["linked_vp_step_ids"] = existing_vids
                updated_fields.append("linked_vp_step_ids")

        if updates:
            updates["enrichment_status"] = "enriched"
            updates["enrichment_attempted_at"] = "now()"
            current_version = driver.get("version", 1)
            updates["version"] = current_version + 1

            update_business_driver(driver_id, project_id, **updates)

            logger.info(f"Updated pain driver with {len(updated_fields)} enriched fields: {updated_fields}")

        result["success"] = True
        result["enrichment"] = enrichment.model_dump()
        result["updated_fields"] = updated_fields

        return result

    except Exception as e:
        error_msg = f"Pain point enrichment failed: {str(e)}"
        result["error"] = error_msg
        logger.error(error_msg, exc_info=True)

        try:
            update_business_driver(
                driver_id,
                project_id,
                enrichment_status="failed",
                enrichment_error=error_msg[:500],
                enrichment_attempted_at="now()",
            )
        except Exception:
            pass

        return result
