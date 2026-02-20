"""API endpoints for stakeholders management."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Path, Query
from pydantic import BaseModel, Field, field_validator

from app.core.logging import get_logger
from app.db import stakeholders as stakeholders_db

logger = get_logger(__name__)

router = APIRouter(prefix="/projects/{project_id}/stakeholders")


# ============================================================================
# Pydantic Models
# ============================================================================


class StakeholderCreate(BaseModel):
    """Request body for creating a stakeholder."""

    name: str = Field(..., min_length=1, description="Stakeholder name")
    first_name: str | None = Field(None, description="First name (auto-parsed from name if not provided)")
    last_name: str | None = Field(None, description="Last name (auto-parsed from name if not provided)")
    role: str | None = Field(None, description="Job title/role")
    email: str | None = Field(None, description="Email address")
    phone: str | None = Field(None, description="Phone number")
    organization: str | None = Field(None, description="Company/department")
    stakeholder_type: str = Field("influencer", description="Type: champion, sponsor, blocker, influencer, end_user")
    influence_level: str = Field("medium", description="Influence level: high, medium, low")
    domain_expertise: list[str] = Field(default_factory=list, description="Areas of expertise")
    priorities: list[str] = Field(default_factory=list, description="What matters to them")
    concerns: list[str] = Field(default_factory=list, description="Their worries/objections")
    notes: str | None = Field(None, description="Additional notes")


class StakeholderUpdate(BaseModel):
    """Request body for updating a stakeholder."""

    name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    role: str | None = None
    email: str | None = None
    phone: str | None = None
    organization: str | None = None
    stakeholder_type: str | None = None
    influence_level: str | None = None
    domain_expertise: list[str] | None = None
    priorities: list[str] | None = None
    concerns: list[str] | None = None
    notes: str | None = None
    is_primary_contact: bool | None = None


def _coerce_str_to_list(v: list[str] | str | None) -> list[str] | None:
    """Coerce JSONB string values to single-item lists. Some older stakeholders
    have priorities/concerns stored as plain strings instead of arrays."""
    if isinstance(v, str):
        return [v]
    return v


class StakeholderOut(BaseModel):
    """Response model for a stakeholder."""

    id: UUID
    project_id: UUID
    name: str
    first_name: str | None = None
    last_name: str | None = None
    role: str | None = None
    project_name: str | None = None
    email: str | None = None
    phone: str | None = None
    organization: str | None = None
    stakeholder_type: str | None = None
    influence_level: str | None = None
    domain_expertise: list[str] | None = None
    topic_mentions: dict[str, int] | None = None
    priorities: list[str] | None = None
    concerns: list[str] | None = None
    notes: str | None = None
    is_primary_contact: bool | None = None
    source_type: str | None = None
    confirmation_status: str | None = None
    extracted_from_signal_id: UUID | None = None
    mentioned_in_signals: list[UUID] | None = None
    created_at: str
    updated_at: str | None = None

    # Enrichment fields
    engagement_level: str | None = None
    communication_preferences: dict | None = None
    last_interaction_date: str | None = None
    preferred_channel: str | None = None
    decision_authority: str | None = None
    engagement_strategy: str | None = None
    risk_if_disengaged: str | None = None
    win_conditions: list[str] | None = None
    key_concerns: list[str] | None = None

    # Decision scope
    approval_required_for: list[str] | None = None
    veto_power_over: list[str] | None = None

    # Relationships (raw UUIDs)
    reports_to_id: UUID | None = None
    allies: list[UUID] | None = None
    potential_blockers: list[UUID] | None = None
    linked_persona_id: UUID | None = None

    # Signal provenance
    source_signal_ids: list[UUID] | None = None
    evidence: list[dict] | None = None
    version: int | None = None
    enrichment_status: str | None = None
    linkedin_profile: str | None = None

    @field_validator("priorities", "concerns", "win_conditions", "key_concerns", mode="before")
    @classmethod
    def coerce_str_to_list(cls, v: list[str] | str | None) -> list[str] | None:
        return _coerce_str_to_list(v)

    class Config:
        from_attributes = True


# ============================================================================
# Detail Response Models (resolved references)
# ============================================================================


class ResolvedStakeholderRef(BaseModel):
    """A resolved stakeholder reference."""
    id: UUID
    name: str
    role: str | None = None
    stakeholder_type: str | None = None


class ResolvedPersonaRef(BaseModel):
    """A resolved persona reference."""
    id: UUID
    name: str
    role: str | None = None


class LinkedFeatureRef(BaseModel):
    """A linked feature reference."""
    id: UUID
    name: str
    priority_group: str | None = None
    confirmation_status: str | None = None


class LinkedDriverRef(BaseModel):
    """A linked business driver reference."""
    id: UUID
    description: str
    driver_type: str
    severity: str | None = None


class StakeholderDetailOut(StakeholderOut):
    """Extended response model with resolved references."""
    reports_to: ResolvedStakeholderRef | None = None
    allies_resolved: list[ResolvedStakeholderRef] = []
    potential_blockers_resolved: list[ResolvedStakeholderRef] = []
    linked_persona: ResolvedPersonaRef | None = None
    linked_features: list[LinkedFeatureRef] = []
    linked_drivers: list[LinkedDriverRef] = []


# ============================================================================
# Evidence Response Models
# ============================================================================


class SignalReference(BaseModel):
    """A signal reference for evidence."""
    id: UUID
    title: str | None = None
    signal_type: str | None = None
    source_label: str | None = None
    created_at: str | None = None


class FieldAttributionItem(BaseModel):
    """A field attribution item."""
    field_path: str
    signal_id: UUID | None = None
    signal_source: str | None = None
    signal_label: str | None = None
    contributed_at: str | None = None
    version_number: int | None = None


class EnrichmentRevisionItem(BaseModel):
    """An enrichment revision summary."""
    revision_number: int | None = None
    revision_type: str
    diff_summary: str | None = None
    changes: dict | None = None
    created_at: str
    created_by: str | None = None
    source_signal_id: UUID | None = None


class StakeholderEvidenceResponse(BaseModel):
    """Response for stakeholder evidence endpoint."""
    source_signals: list[SignalReference] = []
    field_attributions: list[FieldAttributionItem] = []
    enrichment_history: list[EnrichmentRevisionItem] = []
    evidence_items: list[dict] = []
    topic_mentions: dict[str, int] = {}


class StakeholderListResponse(BaseModel):
    """Response for listing stakeholders."""

    stakeholders: list[StakeholderOut]
    total: int


class WhoWouldKnowRequest(BaseModel):
    """Request for stakeholder suggestions."""

    topics: list[str] = Field(..., description="Topics to match against stakeholder expertise")
    entity_type: str | None = Field(None, description="Type of entity needing confirmation")
    gap_description: str | None = Field(None, description="What needs to be confirmed")


class StakeholderSuggestion(BaseModel):
    """A suggested stakeholder for confirmation."""

    stakeholder_id: UUID
    stakeholder_name: str
    role: str | None
    match_score: int
    reasons: list[str]
    is_primary_contact: bool
    suggestion_text: str | None


class WhoWouldKnowResponse(BaseModel):
    """Response for stakeholder suggestions."""

    suggestions: list[StakeholderSuggestion]
    total: int


# ============================================================================
# Helper: resolve references for detail endpoint
# ============================================================================


def _resolve_stakeholder_refs(ids: list, supabase) -> list[ResolvedStakeholderRef]:
    """Resolve a list of stakeholder UUIDs to name/role/type refs."""
    if not ids:
        return []
    str_ids = [str(i) for i in ids if i]
    if not str_ids:
        return []
    result = (
        supabase.table("stakeholders")
        .select("id, name, role, stakeholder_type")
        .in_("id", str_ids)
        .execute()
    )
    return [ResolvedStakeholderRef(**r) for r in (result.data or [])]


# ============================================================================
# Endpoints
# ============================================================================


@router.get("", response_model=StakeholderListResponse)
async def list_stakeholders(
    project_id: UUID = Path(..., description="Project UUID"),
    stakeholder_type: str | None = Query(None, description="Filter by type"),
    influence_level: str | None = Query(None, description="Filter by influence level"),
) -> StakeholderListResponse:
    """List all stakeholders for a project."""
    try:
        if stakeholder_type:
            stakeholders = stakeholders_db.list_stakeholders_by_type(project_id, stakeholder_type)
        else:
            stakeholders = stakeholders_db.list_stakeholders(project_id)

        if influence_level:
            stakeholders = [s for s in stakeholders if s.get("influence_level") == influence_level]

        return StakeholderListResponse(
            stakeholders=[StakeholderOut(**s) for s in stakeholders],
            total=len(stakeholders),
        )

    except Exception as e:
        logger.error(f"Error listing stakeholders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("", response_model=StakeholderOut)
async def create_stakeholder(
    background_tasks: BackgroundTasks,
    project_id: UUID = Path(..., description="Project UUID"),
    body: StakeholderCreate = ...,
) -> StakeholderOut:
    """Create a new stakeholder."""
    try:
        first_name = body.first_name
        last_name = body.last_name
        if not first_name:
            parts = body.name.strip().split(" ", 1)
            first_name = parts[0]
            if not last_name and len(parts) > 1:
                last_name = parts[1]

        stakeholder = stakeholders_db.create_stakeholder(
            project_id=project_id,
            name=body.name,
            stakeholder_type=body.stakeholder_type,
            email=body.email,
            role=body.role,
            organization=body.organization,
            influence_level=body.influence_level,
            priorities=body.priorities,
            concerns=body.concerns,
            notes=body.notes,
            confirmation_status="confirmed_consultant",
            first_name=first_name,
            last_name=last_name,
        )

        if body.domain_expertise:
            stakeholder = stakeholders_db.update_domain_expertise(
                UUID(stakeholder["id"]),
                body.domain_expertise,
                append=False,
            )

        # Trigger SI Agent enrichment in background
        stakeholder_id = UUID(stakeholder["id"])

        async def run_enrichment():
            from app.agents.stakeholder_intelligence_agent import invoke_stakeholder_intelligence_agent

            MAX_ITERATIONS = 6
            prev_score: int | None = None

            for iteration in range(MAX_ITERATIONS):
                try:
                    result = await invoke_stakeholder_intelligence_agent(
                        stakeholder_id=stakeholder_id,
                        project_id=project_id,
                        trigger="user_request",
                        trigger_context=f"Stakeholder created manually — auto-enrichment iteration {iteration + 1}/{MAX_ITERATIONS}",
                        specific_request="Enrich this newly created stakeholder profile" if iteration == 0 else "Continue enriching the weakest profile section",
                    )

                    if result.action_type in ("stop", "guidance"):
                        logger.info(
                            f"SI Agent stopped at iteration {iteration + 1}: {result.action_type}",
                            extra={"stakeholder_id": str(stakeholder_id)},
                        )
                        break

                    current_score = result.profile_completeness_after
                    if current_score is not None and current_score == prev_score:
                        logger.info(
                            f"SI Agent plateaued at {current_score}% after {iteration + 1} iterations",
                            extra={"stakeholder_id": str(stakeholder_id)},
                        )
                        break

                    prev_score = current_score

                    if current_score is not None and current_score >= 85:
                        logger.info(
                            f"SI Agent reached {current_score}% — good enough",
                            extra={"stakeholder_id": str(stakeholder_id)},
                        )
                        break

                except Exception as e:
                    logger.error(f"SI Agent enrichment iteration {iteration + 1} failed: {e}", exc_info=True)
                    break

        background_tasks.add_task(run_enrichment)

        return StakeholderOut(**stakeholder)

    except Exception as e:
        logger.error(f"Error creating stakeholder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{stakeholder_id}")
async def get_stakeholder(
    project_id: UUID = Path(..., description="Project UUID"),
    stakeholder_id: UUID = Path(..., description="Stakeholder UUID"),
    detail: bool = Query(False, description="Return resolved references"),
) -> StakeholderOut | StakeholderDetailOut:
    """Get a single stakeholder by ID. Pass ?detail=true for resolved references."""
    try:
        stakeholder = stakeholders_db.get_stakeholder(stakeholder_id)

        if not stakeholder:
            raise HTTPException(status_code=404, detail="Stakeholder not found")

        if str(stakeholder.get("project_id")) != str(project_id):
            raise HTTPException(status_code=404, detail="Stakeholder not found in this project")

        if not detail:
            return StakeholderOut(**stakeholder)

        # Resolve references for detail view
        from app.db.supabase_client import get_supabase
        supabase = get_supabase()

        # Resolve reports_to
        reports_to = None
        reports_to_id = stakeholder.get("reports_to_id")
        if reports_to_id:
            rt_result = (
                supabase.table("stakeholders")
                .select("id, name, role, stakeholder_type")
                .eq("id", str(reports_to_id))
                .maybe_single()
                .execute()
            )
            if rt_result.data:
                reports_to = ResolvedStakeholderRef(**rt_result.data)

        # Resolve allies
        allies_resolved = _resolve_stakeholder_refs(
            stakeholder.get("allies") or [], supabase
        )

        # Resolve potential blockers
        blockers_resolved = _resolve_stakeholder_refs(
            stakeholder.get("potential_blockers") or [], supabase
        )

        # Resolve linked persona
        linked_persona = None
        persona_id = stakeholder.get("linked_persona_id")
        if persona_id:
            p_result = (
                supabase.table("personas")
                .select("id, name, role")
                .eq("id", str(persona_id))
                .maybe_single()
                .execute()
            )
            if p_result.data:
                linked_persona = ResolvedPersonaRef(**p_result.data)

        # Query linked business drivers
        linked_drivers: list[LinkedDriverRef] = []
        try:
            bd_result = (
                supabase.table("business_drivers")
                .select("id, description, driver_type, severity")
                .eq("stakeholder_id", str(stakeholder_id))
                .execute()
            )
            linked_drivers = [LinkedDriverRef(**d) for d in (bd_result.data or [])]
        except Exception:
            pass  # business_drivers may not have stakeholder_id column

        # Query linked features via entity_dependencies
        linked_features: list[LinkedFeatureRef] = []
        try:
            dep_result = (
                supabase.table("entity_dependencies")
                .select("target_entity_id")
                .eq("source_entity_type", "stakeholder")
                .eq("source_entity_id", str(stakeholder_id))
                .eq("target_entity_type", "feature")
                .execute()
            )
            feature_ids = [d["target_entity_id"] for d in (dep_result.data or [])]
            if feature_ids:
                f_result = (
                    supabase.table("features")
                    .select("id, name, priority_group, confirmation_status")
                    .in_("id", feature_ids)
                    .execute()
                )
                linked_features = [LinkedFeatureRef(**f) for f in (f_result.data or [])]
        except Exception:
            pass

        return StakeholderDetailOut(
            **stakeholder,
            reports_to=reports_to,
            allies_resolved=allies_resolved,
            potential_blockers_resolved=blockers_resolved,
            linked_persona=linked_persona,
            linked_features=linked_features,
            linked_drivers=linked_drivers,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stakeholder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{stakeholder_id}/evidence", response_model=StakeholderEvidenceResponse)
async def get_stakeholder_evidence(
    project_id: UUID = Path(..., description="Project UUID"),
    stakeholder_id: UUID = Path(..., description="Stakeholder UUID"),
) -> StakeholderEvidenceResponse:
    """Get evidence, source signals, field attributions, and enrichment history for a stakeholder."""
    try:
        stakeholder = stakeholders_db.get_stakeholder(stakeholder_id)

        if not stakeholder:
            raise HTTPException(status_code=404, detail="Stakeholder not found")

        if str(stakeholder.get("project_id")) != str(project_id):
            raise HTTPException(status_code=404, detail="Stakeholder not found in this project")

        from app.db.supabase_client import get_supabase
        supabase = get_supabase()

        # Collect all signal IDs from mentioned_in_signals + source_signal_ids
        all_signal_ids: set[str] = set()
        for sid in (stakeholder.get("mentioned_in_signals") or []):
            all_signal_ids.add(str(sid))
        for sid in (stakeholder.get("source_signal_ids") or []):
            all_signal_ids.add(str(sid))
        extracted_signal = stakeholder.get("extracted_from_signal_id")
        if extracted_signal:
            all_signal_ids.add(str(extracted_signal))

        # Resolve signals
        source_signals: list[SignalReference] = []
        if all_signal_ids:
            sig_result = (
                supabase.table("signals")
                .select("id, source_label, signal_type, created_at")
                .in_("id", list(all_signal_ids))
                .order("created_at", desc=True)
                .execute()
            )
            for sig in (sig_result.data or []):
                source_signals.append(SignalReference(
                    id=sig["id"],
                    title=sig.get("source_label"),
                    signal_type=sig.get("signal_type"),
                    source_label=sig.get("source_label"),
                    created_at=sig.get("created_at"),
                ))

        # Field attributions
        field_attributions: list[FieldAttributionItem] = []
        try:
            fa_result = (
                supabase.table("field_attributions")
                .select("*")
                .eq("entity_type", "stakeholder")
                .eq("entity_id", str(stakeholder_id))
                .order("created_at", desc=True)
                .execute()
            )
            for fa in (fa_result.data or []):
                field_attributions.append(FieldAttributionItem(
                    field_path=fa.get("field_path", ""),
                    signal_id=fa.get("signal_id"),
                    signal_source=fa.get("signal_source"),
                    signal_label=fa.get("signal_label"),
                    contributed_at=fa.get("created_at"),
                    version_number=fa.get("version_number"),
                ))
        except Exception:
            pass  # field_attributions table may not exist

        # Enrichment history
        enrichment_history: list[EnrichmentRevisionItem] = []
        try:
            from app.db.revisions_enrichment import list_entity_revisions
            revisions = list_entity_revisions("stakeholder", stakeholder_id, limit=20)
            for rev in revisions:
                enrichment_history.append(EnrichmentRevisionItem(
                    revision_number=rev.get("revision_number"),
                    revision_type=rev.get("revision_type", "unknown"),
                    diff_summary=rev.get("diff_summary"),
                    changes=rev.get("changes"),
                    created_at=rev.get("created_at", ""),
                    created_by=rev.get("created_by"),
                    source_signal_id=rev.get("source_signal_id"),
                ))
        except Exception:
            pass

        return StakeholderEvidenceResponse(
            source_signals=source_signals,
            field_attributions=field_attributions,
            enrichment_history=enrichment_history,
            evidence_items=stakeholder.get("evidence") or [],
            topic_mentions=stakeholder.get("topic_mentions") or {},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stakeholder evidence: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/{stakeholder_id}", response_model=StakeholderOut)
async def update_stakeholder(
    background_tasks: BackgroundTasks,
    project_id: UUID = Path(..., description="Project UUID"),
    stakeholder_id: UUID = Path(..., description="Stakeholder UUID"),
    body: StakeholderUpdate = ...,
) -> StakeholderOut:
    """Update a stakeholder."""
    try:
        existing = stakeholders_db.get_stakeholder(stakeholder_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Stakeholder not found")
        if str(existing.get("project_id")) != str(project_id):
            raise HTTPException(status_code=404, detail="Stakeholder not found in this project")

        updates = {k: v for k, v in body.model_dump().items() if v is not None}

        if not updates:
            return StakeholderOut(**existing)

        stakeholder = stakeholders_db.update_stakeholder(stakeholder_id, updates)

        # Auto-trigger SI Agent re-enrichment on meaningful field changes
        enrichment_relevant_fields = {
            "role", "email", "organization", "influence_level", "stakeholder_type",
            "priorities", "concerns", "notes", "linkedin_profile",
        }
        changed_fields = set(updates.keys()) & enrichment_relevant_fields
        if changed_fields:
            async def run_re_enrichment():
                from app.agents.stakeholder_intelligence_agent import invoke_stakeholder_intelligence_agent

                MAX_ITERATIONS = 4
                prev_score: int | None = None

                for iteration in range(MAX_ITERATIONS):
                    try:
                        result = await invoke_stakeholder_intelligence_agent(
                            stakeholder_id=stakeholder_id,
                            project_id=project_id,
                            trigger="user_request",
                            trigger_context=f"Stakeholder updated — fields changed: {', '.join(changed_fields)}",
                            specific_request="Re-enrich based on updated stakeholder data" if iteration == 0 else "Continue enriching the weakest profile section",
                        )

                        if result.action_type in ("stop", "guidance"):
                            break

                        current_score = result.profile_completeness_after
                        if current_score is not None and current_score == prev_score:
                            break
                        prev_score = current_score
                        if current_score is not None and current_score >= 85:
                            break
                    except Exception as e:
                        logger.error(f"SI Agent re-enrichment iteration {iteration + 1} failed: {e}", exc_info=True)
                        break

            background_tasks.add_task(run_re_enrichment)

        return StakeholderOut(**stakeholder)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating stakeholder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{stakeholder_id}")
async def delete_stakeholder(
    project_id: UUID = Path(..., description="Project UUID"),
    stakeholder_id: UUID = Path(..., description="Stakeholder UUID"),
) -> dict[str, Any]:
    """Delete a stakeholder."""
    try:
        existing = stakeholders_db.get_stakeholder(stakeholder_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Stakeholder not found")
        if str(existing.get("project_id")) != str(project_id):
            raise HTTPException(status_code=404, detail="Stakeholder not found in this project")

        stakeholders_db.delete_stakeholder(stakeholder_id)
        return {"success": True, "message": "Stakeholder deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting stakeholder: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{stakeholder_id}/set-primary", response_model=StakeholderOut)
async def set_primary_contact(
    project_id: UUID = Path(..., description="Project UUID"),
    stakeholder_id: UUID = Path(..., description="Stakeholder UUID"),
) -> StakeholderOut:
    """Set a stakeholder as the primary contact for the project."""
    try:
        stakeholder = stakeholders_db.set_primary_contact(project_id, stakeholder_id)
        return StakeholderOut(**stakeholder)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error setting primary contact: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/primary", response_model=StakeholderListResponse)
async def get_primary_contacts(
    project_id: UUID = Path(..., description="Project UUID"),
) -> StakeholderListResponse:
    """Get primary contact(s) for a project."""
    try:
        stakeholders = stakeholders_db.get_primary_contacts(project_id)
        return StakeholderListResponse(
            stakeholders=[StakeholderOut(**s) for s in stakeholders],
            total=len(stakeholders),
        )

    except Exception as e:
        logger.error(f"Error getting primary contacts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/who-would-know", response_model=WhoWouldKnowResponse)
async def who_would_know(
    project_id: UUID = Path(..., description="Project UUID"),
    body: WhoWouldKnowRequest = ...,
) -> WhoWouldKnowResponse:
    """Find stakeholders who might know about given topics."""
    try:
        suggestions = stakeholders_db.suggest_stakeholders_for_confirmation(
            project_id=project_id,
            entity_type=body.entity_type or "unknown",
            entity_topics=body.topics,
            gap_description=body.gap_description,
        )

        return WhoWouldKnowResponse(
            suggestions=[StakeholderSuggestion(**s) for s in suggestions],
            total=len(suggestions),
        )

    except Exception as e:
        logger.error(f"Error in who-would-know: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Stakeholder Intelligence Endpoints
# ============================================================================


class StakeholderAnalyzeRequest(BaseModel):
    """Request to trigger SI Agent analysis."""

    trigger: str = Field("user_request", description="Trigger type")
    context: str | None = Field(None, description="Additional context")
    specific_request: str | None = Field(None, description="Specific request")
    focus_areas: list[str] | None = Field(None, description="Sections to focus on")


class IntelligenceSectionScore(BaseModel):
    """Score for a single profile section."""

    section: str
    score: int
    max_score: int


class StakeholderIntelligenceOut(BaseModel):
    """Response for stakeholder intelligence profile."""

    stakeholder_id: UUID
    name: str
    role: str | None = None
    profile_completeness: int = 0
    completeness_label: str = "Poor"
    intelligence_version: int = 0
    last_intelligence_at: str | None = None
    sections: list[IntelligenceSectionScore] = []
    enrichment_fields: dict = {}


class IntelligenceLogOut(BaseModel):
    """Response for a single intelligence log entry."""

    id: UUID
    trigger: str
    action_type: str
    action_summary: str | None = None
    profile_completeness_before: int | None = None
    profile_completeness_after: int | None = None
    fields_affected: list[str] = []
    stop_reason: str | None = None
    execution_time_ms: int | None = None
    success: bool = True
    created_at: str


class IntelligenceLogsResponse(BaseModel):
    """Response for intelligence logs listing."""

    logs: list[IntelligenceLogOut]
    total: int


@router.post("/{stakeholder_id}/analyze")
async def analyze_stakeholder(
    background_tasks: BackgroundTasks,
    project_id: UUID = Path(..., description="Project UUID"),
    stakeholder_id: UUID = Path(..., description="Stakeholder UUID"),
    body: StakeholderAnalyzeRequest = StakeholderAnalyzeRequest(),
) -> dict[str, Any]:
    """Trigger SI Agent analysis for a stakeholder (runs in background)."""
    try:
        existing = stakeholders_db.get_stakeholder(stakeholder_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Stakeholder not found")
        if str(existing.get("project_id")) != str(project_id):
            raise HTTPException(status_code=404, detail="Stakeholder not found in this project")

        async def run_analysis():
            from app.agents.stakeholder_intelligence_agent import invoke_stakeholder_intelligence_agent

            MAX_ITERATIONS = 6
            prev_score: int | None = None

            for iteration in range(MAX_ITERATIONS):
                try:
                    result = await invoke_stakeholder_intelligence_agent(
                        stakeholder_id=stakeholder_id,
                        project_id=project_id,
                        trigger=body.trigger if iteration == 0 else "user_request",
                        trigger_context=body.context if iteration == 0 else f"Auto-iteration {iteration + 1}/{MAX_ITERATIONS}",
                        specific_request=body.specific_request if iteration == 0 else "Continue enriching the weakest profile section",
                        focus_areas=body.focus_areas,
                    )

                    # Stop if agent chose to stop or returned guidance-only
                    if result.action_type in ("stop", "guidance"):
                        logger.info(
                            f"SI Agent stopped at iteration {iteration + 1}: {result.action_type}",
                            extra={"stakeholder_id": str(stakeholder_id)},
                        )
                        break

                    # Stop if completeness plateaued (no improvement)
                    current_score = result.profile_completeness_after
                    if current_score is not None and current_score == prev_score:
                        logger.info(
                            f"SI Agent plateaued at {current_score}% after {iteration + 1} iterations",
                            extra={"stakeholder_id": str(stakeholder_id)},
                        )
                        break

                    prev_score = current_score

                    # Stop if we've reached high completeness
                    if current_score is not None and current_score >= 85:
                        logger.info(
                            f"SI Agent reached {current_score}% — good enough",
                            extra={"stakeholder_id": str(stakeholder_id)},
                        )
                        break

                except Exception as e:
                    logger.error(f"SI Agent iteration {iteration + 1} failed: {e}", exc_info=True)
                    break

        background_tasks.add_task(run_analysis)

        return {
            "success": True,
            "message": "Stakeholder intelligence analysis started",
            "stakeholder_id": str(stakeholder_id),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering SI analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{stakeholder_id}/intelligence", response_model=StakeholderIntelligenceOut)
async def get_stakeholder_intelligence(
    project_id: UUID = Path(..., description="Project UUID"),
    stakeholder_id: UUID = Path(..., description="Stakeholder UUID"),
) -> StakeholderIntelligenceOut:
    """Get current intelligence profile and completeness breakdown for a stakeholder."""
    try:
        stakeholder = stakeholders_db.get_stakeholder(stakeholder_id)
        if not stakeholder:
            raise HTTPException(status_code=404, detail="Stakeholder not found")
        if str(stakeholder.get("project_id")) != str(project_id):
            raise HTTPException(status_code=404, detail="Stakeholder not found in this project")

        # Compute live completeness
        from app.agents.stakeholder_intelligence_tools import _execute_update_profile_completeness
        import asyncio
        completeness_result = await _execute_update_profile_completeness(stakeholder_id, project_id)
        completeness = completeness_result.get("data", {})

        sections = []
        max_scores = {
            "core_identity": 10,
            "engagement_profile": 20,
            "decision_authority": 20,
            "relationships": 20,
            "communication": 10,
            "win_conditions_concerns": 15,
            "evidence_depth": 5,
        }
        for section_name, section_score in completeness.get("sections", {}).items():
            sections.append(IntelligenceSectionScore(
                section=section_name,
                score=section_score,
                max_score=max_scores.get(section_name, 10),
            ))

        enrichment_fields = {
            "engagement_level": stakeholder.get("engagement_level"),
            "engagement_strategy": stakeholder.get("engagement_strategy"),
            "risk_if_disengaged": stakeholder.get("risk_if_disengaged"),
            "decision_authority": stakeholder.get("decision_authority"),
            "approval_required_for": stakeholder.get("approval_required_for"),
            "veto_power_over": stakeholder.get("veto_power_over"),
            "reports_to_id": str(stakeholder["reports_to_id"]) if stakeholder.get("reports_to_id") else None,
            "allies": stakeholder.get("allies"),
            "potential_blockers": stakeholder.get("potential_blockers"),
            "preferred_channel": stakeholder.get("preferred_channel"),
            "communication_preferences": stakeholder.get("communication_preferences"),
            "last_interaction_date": stakeholder.get("last_interaction_date"),
            "win_conditions": stakeholder.get("win_conditions"),
            "key_concerns": stakeholder.get("key_concerns"),
        }

        return StakeholderIntelligenceOut(
            stakeholder_id=stakeholder_id,
            name=stakeholder.get("name", ""),
            role=stakeholder.get("role"),
            profile_completeness=completeness.get("score", 0),
            completeness_label=completeness.get("label", "Poor"),
            intelligence_version=stakeholder.get("intelligence_version", 0),
            last_intelligence_at=str(stakeholder["last_intelligence_at"]) if stakeholder.get("last_intelligence_at") else None,
            sections=sections,
            enrichment_fields=enrichment_fields,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stakeholder intelligence: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{stakeholder_id}/intelligence-logs", response_model=IntelligenceLogsResponse)
async def get_stakeholder_intelligence_logs(
    project_id: UUID = Path(..., description="Project UUID"),
    stakeholder_id: UUID = Path(..., description="Stakeholder UUID"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> IntelligenceLogsResponse:
    """Get analysis history for a stakeholder (paginated)."""
    try:
        existing = stakeholders_db.get_stakeholder(stakeholder_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Stakeholder not found")
        if str(existing.get("project_id")) != str(project_id):
            raise HTTPException(status_code=404, detail="Stakeholder not found in this project")

        logs = stakeholders_db.get_stakeholder_intelligence_logs(
            stakeholder_id=stakeholder_id,
            limit=limit,
            offset=offset,
        )

        log_items = []
        for log in logs:
            log_items.append(IntelligenceLogOut(
                id=log["id"],
                trigger=log["trigger"],
                action_type=log["action_type"],
                action_summary=log.get("action_summary"),
                profile_completeness_before=log.get("profile_completeness_before"),
                profile_completeness_after=log.get("profile_completeness_after"),
                fields_affected=log.get("fields_affected") or [],
                stop_reason=log.get("stop_reason"),
                execution_time_ms=log.get("execution_time_ms"),
                success=log.get("success", True),
                created_at=str(log["created_at"]),
            ))

        return IntelligenceLogsResponse(logs=log_items, total=len(log_items))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting intelligence logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Cross-Project People Endpoint
# ============================================================================

people_router = APIRouter(prefix="/people")


class PeopleListResponse(BaseModel):
    """Response for listing stakeholders across projects."""
    stakeholders: list[StakeholderOut]
    total: int


@people_router.get("", response_model=PeopleListResponse)
async def list_all_stakeholders(
    search: str | None = Query(None, description="Search by name or email"),
    stakeholder_type: str | None = Query(None, description="Filter by type"),
    influence_level: str | None = Query(None, description="Filter by influence level"),
    project_id: str | None = Query(None, description="Filter by project"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> PeopleListResponse:
    """List all stakeholders across projects with optional filters."""
    from supabase import create_client
    from app.core.config import get_settings

    try:
        # Use a fresh service-role client to bypass RLS for cross-project queries.
        # The shared singleton from get_supabase() may have been mutated by auth
        # middleware, causing RLS to filter out rows with a stale JWT.
        settings = get_settings()
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

        query = supabase.table("stakeholders").select(
            "*, projects(name)", count="exact"
        ).order("updated_at", desc=True).range(offset, offset + limit - 1)

        if project_id:
            query = query.eq("project_id", project_id)
        if stakeholder_type:
            query = query.eq("stakeholder_type", stakeholder_type)
        if influence_level:
            query = query.eq("influence_level", influence_level)
        if search:
            query = query.or_(f"name.ilike.%{search}%,email.ilike.%{search}%")

        result = query.execute()
        total = result.count or 0

        stakeholders_out = []
        for s in (result.data or []):
            project_info = s.pop("projects", None)
            s["project_name"] = project_info.get("name") if project_info else None
            stakeholders_out.append(StakeholderOut(**s))

        return PeopleListResponse(stakeholders=stakeholders_out, total=total)

    except Exception as e:
        logger.error(f"Error listing all stakeholders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{stakeholder_id}/topics", response_model=StakeholderOut)
async def update_topic_mentions(
    project_id: UUID = Path(..., description="Project UUID"),
    stakeholder_id: UUID = Path(..., description="Stakeholder UUID"),
    topics: list[str] = ...,
) -> StakeholderOut:
    """Update topic mention counts for a stakeholder."""
    try:
        existing = stakeholders_db.get_stakeholder(stakeholder_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Stakeholder not found")
        if str(existing.get("project_id")) != str(project_id):
            raise HTTPException(status_code=404, detail="Stakeholder not found in this project")

        stakeholder = stakeholders_db.update_topic_mentions(stakeholder_id, topics)
        return StakeholderOut(**stakeholder)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating topic mentions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
