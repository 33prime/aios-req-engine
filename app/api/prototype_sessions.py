"""API routes for prototype review sessions and feedback.

Handles session lifecycle, feedback submission, context-aware chat,
client review tokens, feedback synthesis, and code updates.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.core.schemas_prototypes import (
    ApplySynthesisResponse,
    ChatResponse,
    CreatedFeature,
    CreateSessionRequest,
    FeedbackResponse,
    SessionChatRequest,
    SessionResponse,
    SkippedFeature,
    StatusChange,
    SubmitEpicVerdictRequest,
    SubmitFeedbackRequest,
)
from app.db.prototype_sessions import (
    create_feedback,
    create_session,
    generate_client_token,
    get_feedback_for_session,
    get_session,
    get_session_by_token,
    list_epic_confirmations,
    list_sessions,
    update_session,
    upsert_epic_confirmation,
)
from app.db.prototypes import get_prototype, list_overlays, update_prototype

logger = get_logger(__name__)
router = APIRouter(prefix="/prototype-sessions", tags=["prototype_sessions"])


@router.get("/by-prototype/{prototype_id}", response_model=list[SessionResponse])
async def list_sessions_endpoint(prototype_id: UUID) -> list[SessionResponse]:
    """List all sessions for a prototype."""
    try:
        sessions = list_sessions(prototype_id)
        return [SessionResponse(**s) for s in sessions]
    except Exception:
        logger.exception(f"Failed to list sessions for prototype {prototype_id}")
        raise HTTPException(status_code=500, detail="Failed to list sessions")


@router.post("", status_code=201, response_model=SessionResponse)
async def create_session_endpoint(
    request: CreateSessionRequest,
) -> SessionResponse:
    """Create a new review session for a prototype."""
    try:
        prototype = get_prototype(request.prototype_id)
        if not prototype:
            raise HTTPException(status_code=404, detail="Prototype not found")

        # Determine session number
        existing = list_sessions(request.prototype_id)
        session_number = len(existing) + 1

        session = create_session(
            prototype_id=request.prototype_id,
            session_number=session_number,
        )

        # Increment prototype session count
        update_prototype(request.prototype_id, session_count=session_number)

        # Start the session
        update_session(
            UUID(session["id"]),
            status="consultant_review",
            started_at="now()",
        )

        logger.info(
            f"Created session #{session_number} for prototype {request.prototype_id}"
        )
        return SessionResponse(**session)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to create session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session")


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session_endpoint(session_id: UUID) -> SessionResponse:
    """Get session details."""
    try:
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return SessionResponse(**session)
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to get session {session_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve session")


@router.post("/{session_id}/feedback", status_code=201, response_model=FeedbackResponse)
async def submit_feedback_endpoint(
    session_id: UUID,
    request: SubmitFeedbackRequest,
) -> FeedbackResponse:
    """Submit consultant feedback during a session."""
    try:
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        feedback = create_feedback(
            session_id=session_id,
            source="consultant",
            content=request.content,
            feedback_type=request.feedback_type,
            context=request.context.model_dump() if request.context else None,
            feature_id=UUID(request.feature_id) if request.feature_id else None,
            page_path=request.page_path,
            component_name=request.component_name,
            answers_question_id=UUID(request.answers_question_id) if request.answers_question_id else None,
            priority=request.priority,
        )

        # If this answers a question, record the answer
        if request.answers_question_id:
            from app.db.prototypes import answer_question

            answer_question(
                question_id=UUID(request.answers_question_id),
                answer=request.content,
                session_number=session["session_number"],
                answered_by="consultant",
            )

        return FeedbackResponse(**feedback)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to submit feedback: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback")


@router.post("/{session_id}/chat", response_model=ChatResponse)
async def session_chat_endpoint(
    session_id: UUID,
    request: SessionChatRequest,
) -> ChatResponse:
    """Context-aware AI chat during a review session.

    When a feature_id is provided, builds a verdict-aware prompt that asks
    concise follow-up questions based on the consultant's verdict.
    """
    try:
        from anthropic import Anthropic

        from app.core.config import get_settings

        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        settings = get_settings()
        prototype = get_prototype(UUID(session["prototype_id"]))
        overlays = list_overlays(UUID(session["prototype_id"])) if prototype else []

        # Resolve which feature overlay to use
        target_feature_id = request.feature_id or (
            request.context.active_feature_id if request.context else None
        )

        active_overlay = None
        if target_feature_id:
            for o in overlays:
                if o.get("feature_id") == target_feature_id:
                    active_overlay = o
                    break

        # Build context section
        context_info = ""
        if request.context:
            ctx = request.context
            context_info = f"Page: {ctx.current_page} | Feature: {ctx.active_feature_name or 'None'} | Reviewed: {len(ctx.features_reviewed)}/{len(overlays)}"

        # Build verdict-aware system prompt
        overlay_content = active_overlay.get("overlay_content", {}) if active_overlay else {}
        feature_name = overlay_content.get("feature_name", "this feature")
        consultant_verdict = active_overlay.get("consultant_verdict") if active_overlay else None
        suggested_verdict = overlay_content.get("suggested_verdict")
        gaps = overlay_content.get("gaps", [])
        overview = overlay_content.get("overview", {})
        spec_summary = overview.get("spec_summary", "")
        proto_summary = overview.get("prototype_summary", "")
        delta = overview.get("delta", [])
        confidence = overlay_content.get("confidence", 0)
        impl_status = overview.get("implementation_status", "unknown")

        # Verdict-specific guidance
        verdict_guidance = ""
        if consultant_verdict == "aligned":
            verdict_guidance = (
                "The consultant marked this feature as ALIGNED. "
                "Ask if there are edge cases, missing validation rules, or data handling nuances "
                "that look correct but might break under real-world conditions. Be brief."
            )
        elif consultant_verdict == "needs_adjustment":
            gap_text = "; ".join(g.get("question", "") for g in gaps[:2]) if gaps else "gaps found in analysis"
            verdict_guidance = (
                f"The consultant says this NEEDS ADJUSTMENT. "
                f"Our analysis found these gaps: {gap_text}. "
                f"Deltas: {'; '.join(delta[:3])}. "
                "Ask what specifically needs to change — is it the spec, the implementation, or both?"
            )
        elif consultant_verdict == "off_track":
            verdict_guidance = (
                "The consultant says this is OFF TRACK — a fundamental disconnect. "
                "Ask about the core misunderstanding: is the feature solving the wrong problem, "
                "targeting the wrong persona, or missing the business intent entirely?"
            )
        else:
            verdict_guidance = "No verdict set yet. Help the consultant understand the feature."

        # Note if consultant disagrees with AI suggestion
        disagreement = ""
        if consultant_verdict and suggested_verdict and consultant_verdict != suggested_verdict:
            disagreement = (
                f"\nNote: AI suggested '{suggested_verdict}' but the consultant chose '{consultant_verdict}'. "
                "This disagreement is interesting — gently explore why they see it differently."
            )

        system_prompt = f"""You are a concise requirements assistant helping a consultant review "{feature_name}" in a prototype.

Context: {context_info}
Implementation: {impl_status} | Confidence: {round(confidence * 100)}%
Spec: {spec_summary[:200]}
Prototype: {proto_summary[:200]}

{verdict_guidance}{disagreement}

RULES:
- Be concise: 2-3 sentences max, then ask ONE follow-up question
- Focus on requirements implications, not code quality
- If the consultant's observation reveals a new requirement, acknowledge it
- Never repeat information the consultant already knows"""

        # Use verdict chat model (Haiku) by default, allow override
        model = request.model_override or settings.VERDICT_CHAT_MODEL

        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=model,
            max_tokens=512,
            system=system_prompt,
            messages=[{"role": "user", "content": request.message}],
        )

        response_text = response.content[0].text

        return ChatResponse(
            response=response_text,
            extracted_feedback=[],
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to chat in session {session_id}")
        raise HTTPException(status_code=500, detail="Failed to process chat message")


@router.post("/{session_id}/end-review")
async def end_review_endpoint(session_id: UUID) -> dict:
    """End consultant review and generate a client review token."""
    try:
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        token = generate_client_token(session_id)
        update_session(session_id, status="awaiting_client")

        prototype = get_prototype(UUID(session["prototype_id"]))
        project_id = prototype["project_id"] if prototype else "unknown"

        return {
            "session_id": str(session_id),
            "client_review_token": token,
            "client_review_url": f"/portal/{project_id}/prototype?token={token}&session={session_id}",
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to end review for session {session_id}")
        raise HTTPException(status_code=500, detail="Failed to end review")


@router.get("/{session_id}/client-data")
async def get_client_data_endpoint(session_id: UUID, token: str) -> dict:
    """Get client review data. Authenticated via client review token."""
    try:
        session = get_session_by_token(token)
        if not session or session["id"] != str(session_id):
            raise HTTPException(status_code=403, detail="Invalid token")

        prototype = get_prototype(UUID(session["prototype_id"]))
        if not prototype:
            raise HTTPException(status_code=404, detail="Prototype not found")

        overlays = list_overlays(UUID(session["prototype_id"]))

        # Get unanswered high-priority questions for client (legacy compat)
        from app.db.prototypes import get_unanswered_questions

        questions = get_unanswered_questions(UUID(session["prototype_id"]))
        client_questions = [q for q in questions if q.get("priority") in ("high", "medium")]

        # Build per-feature review context for client
        feature_reviews = []
        for o in overlays:
            content = o.get("overlay_content") or {}
            gaps = content.get("gaps", [])
            feature_reviews.append({
                "feature_name": content.get("feature_name", o.get("handoff_feature_name", "Unknown")),
                "overlay_id": o["id"],
                "consultant_verdict": o.get("consultant_verdict"),
                "consultant_notes": o.get("consultant_notes"),
                "suggested_verdict": content.get("suggested_verdict"),
                "validation_question": gaps[0].get("question") if gaps else None,
                "validation_why": gaps[0].get("why_it_matters") if gaps else None,
                "validation_area": gaps[0].get("requirement_area") if gaps else None,
                "spec_summary": (content.get("overview") or {}).get("spec_summary"),
                "implementation_status": (content.get("overview") or {}).get("implementation_status"),
                "confidence": content.get("confidence", 0),
                "status": content.get("status", "unknown"),
            })

        return {
            "prototype_id": str(session["prototype_id"]),
            "deploy_url": prototype.get("deploy_url"),
            "session_number": session["session_number"],
            "features_analyzed": len(overlays),
            "questions": client_questions[:20],  # Legacy compat
            "feature_reviews": feature_reviews,
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to get client data for session {session_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve client data")


@router.post("/{session_id}/synthesize")
async def synthesize_endpoint(session_id: UUID) -> dict:
    """Trigger feedback synthesis for a session."""
    try:
        from app.chains.synthesize_feedback import synthesize_session_feedback
        from app.core.config import get_settings
        from app.db.features import list_features

        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        settings = get_settings()
        prototype = get_prototype(UUID(session["prototype_id"]))
        if not prototype:
            raise HTTPException(status_code=404, detail="Prototype not found")

        feedback_items = get_feedback_for_session(session_id)
        overlays = list_overlays(UUID(session["prototype_id"]))
        features = list_features(UUID(prototype["project_id"]))

        update_session(session_id, status="synthesizing")

        synthesis = synthesize_session_feedback(
            feedback_items=feedback_items,
            overlays=overlays,
            features=features,
            settings=settings,
        )

        update_session(session_id, synthesis=synthesis.model_dump())

        logger.info(f"Synthesized feedback for session {session_id}")

        return {
            "session_id": str(session_id),
            "features_with_feedback": len(synthesis.by_feature),
            "new_features_discovered": len(synthesis.new_features_discovered),
            "high_priority_changes": len(synthesis.high_priority_changes),
            "session_summary": synthesis.session_summary,
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to synthesize feedback for session {session_id}")
        raise HTTPException(status_code=500, detail="Failed to synthesize feedback")


@router.post("/{session_id}/apply-synthesis", response_model=ApplySynthesisResponse)
async def apply_synthesis_endpoint(session_id: UUID) -> ApplySynthesisResponse:
    """Apply feedback synthesis results to AIOS feature entities.

    Reads the session's synthesis, then for each feature:
    - Updates confirmation_status to the recommended_status
    - Stores confirmed_requirements, new_requirements, code_changes as ai_notes
    - Creates new features from new_features_discovered
    """
    try:
        from app.db.features import get_feature, update_feature, update_feature_status

        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        synthesis_data = session.get("synthesis")
        if not synthesis_data:
            raise HTTPException(
                status_code=400,
                detail="No synthesis available — run synthesize first",
            )

        prototype = get_prototype(UUID(session["prototype_id"]))
        if not prototype:
            raise HTTPException(status_code=404, detail="Prototype not found")

        project_id = UUID(prototype["project_id"])

        # Valid confirmation statuses from frozen contract
        valid_statuses = {
            "ai_generated",
            "confirmed_consultant",
            "confirmed_client",
            "needs_client",
        }

        status_changes: list[StatusChange] = []
        skipped: list[SkippedFeature] = []

        # Apply per-feature synthesis
        by_feature = synthesis_data.get("by_feature", {})
        for feature_id, synth in by_feature.items():
            recommended = synth.get("recommended_status")
            if not recommended or recommended not in valid_statuses:
                skipped.append(SkippedFeature(
                    feature_id=feature_id,
                    reason=f"Invalid recommended_status: {recommended}",
                ))
                continue

            try:
                feature = get_feature(UUID(feature_id))
            except (ValueError, Exception):
                skipped.append(SkippedFeature(
                    feature_id=feature_id,
                    reason="Feature not found in database",
                ))
                continue

            old_status = feature.get("confirmation_status", "ai_generated")

            # Skip if status unchanged
            if old_status == recommended:
                skipped.append(SkippedFeature(
                    feature_id=feature_id,
                    reason=f"Status already {old_status}",
                ))
                continue

            # Apply status change
            update_feature_status(UUID(feature_id), recommended)

            # Store synthesis notes on the feature
            ai_notes = {
                "source": f"prototype_session_{session_id}",
                "session_number": session.get("session_number"),
                "confirmed_requirements": synth.get("confirmed_requirements", []),
                "new_requirements": synth.get("new_requirements", []),
                "code_changes": synth.get("code_changes", []),
                "contradictions": synth.get("contradictions", []),
            }
            update_feature(
                UUID(feature_id),
                {"ai_notes": ai_notes},
                trigger_event="prototype_synthesis",
            )

            status_changes.append(StatusChange(
                feature_id=feature_id,
                feature_name=feature.get("name", "Unknown"),
                old_status=old_status,
                new_status=recommended,
            ))

        # Create new features discovered during session
        features_created: list[CreatedFeature] = []
        new_features = synthesis_data.get("new_features_discovered", [])

        if new_features:
            from app.db.supabase_client import get_supabase

            supabase = get_supabase()
            for nf in new_features:
                name = nf.get("name", "").strip()
                if not name:
                    continue

                row = {
                    "project_id": str(project_id),
                    "name": name,
                    "overview": nf.get("description", ""),
                    "confirmation_status": "ai_generated",
                    "status": "ai_generated",
                    "evidence": [
                        {
                            "source": f"prototype_session_{session_id}",
                            "content": nf.get("source", "Discovered during prototype review"),
                        }
                    ],
                }
                try:
                    supabase.table("features").insert(row).execute()
                    features_created.append(CreatedFeature(
                        name=name,
                        description=nf.get("description", ""),
                    ))
                except Exception as e:
                    logger.warning(f"Failed to create new feature '{name}': {e}")

        logger.info(
            f"Applied synthesis for session {session_id}: "
            f"{len(status_changes)} updated, {len(features_created)} created, "
            f"{len(skipped)} skipped"
        )

        return ApplySynthesisResponse(
            applied_count=len(status_changes),
            created_count=len(features_created),
            status_changes=status_changes,
            features_created=features_created,
            skipped=skipped,
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to apply synthesis for session {session_id}")
        raise HTTPException(status_code=500, detail="Failed to apply synthesis")


@router.post("/{session_id}/complete-client-review")
async def complete_client_review_endpoint(session_id: UUID, token: str) -> dict:
    """Mark client review as complete. Auth via client review token."""
    try:
        session = get_session_by_token(token)
        if not session or session["id"] != str(session_id):
            raise HTTPException(status_code=403, detail="Invalid token")

        update_session(session_id, status="client_complete", client_completed_at="now()")

        # Auto-compute and save convergence snapshot
        try:
            from app.core.convergence_tracker import compute_convergence, save_convergence_snapshot
            prototype_id = UUID(session["prototype_id"])
            snapshot = compute_convergence(prototype_id)
            save_convergence_snapshot(session_id, snapshot)
        except Exception as conv_err:
            logger.warning(f"Convergence snapshot failed (non-fatal): {conv_err}")

        return {"session_id": str(session_id), "status": "client_complete"}

    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to complete client review for session {session_id}")
        raise HTTPException(status_code=500, detail="Failed to complete client review")


@router.post("/{session_id}/update-code")
async def update_code_endpoint(session_id: UUID) -> dict:
    """Trigger code updater agent for a session."""
    try:
        from app.agents.prototype_updater import execute_updates, plan_updates
        from app.core.config import get_settings
        from app.db.features import list_features
        from app.services.git_manager import GitManager

        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        synthesis_data = session.get("synthesis")
        if not synthesis_data:
            raise HTTPException(status_code=400, detail="No synthesis available — run synthesize first")

        prototype = get_prototype(UUID(session["prototype_id"]))
        if not prototype or not prototype.get("local_path"):
            raise HTTPException(status_code=400, detail="Prototype not ingested")

        settings = get_settings()
        features = list_features(UUID(prototype["project_id"]))
        git = GitManager(base_dir=settings.PROTOTYPE_TEMP_DIR)
        file_tree = git.get_file_tree(prototype["local_path"])

        update_session(session_id, status="updating")

        # Create session branch
        branch_name = f"session-{session['session_number']}"
        try:
            git.create_branch(prototype["local_path"], branch_name)
        except Exception:
            git.checkout(prototype["local_path"], branch_name)

        # Plan and execute
        plan = await plan_updates(synthesis_data, file_tree, features)
        update_session(session_id, code_update_plan=plan.model_dump())

        result = await execute_updates(
            plan=plan,
            local_path=prototype["local_path"],
            project_id=prototype["project_id"],
        )

        update_session(
            session_id,
            code_update_result=result.model_dump(),
            status="completed",
            completed_at="now()",
        )

        # Auto-compute and save convergence snapshot
        try:
            from app.core.convergence_tracker import compute_convergence, save_convergence_snapshot
            prototype_id_uuid = UUID(prototype["id"])
            snapshot = compute_convergence(prototype_id_uuid)
            save_convergence_snapshot(session_id, snapshot)
        except Exception as conv_err:
            logger.warning(f"Convergence snapshot failed (non-fatal): {conv_err}")

        # Push changes
        try:
            git.push(prototype["local_path"], branch_name)
        except Exception as e:
            logger.warning(f"Failed to push session branch: {e}")

        return {
            "session_id": str(session_id),
            "files_changed": len(result.files_changed),
            "build_passed": result.build_passed,
            "commit_sha": result.commit_sha,
            "summary": result.summary,
        }

    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to update code for session {session_id}")
        raise HTTPException(status_code=500, detail="Failed to update code")


# =============================================================================
# Epic Confirmations
# =============================================================================


@router.put("/{session_id}/epic-verdict")
async def submit_epic_verdict(session_id: UUID, body: SubmitEpicVerdictRequest):
    """Submit or update a single epic confirmation verdict."""
    try:
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        result = upsert_epic_confirmation(
            session_id=session_id,
            card_type=body.card_type,
            card_index=body.card_index,
            verdict=body.verdict,
            notes=body.notes,
            answer=body.answer,
            source=body.source,
        )
        return result

    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to submit epic verdict for session {session_id}")
        raise HTTPException(status_code=500, detail="Failed to submit epic verdict")


@router.get("/{session_id}/epic-verdicts")
async def get_epic_verdicts(session_id: UUID):
    """Get all epic confirmations for a session."""
    try:
        session = get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return list_epic_confirmations(session_id)

    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Failed to get epic verdicts for session {session_id}")
        raise HTTPException(status_code=500, detail="Failed to retrieve epic verdicts")


# =============================================================================
# Convergence Tracking
# =============================================================================


@router.get("/prototype-sessions/convergence/{prototype_id}")
async def get_convergence(prototype_id: UUID):
    """Get convergence metrics for a prototype across all sessions.

    Returns alignment rate, trend, per-feature convergence detail,
    feedback resolution rate, and question coverage.
    """
    from app.core.convergence_tracker import compute_convergence

    snapshot = compute_convergence(prototype_id)
    return snapshot.to_dict()


@router.post("/prototype-sessions/{session_id}/save-convergence")
async def save_session_convergence(session_id: UUID):
    """Compute and persist convergence snapshot for a session.

    Call after session completion to freeze metrics for trend analysis.
    """
    from app.core.convergence_tracker import compute_convergence, save_convergence_snapshot

    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    prototype_id = UUID(session["prototype_id"])
    snapshot = compute_convergence(prototype_id)
    save_convergence_snapshot(session_id, snapshot)

    return {"saved": True, "alignment_rate": snapshot.alignment_rate, "trend": snapshot.trend}
