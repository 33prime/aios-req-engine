"""API endpoints for Discovery Prep feature.

Supports stage-aware prep generation for different collaboration phases:
- PRE_DISCOVERY: Extract requirements and understand problem space
- VALIDATION: Confirm features and requirements
- PROTOTYPE: Get feedback on designs
"""

import asyncio
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth_middleware import AuthContext, require_consultant
from app.core.logging import get_logger
from app.core.schemas_collaboration import CollaborationPhase
from app.core.schemas_discovery_prep import (
    ConfirmItemRequest,
    DiscoveryPrepBundle,
    DocRecommendation,
    GeneratePrepRequest,
    GeneratePrepResponse,
    PrepQuestion,
    PrepStatus,
    SendToPortalResponse,
    SendToPotalRequest,
)
from app.db.discovery_prep import (
    create_or_update_bundle,
    delete_bundle,
    get_bundle,
    update_bundle_status,
    update_document,
    update_question,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/discovery-prep", tags=["discovery-prep"])


@router.get("/{project_id}", response_model=DiscoveryPrepBundle)
async def get_discovery_prep(
    project_id: UUID,
    auth: AuthContext = Depends(require_consultant),
):
    """Get the current discovery prep bundle for a project."""
    bundle = await get_bundle(project_id)
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No discovery prep bundle found. Generate one first.",
        )
    return bundle


@router.post("/{project_id}/generate", response_model=GeneratePrepResponse)
async def generate_discovery_prep(
    project_id: UUID,
    request: Optional[GeneratePrepRequest] = None,
    phase: Optional[CollaborationPhase] = Query(
        default=None,
        description="Collaboration phase for stage-aware generation. Defaults to PRE_DISCOVERY.",
    ),
    auth: AuthContext = Depends(require_consultant),
):
    """
    Generate prep content (questions, documents, agenda) for any collaboration phase.

    Runs Question Agent and Document Agent in parallel, then generates
    a cohesive agenda that incorporates the questions.

    The phase parameter controls the focus of generated content:
    - PRE_DISCOVERY: Extract requirements and understand problem space
    - VALIDATION: Confirm features and requirements
    - PROTOTYPE: Get feedback on designs
    - etc.
    """
    from app.agents.discovery_prep import generate_prep_questions, recommend_documents, generate_agenda

    # Default to pre_discovery if not specified
    target_phase = phase or CollaborationPhase.PRE_DISCOVERY

    # Check if bundle exists and force_regenerate not set
    if request and not request.force_regenerate:
        existing = await get_bundle(project_id)
        if existing:
            return GeneratePrepResponse(
                bundle=existing,
                message="Bundle already exists. Use force_regenerate=true to regenerate.",
            )

    try:
        # Run question and document agents in parallel (with phase awareness)
        question_result, document_result = await asyncio.gather(
            generate_prep_questions(project_id, phase=target_phase),
            recommend_documents(project_id, phase=target_phase),
        )

        # Generate agenda that incorporates the questions
        document_names = [d.document_name for d in document_result.documents]
        agenda_result = await generate_agenda(
            project_id,
            questions=question_result.questions,
            document_names=document_names,
        )

        # Get stakeholder suggestions for questions
        from app.agents.stakeholder_suggester import suggest_stakeholder_for_question

        # Convert agent outputs to model instances with IDs
        questions = []
        for q in question_result.questions:
            # Get stakeholder suggestions for this question
            suggestions = await suggest_stakeholder_for_question(project_id, q.question)
            suggested_names = [
                s.name for s in suggestions
                if s.is_matched and s.name
            ][:3]  # Limit to 3 suggestions

            questions.append(
                PrepQuestion(
                    question=q.question,
                    best_answered_by=q.best_answered_by,
                    why_important=q.why_important,
                    suggested_stakeholders=suggested_names,
                )
            )

        # Import helper for example formats
        from app.agents.discovery_prep.document_agent import get_example_formats

        documents = [
            DocRecommendation(
                document_name=d.document_name,
                priority=d.priority,
                why_important=d.why_important,
                example_formats=get_example_formats(d.document_name),
            )
            for d in document_result.documents
        ]

        # Create bundle
        bundle = await create_or_update_bundle(
            project_id=project_id,
            agenda_summary=agenda_result.summary,
            agenda_bullets=agenda_result.bullets,
            questions=questions,
            documents=documents,
        )

        return GeneratePrepResponse(
            bundle=bundle,
            message=f"Generated {len(questions)} questions and {len(documents)} document recommendations.",
        )

    except Exception as e:
        logger.error(f"Error generating discovery prep: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate discovery prep: {str(e)}",
        )


@router.post("/{project_id}/questions/{question_id}/confirm", response_model=DiscoveryPrepBundle)
async def confirm_question(
    project_id: UUID,
    question_id: UUID,
    request: Optional[ConfirmItemRequest] = None,
    auth: AuthContext = Depends(require_consultant),
):
    """Confirm (or unconfirm) a prep question."""
    confirmed = request.confirmed if request else True

    bundle = await update_question(project_id, question_id, confirmed=confirmed)
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bundle or question not found.",
        )
    return bundle


@router.post("/{project_id}/documents/{document_id}/confirm", response_model=DiscoveryPrepBundle)
async def confirm_document(
    project_id: UUID,
    document_id: UUID,
    request: Optional[ConfirmItemRequest] = None,
    auth: AuthContext = Depends(require_consultant),
):
    """Confirm (or unconfirm) a document recommendation."""
    confirmed = request.confirmed if request else True

    bundle = await update_document(project_id, document_id, confirmed=confirmed)
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bundle or document not found.",
        )
    return bundle


@router.post("/{project_id}/send", response_model=SendToPortalResponse)
async def send_to_portal(
    project_id: UUID,
    request: Optional[SendToPotalRequest] = None,
    auth: AuthContext = Depends(require_consultant),
):
    """
    Send confirmed questions and documents to the client portal.

    Creates info_requests from confirmed items and optionally invites stakeholders.
    """
    bundle = await get_bundle(project_id)
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No discovery prep bundle found.",
        )

    # Get confirmed items
    confirmed_questions = [q for q in bundle.questions if q.confirmed]
    confirmed_documents = [d for d in bundle.documents if d.confirmed]

    if not confirmed_questions and not confirmed_documents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No confirmed items to send. Confirm at least one question or document.",
        )

    try:
        # Create info requests from confirmed items
        from app.core.schemas_portal import (
            InfoRequestCreate,
            InfoRequestCreator,
            InfoRequestInputType,
            InfoRequestPhase,
            InfoRequestPriority,
            InfoRequestType,
        )
        from app.db.info_requests import bulk_create_info_requests

        info_requests = []

        # Convert questions to info requests
        for i, q in enumerate(confirmed_questions):
            info_requests.append(
                InfoRequestCreate(
                    phase=InfoRequestPhase.PRE_CALL,
                    created_by=InfoRequestCreator.CONSULTANT,
                    display_order=i,
                    title=q.question,
                    request_type=InfoRequestType.QUESTION,
                    input_type=InfoRequestInputType.TEXT,
                    priority=InfoRequestPriority.MEDIUM,
                    best_answered_by=q.best_answered_by,
                    why_asking=q.why_important,
                )
            )

        # Convert documents to info requests
        for i, d in enumerate(confirmed_documents):
            priority_map = {
                "high": InfoRequestPriority.HIGH,
                "medium": InfoRequestPriority.MEDIUM,
                "low": InfoRequestPriority.LOW,
            }
            info_requests.append(
                InfoRequestCreate(
                    phase=InfoRequestPhase.PRE_CALL,
                    created_by=InfoRequestCreator.CONSULTANT,
                    display_order=len(confirmed_questions) + i,
                    title=d.document_name,
                    request_type=InfoRequestType.DOCUMENT,
                    input_type=InfoRequestInputType.FILE,
                    priority=priority_map.get(d.priority.value, InfoRequestPriority.MEDIUM),
                    why_asking=d.why_important,
                )
            )

        # Create info requests in database
        await bulk_create_info_requests(project_id, info_requests)

        # Handle invitations if provided
        invitations_sent = 0
        if request and request.invite_emails:
            invitations_sent = await _send_invitations(project_id, request.invite_emails, auth)

        # Update bundle status
        await update_bundle_status(project_id, PrepStatus.SENT, sent_at=datetime.utcnow())

        return SendToPortalResponse(
            success=True,
            questions_sent=len(confirmed_questions),
            documents_sent=len(confirmed_documents),
            invitations_sent=invitations_sent,
            message=f"Sent {len(confirmed_questions)} questions and {len(confirmed_documents)} document requests to portal.",
        )

    except Exception as e:
        logger.error(f"Error sending to portal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send to portal: {str(e)}",
        )


@router.post("/{project_id}/regenerate-questions", response_model=DiscoveryPrepBundle)
async def regenerate_questions(
    project_id: UUID,
    auth: AuthContext = Depends(require_consultant),
):
    """Regenerate just the questions, keeping other bundle content."""
    from app.agents.discovery_prep import generate_prep_questions

    bundle = await get_bundle(project_id)
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No bundle found. Generate one first.",
        )

    # Generate new questions
    result = await generate_prep_questions(project_id)

    questions = [
        PrepQuestion(
            question=q.question,
            best_answered_by=q.best_answered_by,
            why_important=q.why_important,
        )
        for q in result.questions
    ]

    # Update bundle with new questions
    return await create_or_update_bundle(
        project_id=project_id,
        agenda_summary=bundle.agenda_summary or "",
        agenda_bullets=bundle.agenda_bullets,
        questions=questions,
        documents=bundle.documents,
    )


@router.post("/{project_id}/regenerate-documents", response_model=DiscoveryPrepBundle)
async def regenerate_documents(
    project_id: UUID,
    auth: AuthContext = Depends(require_consultant),
):
    """Regenerate just the document recommendations, keeping other bundle content."""
    from app.agents.discovery_prep import recommend_documents

    bundle = await get_bundle(project_id)
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No bundle found. Generate one first.",
        )

    # Generate new document recommendations
    result = await recommend_documents(project_id)

    documents = [
        DocRecommendation(
            document_name=d.document_name,
            priority=d.priority,
            why_important=d.why_important,
        )
        for d in result.documents
    ]

    # Update bundle with new documents
    return await create_or_update_bundle(
        project_id=project_id,
        agenda_summary=bundle.agenda_summary or "",
        agenda_bullets=bundle.agenda_bullets,
        questions=bundle.questions,
        documents=documents,
    )


@router.post("/{project_id}/regenerate-agenda", response_model=DiscoveryPrepBundle)
async def regenerate_agenda(
    project_id: UUID,
    auth: AuthContext = Depends(require_consultant),
):
    """Regenerate just the agenda, keeping questions and documents."""
    from app.agents.discovery_prep import generate_agenda
    from app.core.schemas_discovery_prep import PrepQuestionCreate

    bundle = await get_bundle(project_id)
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No bundle found. Generate one first.",
        )

    # Convert existing questions to create format for agenda agent
    questions_for_agenda = [
        PrepQuestionCreate(
            question=q.question,
            best_answered_by=q.best_answered_by,
            why_important=q.why_important,
        )
        for q in bundle.questions
    ]

    document_names = [d.document_name for d in bundle.documents]

    # Generate new agenda
    agenda_result = await generate_agenda(
        project_id,
        questions=questions_for_agenda,
        document_names=document_names,
    )

    # Update bundle with new agenda
    return await create_or_update_bundle(
        project_id=project_id,
        agenda_summary=agenda_result.summary,
        agenda_bullets=agenda_result.bullets,
        questions=bundle.questions,
        documents=bundle.documents,
    )


@router.delete("/{project_id}")
async def delete_discovery_prep(
    project_id: UUID,
    auth: AuthContext = Depends(require_consultant),
):
    """Delete a discovery prep bundle."""
    success = await delete_bundle(project_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bundle not found.",
        )
    return {"message": "Bundle deleted."}


# =============================================================================
# Helper Functions
# =============================================================================


async def _send_invitations(project_id: UUID, emails: list[str], auth: AuthContext) -> int:
    """Send portal invitations to stakeholders."""
    from app.core.schemas_auth import ClientInviteRequest, MemberRole, UserCreate, UserType
    from app.db.project_members import add_project_member
    from app.db.users import create_user, get_user_by_email
    from app.db.supabase_client import get_supabase

    invitations_sent = 0
    client = get_supabase()

    for email in emails:
        try:
            # Get or create user
            existing_user = await get_user_by_email(email)
            if existing_user:
                user = existing_user
            else:
                user = await create_user(
                    UserCreate(
                        email=email,
                        user_type=UserType.CLIENT,
                    )
                )

            # Add to project
            await add_project_member(
                project_id=project_id,
                user_id=user.id,
                role=MemberRole.CLIENT,
                invited_by=auth.user_id,
            )

            # Send magic link
            try:
                client.auth.sign_in_with_otp({
                    "email": email,
                    "options": {
                        "email_redirect_to": "http://localhost:3001/auth/verify",
                        "should_create_user": True,
                    },
                })
                invitations_sent += 1
            except Exception as e:
                logger.warning(f"Could not send magic link to {email}: {e}")

        except Exception as e:
            logger.error(f"Error inviting {email}: {e}")

    return invitations_sent
