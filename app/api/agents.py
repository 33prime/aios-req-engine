"""API endpoints for LangGraph agents."""

from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.core.replay_policy import (
    make_replay_input_for_extract_facts,
    make_replay_output_for_extract_facts,
)
from app.core.schemas_facts import (
    ExtractFactsRequest,
    ExtractFactsResponse,
    ReplayRequest,
)
from app.db.agent_runs import (
    complete_agent_run,
    create_agent_run,
    fail_agent_run,
    get_agent_run,
    start_agent_run,
)
from app.db.jobs import complete_job, create_job, fail_job, start_job
from app.db.signals import get_signal
from app.graphs.extract_facts_graph import run_extract_facts

logger = get_logger(__name__)

router = APIRouter()


@router.post("/extract-facts", response_model=ExtractFactsResponse)
async def extract_facts(request: ExtractFactsRequest) -> ExtractFactsResponse:
    """
    Extract structured facts from a signal.

    This endpoint:
    1. Creates a job for tracking
    2. Validates project_id if provided
    3. Runs the extract_facts LangGraph agent
    4. Persists results to extracted_facts table
    5. Returns summary and counts

    Args:
        request: ExtractFactsRequest with signal_id and optional project_id/top_chunks

    Returns:
        ExtractFactsResponse with extraction results

    Raises:
        HTTPException 400: If project_id doesn't match signal
        HTTPException 500: If extraction fails
    """
    run_id = uuid4()
    job_id: UUID | None = None
    agent_run_id: UUID | None = None

    try:
        # Create job
        job_id = create_job(
            project_id=request.project_id,
            job_type="extract_facts",
            input_json=request.model_dump(mode="json"),
            run_id=run_id,
        )

        # Create agent run for replay/audit
        agent_run_id = create_agent_run(
            agent_name="extract_facts",
            project_id=request.project_id,
            signal_id=request.signal_id,
            run_id=run_id,
            job_id=job_id,
            input_json=make_replay_input_for_extract_facts(request, signal_id=request.signal_id),
        )

        start_job(job_id)
        start_agent_run(agent_run_id)

        logger.info(
            f"Starting extract_facts for signal {request.signal_id}",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "agent_run_id": str(agent_run_id),
            },
        )

        # Validate project_id if provided
        if request.project_id is not None:
            signal = get_signal(request.signal_id)
            signal_project_id = signal.get("project_id")

            if signal_project_id and str(request.project_id) != str(signal_project_id):
                fail_job(job_id, "project_id does not match signal")
                if agent_run_id:
                    fail_agent_run(agent_run_id, "project_id does not match signal")
                raise HTTPException(
                    status_code=400,
                    detail="project_id does not match signal",
                )

        # Run the graph
        llm_output, extracted_facts_id, actual_project_id = run_extract_facts(
            signal_id=request.signal_id,
            project_id=request.project_id,
            job_id=job_id,
            run_id=run_id,
            top_chunks=request.top_chunks,
        )

        # Build response
        response = ExtractFactsResponse(
            run_id=run_id,
            job_id=job_id,
            extracted_facts_id=extracted_facts_id,
            summary=llm_output.summary,
            facts_count=len(llm_output.facts),
            open_questions_count=len(llm_output.open_questions),
            contradictions_count=len(llm_output.contradictions),
        )

        # Complete agent run with replay output
        if agent_run_id:
            complete_agent_run(
                agent_run_id,
                make_replay_output_for_extract_facts(response, llm_output),
            )

        # Complete job
        complete_job(
            job_id,
            {
                "extracted_facts_id": str(extracted_facts_id),
                "facts_count": len(llm_output.facts),
                "open_questions_count": len(llm_output.open_questions),
                "contradictions_count": len(llm_output.contradictions),
            },
        )

        logger.info(
            "Completed extract_facts",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "agent_run_id": str(agent_run_id) if agent_run_id else None,
                "extracted_facts_id": str(extracted_facts_id),
            },
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception(
            f"Extract facts failed: {e}",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id) if job_id else None,
                "agent_run_id": str(agent_run_id) if agent_run_id else None,
            },
        )
        if agent_run_id:
            fail_agent_run(agent_run_id, str(e))
        if job_id:
            fail_job(job_id, str(e))
        raise HTTPException(status_code=500, detail="Extract facts failed") from e


@router.post("/replay/{agent_run_id}", response_model=ExtractFactsResponse)
async def replay_agent_run(
    agent_run_id: UUID, replay_request: ReplayRequest | None = None
) -> ExtractFactsResponse:
    """
    Replay a previous agent run with optional overrides.

    This endpoint:
    1. Loads the original agent_run record
    2. Validates agent_name (only extract_facts supported)
    3. Reconstructs the request from stored input
    4. Applies any overrides (model, top_chunks)
    5. Creates NEW job + NEW agent_run (preserves audit trail)
    6. Runs the agent with overrides
    7. Returns results

    Args:
        agent_run_id: UUID of the agent run to replay
        replay_request: Optional overrides for model and chunk count

    Returns:
        ExtractFactsResponse for the NEW run

    Raises:
        HTTPException 400: If agent_name not supported or validation fails
        HTTPException 404: If agent_run not found
        HTTPException 500: If replay fails
    """
    run_id = uuid4()
    job_id: UUID | None = None
    new_agent_run_id: UUID | None = None

    # Default to empty request if none provided
    if replay_request is None:
        replay_request = ReplayRequest()

    try:
        # Load original agent run
        try:
            original_run = get_agent_run(agent_run_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e

        # Validate agent name
        if original_run["agent_name"] != "extract_facts":
            raise HTTPException(
                status_code=400,
                detail=f"Replay not supported for agent: {original_run['agent_name']}",
            )

        # Reconstruct request from stored input
        input_data = original_run["input"]
        signal_id = UUID(input_data["signal_id"])
        project_id = UUID(input_data["project_id"]) if input_data.get("project_id") else None
        top_chunks = input_data.get("top_chunks")

        # Apply overrides
        if replay_request.override_top_chunks is not None:
            top_chunks = replay_request.override_top_chunks

        # Build replay input with replay_of marker
        replay_input = {
            "signal_id": str(signal_id),
            "project_id": str(project_id) if project_id else None,
            "top_chunks": top_chunks,
            "replay_of": str(agent_run_id),
        }

        # Create NEW job for replay
        job_id = create_job(
            project_id=project_id,
            job_type="extract_facts",
            input_json=replay_input,
            run_id=run_id,
        )

        # Create NEW agent run for replay
        new_agent_run_id = create_agent_run(
            agent_name="extract_facts",
            project_id=project_id,
            signal_id=signal_id,
            run_id=run_id,
            job_id=job_id,
            input_json=replay_input,
        )

        start_job(job_id)
        start_agent_run(new_agent_run_id)

        logger.info(
            f"Replaying agent_run {agent_run_id} as new run {new_agent_run_id}",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "agent_run_id": str(new_agent_run_id),
                "original_agent_run_id": str(agent_run_id),
            },
        )

        # Validate project_id if provided
        if project_id is not None:
            signal = get_signal(signal_id)
            signal_project_id = signal.get("project_id")

            if signal_project_id and str(project_id) != str(signal_project_id):
                fail_job(job_id, "project_id does not match signal")
                if new_agent_run_id:
                    fail_agent_run(new_agent_run_id, "project_id does not match signal")
                raise HTTPException(
                    status_code=400,
                    detail="project_id does not match signal",
                )

        # Run the graph with optional model override
        llm_output, extracted_facts_id, actual_project_id = run_extract_facts(
            signal_id=signal_id,
            project_id=project_id,
            job_id=job_id,
            run_id=run_id,
            top_chunks=top_chunks,
            model_override=replay_request.override_model,
        )

        # Build response
        response = ExtractFactsResponse(
            run_id=run_id,
            job_id=job_id,
            extracted_facts_id=extracted_facts_id,
            summary=llm_output.summary,
            facts_count=len(llm_output.facts),
            open_questions_count=len(llm_output.open_questions),
            contradictions_count=len(llm_output.contradictions),
        )

        # Complete agent run with replay output (includes replay_of marker)
        if new_agent_run_id:
            replay_output = make_replay_output_for_extract_facts(response, llm_output)
            replay_output["replay_of"] = str(agent_run_id)
            complete_agent_run(new_agent_run_id, replay_output)

        # Complete job
        complete_job(
            job_id,
            {
                "extracted_facts_id": str(extracted_facts_id),
                "facts_count": len(llm_output.facts),
                "open_questions_count": len(llm_output.open_questions),
                "contradictions_count": len(llm_output.contradictions),
                "replay_of": str(agent_run_id),
            },
        )

        logger.info(
            "Completed replay",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id),
                "agent_run_id": str(new_agent_run_id) if new_agent_run_id else None,
                "original_agent_run_id": str(agent_run_id),
                "extracted_facts_id": str(extracted_facts_id),
            },
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception(
            f"Replay failed: {e}",
            extra={
                "run_id": str(run_id),
                "job_id": str(job_id) if job_id else None,
                "agent_run_id": str(new_agent_run_id) if new_agent_run_id else None,
                "original_agent_run_id": str(agent_run_id),
            },
        )
        if new_agent_run_id:
            fail_agent_run(new_agent_run_id, str(e))
        if job_id:
            fail_job(job_id, str(e))
        raise HTTPException(status_code=500, detail="Replay failed") from e
