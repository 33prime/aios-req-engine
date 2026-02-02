"""API routes for prototype review sessions and feedback.

Handles session lifecycle, feedback submission, context-aware chat,
client review tokens, feedback synthesis, and code updates.
"""

import json
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.core.schemas_prototypes import (
    ChatResponse,
    CreateSessionRequest,
    FeedbackResponse,
    SessionResponse,
    SubmitFeedbackRequest,
    SessionChatRequest,
)
from app.db.prototype_sessions import (
    create_feedback,
    create_session,
    generate_client_token,
    get_feedback_for_session,
    get_session,
    get_session_by_token,
    list_sessions,
    update_session,
)
from app.db.prototypes import get_prototype, list_overlays, update_prototype

logger = get_logger(__name__)
router = APIRouter(prefix="/prototype-sessions", tags=["prototype_sessions"])


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
    except Exception as e:
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

    Uses the current session context (page, feature, component) to provide
    relevant responses and extract structured feedback.
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

        # Build context-aware prompt
        context_info = ""
        if request.context:
            ctx = request.context
            context_info = f"""
Current page: {ctx.current_page}
Active feature: {ctx.active_feature_name or 'None'} ({ctx.active_feature_id or 'N/A'})
Active component: {ctx.active_component or 'None'}
Visible features: {', '.join(ctx.visible_features)}
Pages visited: {len(ctx.page_history)}
Features reviewed: {len(ctx.features_reviewed)}
"""

        # Find overlay for active feature
        active_overlay = None
        if request.context and request.context.active_feature_id:
            for o in overlays:
                if o.get("feature_id") == request.context.active_feature_id:
                    active_overlay = o
                    break

        system_prompt = f"""You are an AI requirements assistant helping a consultant review a prototype.
You have access to feature analysis data and can help identify requirements gaps.

Session Context:
{context_info}

{"Active Feature Overlay:" if active_overlay else "No active feature overlay."}
{json.dumps(active_overlay.get("overlay_content", {}), indent=2, default=str)[:2000] if active_overlay else ""}

Help the consultant by:
1. Answering questions about the current feature/page
2. Suggesting what to look for based on the overlay data
3. Identifying when their observations match or conflict with existing requirements
4. Extracting structured feedback from their messages

After responding, if the message contains feedback (observations, requirements, concerns),
include it in the extracted_feedback array as JSON objects with keys:
feedback_type, content, feature_id (if applicable), priority
"""

        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=settings.CHAT_MODEL,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": request.message}],
        )

        response_text = response.content[0].text

        # Try to extract feedback from the response
        extracted_feedback: list[dict] = []
        # If the AI included structured feedback in its response, we'd parse it here
        # For now, return the response as-is

        return ChatResponse(
            response=response_text,
            extracted_feedback=extracted_feedback,
        )

    except HTTPException:
        raise
    except Exception as e:
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

        return {
            "session_id": str(session_id),
            "client_review_token": token,
            "client_review_url": f"/portal/prototype?token={token}",
        }

    except HTTPException:
        raise
    except Exception as e:
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

        # Get unanswered high-priority questions for client
        from app.db.prototypes import get_unanswered_questions

        questions = get_unanswered_questions(UUID(session["prototype_id"]))
        client_questions = [q for q in questions if q.get("priority") in ("high", "medium")]

        return {
            "deploy_url": prototype.get("deploy_url"),
            "session_number": session["session_number"],
            "features_analyzed": len(overlays),
            "questions": client_questions[:20],  # Top 20 for client
        }

    except HTTPException:
        raise
    except Exception as e:
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
    except Exception as e:
        logger.exception(f"Failed to synthesize feedback for session {session_id}")
        raise HTTPException(status_code=500, detail="Failed to synthesize feedback")


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
    except Exception as e:
        logger.exception(f"Failed to update code for session {session_id}")
        raise HTTPException(status_code=500, detail="Failed to update code")
