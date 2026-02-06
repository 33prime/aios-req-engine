"""
Unified Signal Processor.

Single pipeline that replaces the mode-based split between extract_facts_graph
and surgical_update_graph. Handles all signals consistently:

1. Extract claims from signal
2. Match claims to existing entities via SimilarityMatcher
3. Route to CREATE or UPDATE based on similarity scores
4. Execute operations with versioning
5. Apply auto-confirmation based on signal authority
6. Queue enrichment for confirmed entities

Usage:
    from app.graphs.unified_processor import process_signal

    result = process_signal(
        signal_id=signal_id,
        project_id=project_id,
        run_id=run_id,
    )
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from pydantic import BaseModel

from app.core.logging import get_logger
from app.core.similarity import SimilarityMatcher, MatchResult, should_create_or_update
from app.core.entity_versioning import EntityVersioning, track_entity_update
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)

MAX_STEPS = 20  # Safety cap for linear pipeline (6 nodes + margin)

# =============================================================================
# Configuration
# =============================================================================

# Similarity thresholds for routing
CREATE_THRESHOLD = 0.50  # Below this, definitely create new
UPDATE_THRESHOLD = 0.80  # Above this, definitely update existing
# Between these = ambiguous, flag for review

# Authority levels that trigger auto-confirmation
AUTO_CONFIRM_AUTHORITIES = {"client", "consultant"}

# Entity types we process
ENTITY_TYPES = {"feature", "persona", "vp_step"}


# =============================================================================
# Data Models
# =============================================================================

class ExtractedClaim(BaseModel):
    """A claim extracted from a signal."""
    text: str
    entity_type_hint: str  # "feature", "persona", "vp_step", "unknown"
    confidence: float
    field_hints: dict[str, Any] = {}
    evidence_excerpt: str = ""


class MatchedClaim(BaseModel):
    """A claim with its entity match result."""
    claim: ExtractedClaim
    action: Literal["create", "update", "review"]
    match_result: dict[str, Any] | None = None
    matched_entity_id: str | None = None
    matched_entity_name: str | None = None
    similarity_score: float = 0.0


class ProcessedOperation(BaseModel):
    """Result of processing a single operation."""
    operation_type: Literal["create", "update", "skip", "review"]
    entity_type: str
    entity_id: str | None = None
    entity_name: str = ""
    changes_applied: dict[str, Any] = {}
    version_id: str | None = None
    error: str | None = None


class ProcessingResult(BaseModel):
    """Final result of signal processing."""
    signal_id: str
    project_id: str
    claims_extracted: int = 0
    entities_created: int = 0
    entities_updated: int = 0
    entities_flagged_for_review: int = 0
    operations: list[ProcessedOperation] = []
    enrichment_queued: list[str] = []
    success: bool = True
    error: str | None = None


# =============================================================================
# Graph State
# =============================================================================

@dataclass
class UnifiedProcessorState:
    """State for the unified processor graph."""

    # Input
    signal_id: UUID
    project_id: UUID
    run_id: UUID

    # Loaded data
    signal: dict[str, Any] | None = None
    signal_authority: str = "unknown"
    existing_entities: dict[str, list[dict]] = field(default_factory=dict)

    # Processing
    extracted_claims: list[ExtractedClaim] = field(default_factory=list)
    matched_claims: list[MatchedClaim] = field(default_factory=list)
    operations: list[ProcessedOperation] = field(default_factory=list)
    enrichment_queue: list[str] = field(default_factory=list)

    # Counters
    created_count: int = 0
    updated_count: int = 0
    review_count: int = 0
    step_count: int = 0

    # Status
    success: bool = True
    error: str | None = None


# =============================================================================
# Node Functions
# =============================================================================

def _check_max_steps(state: UnifiedProcessorState) -> UnifiedProcessorState:
    """Check and increment step count, raise if exceeded."""
    state.step_count += 1
    if state.step_count > MAX_STEPS:
        raise RuntimeError(f"Graph exceeded max steps ({MAX_STEPS})")
    return state


def load_signal(state: UnifiedProcessorState) -> dict[str, Any]:
    """Load signal data from database."""
    state = _check_max_steps(state)
    logger.info(
        f"Loading signal {state.signal_id}",
        extra={"run_id": str(state.run_id)},
    )

    supabase = get_supabase()
    response = (
        supabase.table("signals")
        .select("*")
        .eq("id", str(state.signal_id))
        .single()
        .execute()
    )

    if not response.data:
        return {
            "error": f"Signal {state.signal_id} not found",
            "success": False,
        }

    signal = response.data
    metadata = signal.get("metadata", {}) or {}
    authority = metadata.get("authority", "unknown")

    logger.info(
        f"Loaded signal with authority '{authority}'",
        extra={"run_id": str(state.run_id), "signal_type": signal.get("signal_type")},
    )

    return {
        "signal": signal,
        "signal_authority": authority,
    }


def load_existing_entities(state: UnifiedProcessorState) -> dict[str, Any]:
    """Load all existing entities for similarity matching."""
    if not state.signal:
        return {"error": "No signal loaded", "success": False}

    logger.info(
        f"Loading existing entities for project {state.project_id}",
        extra={"run_id": str(state.run_id)},
    )

    supabase = get_supabase()
    entities = {}

    # Load features
    features_response = (
        supabase.table("features")
        .select("id, name, slug, confirmation_status, details")
        .eq("project_id", str(state.project_id))
        .execute()
    )
    entities["feature"] = features_response.data or []

    # Load personas
    personas_response = (
        supabase.table("personas")
        .select("id, name, slug, confirmation_status, role, goals")
        .eq("project_id", str(state.project_id))
        .execute()
    )
    entities["persona"] = personas_response.data or []

    # Load VP steps
    vp_response = (
        supabase.table("vp_steps")
        .select("id, name, slug, confirmation_status, step_index, description")
        .eq("project_id", str(state.project_id))
        .execute()
    )
    entities["vp_step"] = vp_response.data or []

    logger.info(
        f"Loaded {len(entities['feature'])} features, "
        f"{len(entities['persona'])} personas, "
        f"{len(entities['vp_step'])} VP steps",
        extra={"run_id": str(state.run_id)},
    )

    return {"existing_entities": entities}


def extract_claims(state: UnifiedProcessorState) -> dict[str, Any]:
    """Extract claims from signal using LLM."""
    if not state.signal:
        return {"error": "No signal loaded", "success": False}

    logger.info(
        f"Extracting claims from signal {state.signal_id}",
        extra={"run_id": str(state.run_id)},
    )

    signal_text = state.signal.get("raw_text", "")
    if not signal_text:
        logger.warning("Signal has no text content")
        return {"extracted_claims": []}

    # Call LLM to extract claims
    try:
        claims = _extract_claims_llm(
            signal_text=signal_text,
            signal_type=state.signal.get("signal_type", "note"),
            existing_entities=state.existing_entities,
            run_id=state.run_id,
        )

        logger.info(
            f"Extracted {len(claims)} claims from signal",
            extra={"run_id": str(state.run_id)},
        )

        return {"extracted_claims": claims}

    except Exception as e:
        logger.error(f"Claim extraction failed: {e}", extra={"run_id": str(state.run_id)})
        return {"extracted_claims": [], "error": str(e)}


def match_claims_to_entities(state: UnifiedProcessorState) -> dict[str, Any]:
    """Match extracted claims to existing entities using SimilarityMatcher."""
    if not state.extracted_claims:
        return {"matched_claims": []}

    logger.info(
        f"Matching {len(state.extracted_claims)} claims to entities",
        extra={"run_id": str(state.run_id)},
    )

    matched_claims = []

    for claim in state.extracted_claims:
        entity_type = claim.entity_type_hint
        if entity_type not in ENTITY_TYPES:
            entity_type = "feature"  # Default to feature

        existing = state.existing_entities.get(entity_type, [])

        if not existing:
            # No existing entities of this type, must create
            matched_claims.append(MatchedClaim(
                claim=claim,
                action="create",
                similarity_score=0.0,
            ))
            continue

        # Use similarity matcher to find best match
        action, match_result = should_create_or_update(
            candidate_name=claim.text[:100],  # Use first 100 chars as name
            existing_entities=existing,
            entity_type=entity_type,
        )

        matched_claims.append(MatchedClaim(
            claim=claim,
            action=action,
            match_result=match_result.to_dict() if hasattr(match_result, 'to_dict') else None,
            matched_entity_id=match_result.matched_id,
            matched_entity_name=match_result.matched_item.get("name") if match_result.matched_item else None,
            similarity_score=match_result.score,
        ))

    # Log summary
    creates = sum(1 for m in matched_claims if m.action == "create")
    updates = sum(1 for m in matched_claims if m.action == "update")
    reviews = sum(1 for m in matched_claims if m.action == "review")

    logger.info(
        f"Routing: {creates} creates, {updates} updates, {reviews} reviews",
        extra={"run_id": str(state.run_id)},
    )

    return {"matched_claims": matched_claims}


def execute_operations(state: UnifiedProcessorState) -> dict[str, Any]:
    """Execute create/update operations for matched claims."""
    if not state.matched_claims:
        return {"operations": []}

    logger.info(
        f"Executing {len(state.matched_claims)} operations",
        extra={"run_id": str(state.run_id)},
    )

    operations = []
    created_count = 0
    updated_count = 0
    review_count = 0
    enrichment_queue = []

    versioning = EntityVersioning()

    for matched in state.matched_claims:
        claim = matched.claim
        entity_type = claim.entity_type_hint if claim.entity_type_hint in ENTITY_TYPES else "feature"

        # Determine confirmation status based on authority
        confirmation_status = _get_confirmation_status(state.signal_authority)

        try:
            if matched.action == "create":
                # Create new entity
                result = _create_entity(
                    entity_type=entity_type,
                    claim=claim,
                    project_id=state.project_id,
                    signal_id=state.signal_id,
                    confirmation_status=confirmation_status,
                    versioning=versioning,
                )
                operations.append(result)
                if result.operation_type == "create":
                    created_count += 1
                    # Queue for enrichment if confirmed
                    if confirmation_status in {"confirmed_client", "confirmed_consultant"}:
                        enrichment_queue.append(f"{entity_type}:{result.entity_id}")

            elif matched.action == "update":
                # Update existing entity
                result = _update_entity(
                    entity_type=entity_type,
                    entity_id=matched.matched_entity_id,
                    claim=claim,
                    signal_id=state.signal_id,
                    versioning=versioning,
                )
                operations.append(result)
                if result.operation_type == "update":
                    updated_count += 1

            else:
                # Flag for review
                operations.append(ProcessedOperation(
                    operation_type="review",
                    entity_type=entity_type,
                    entity_name=claim.text[:50],
                    changes_applied={"claim": claim.text, "candidates": matched.match_result},
                ))
                review_count += 1

        except Exception as e:
            logger.error(f"Operation failed: {e}", extra={"run_id": str(state.run_id)})
            operations.append(ProcessedOperation(
                operation_type="skip",
                entity_type=entity_type,
                entity_name=claim.text[:50],
                error=str(e),
            ))

    return {
        "operations": operations,
        "created_count": created_count,
        "updated_count": updated_count,
        "review_count": review_count,
        "enrichment_queue": enrichment_queue,
    }


def queue_enrichment(state: UnifiedProcessorState) -> dict[str, Any]:
    """Queue confirmed entities for auto-enrichment."""
    if not state.enrichment_queue:
        return {}

    logger.info(
        f"Queueing {len(state.enrichment_queue)} entities for enrichment",
        extra={"run_id": str(state.run_id)},
    )

    # Insert into enrichment queue table (if exists) or log for processing
    supabase = get_supabase()

    for item in state.enrichment_queue:
        entity_type, entity_id = item.split(":", 1)
        try:
            supabase.table("enrichment_queue").insert({
                "project_id": str(state.project_id),
                "entity_type": entity_type,
                "entity_id": entity_id,
                "status": "pending",
                "priority": 5,
            }).execute()
        except Exception as e:
            # Table might not exist yet, just log
            logger.debug(f"Could not queue enrichment: {e}")

    return {"success": True}


# =============================================================================
# Helper Functions
# =============================================================================

def _extract_claims_llm(
    signal_text: str,
    signal_type: str,
    existing_entities: dict[str, list[dict]],
    run_id: UUID,
) -> list[ExtractedClaim]:
    """Extract claims from signal text using LLM."""
    from langchain_core.messages import SystemMessage
    from langchain_core.output_parsers import JsonOutputParser
    from langchain_core.prompts import ChatPromptTemplate

    from app.core.llm import get_llm

    # Build entity context for LLM
    entity_context = _build_entity_context(existing_entities)

    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=CLAIM_EXTRACTION_PROMPT),
        ("user", CLAIM_EXTRACTION_USER_TEMPLATE),
    ])

    llm = get_llm(model="gpt-4o", temperature=0.1)
    parser = JsonOutputParser()
    chain = prompt | llm | parser

    result = chain.invoke({
        "signal_text": signal_text[:8000],  # Limit text length
        "signal_type": signal_type,
        "entity_context": entity_context,
    })

    claims = []
    for item in result:
        try:
            claims.append(ExtractedClaim(
                text=item.get("text", ""),
                entity_type_hint=item.get("entity_type", "feature"),
                confidence=item.get("confidence", 0.7),
                field_hints=item.get("fields", {}),
                evidence_excerpt=item.get("evidence", ""),
            ))
        except Exception as e:
            logger.warning(f"Failed to parse claim: {e}")

    return claims


def _build_entity_context(existing_entities: dict[str, list[dict]]) -> str:
    """Build entity context string for LLM prompt."""
    lines = []

    for entity_type, entities in existing_entities.items():
        if not entities:
            continue

        lines.append(f"\n## Existing {entity_type}s:")
        for e in entities[:20]:  # Limit to 20 per type
            name = e.get("name", e.get("slug", "unknown"))
            status = e.get("confirmation_status", "")
            lines.append(f"- {name} (id: {e.get('id')}) [{status}]")

    return "\n".join(lines) if lines else "(No existing entities)"


def _get_confirmation_status(authority: str) -> str:
    """Determine confirmation status based on signal authority."""
    if authority == "client":
        return "confirmed_client"
    elif authority == "consultant":
        return "confirmed_consultant"
    else:
        return "ai_generated"


def _create_entity(
    entity_type: str,
    claim: ExtractedClaim,
    project_id: UUID,
    signal_id: UUID,
    confirmation_status: str,
    versioning: EntityVersioning,
) -> ProcessedOperation:
    """Create a new entity from a claim."""
    supabase = get_supabase()

    # Generate slug from claim text
    import re
    name = claim.text[:100].strip()
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower())[:50]

    try:
        if entity_type == "feature":
            from app.db.features import create_feature
            entity = create_feature(
                project_id=project_id,
                name=name,
                slug=slug,
                confirmation_status=confirmation_status,
            )
        elif entity_type == "persona":
            from app.db.personas import create_persona
            entity = create_persona(
                project_id=project_id,
                name=name,
                slug=slug,
                confirmation_status=confirmation_status,
            )
        elif entity_type == "vp_step":
            from app.db.vp import create_vp_step
            # Get next step index
            existing = supabase.table("vp_steps").select("step_index").eq(
                "project_id", str(project_id)
            ).order("step_index", desc=True).limit(1).execute()
            next_index = (existing.data[0]["step_index"] + 1) if existing.data else 1

            entity = create_vp_step(
                project_id=project_id,
                name=name,
                slug=slug,
                step_index=next_index,
                confirmation_status=confirmation_status,
            )
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")

        # Create version snapshot
        version_id = versioning.create_snapshot(
            entity_type=entity_type,
            entity_id=entity["id"],
            entity_data=entity,
            trigger_event="unified_processor_create",
            source_signal_id=signal_id,
        )

        # Record field attribution
        versioning.record_field_attribution(
            entity_type=entity_type,
            entity_id=entity["id"],
            field_path="name",
            signal_id=signal_id,
        )

        return ProcessedOperation(
            operation_type="create",
            entity_type=entity_type,
            entity_id=entity["id"],
            entity_name=name,
            changes_applied={"name": name, "confirmation_status": confirmation_status},
            version_id=version_id,
        )

    except Exception as e:
        return ProcessedOperation(
            operation_type="skip",
            entity_type=entity_type,
            entity_name=name,
            error=str(e),
        )


def _update_entity(
    entity_type: str,
    entity_id: str,
    claim: ExtractedClaim,
    signal_id: UUID,
    versioning: EntityVersioning,
) -> ProcessedOperation:
    """Update an existing entity with claim data."""
    try:
        # Load current entity
        if entity_type == "feature":
            from app.db.features import get_feature, update_feature
            entity = get_feature(UUID(entity_id))
            if not entity:
                raise ValueError(f"Feature {entity_id} not found")

            # Update details with claim info
            details = entity.get("details", {}) or {}
            if claim.field_hints:
                for field, value in claim.field_hints.items():
                    if field in details:
                        # Append to existing
                        if isinstance(details[field], list):
                            details[field].append(value)
                        else:
                            details[field] = value
                    else:
                        details[field] = value

            # Add claim as note
            notes = details.get("notes", []) or []
            notes.append(f"[Signal] {claim.text[:200]}")
            details["notes"] = notes

            old_data = entity.copy()
            update_feature(UUID(entity_id), {"details": details})
            entity["details"] = details

        elif entity_type == "persona":
            from app.db.personas import get_persona, update_persona
            entity = get_persona(UUID(entity_id))
            if not entity:
                raise ValueError(f"Persona {entity_id} not found")

            old_data = entity.copy()
            # Add claim to goals or pain_points based on content
            updates = {}
            if "goal" in claim.text.lower() or "want" in claim.text.lower():
                goals = entity.get("goals", []) or []
                goals.append(claim.text[:200])
                updates["goals"] = goals
            else:
                pain_points = entity.get("pain_points", []) or []
                pain_points.append(claim.text[:200])
                updates["pain_points"] = pain_points

            update_persona(UUID(entity_id), updates)
            entity.update(updates)

        elif entity_type == "vp_step":
            from app.db.vp import get_vp_step, update_vp_step
            entity = get_vp_step(UUID(entity_id))
            if not entity:
                raise ValueError(f"VP step {entity_id} not found")

            old_data = entity.copy()
            # Append to description or notes
            description = entity.get("description", "") or ""
            description += f"\n\n[Update] {claim.text[:300]}"
            update_vp_step(UUID(entity_id), {"description": description.strip()})
            entity["description"] = description.strip()

        else:
            raise ValueError(f"Unknown entity type: {entity_type}")

        # Track version
        version_id = track_entity_update(
            entity_type=entity_type,
            entity_id=entity_id,
            old_data=old_data,
            new_data=entity,
            trigger_event="unified_processor_update",
            source_signal_id=signal_id,
        )

        return ProcessedOperation(
            operation_type="update",
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity.get("name", ""),
            changes_applied={"claim_applied": claim.text[:100]},
            version_id=version_id,
        )

    except Exception as e:
        return ProcessedOperation(
            operation_type="skip",
            entity_type=entity_type,
            entity_id=entity_id,
            error=str(e),
        )


# =============================================================================
# LLM Prompts
# =============================================================================

CLAIM_EXTRACTION_PROMPT = """You are a requirements analyst extracting structured claims from product signals.

Your task is to identify specific, actionable claims about product requirements.

# Entity Types
- **feature**: A product capability or function
- **persona**: A user type or role
- **vp_step**: A step in the user's value path/journey

# Output Format
Return a JSON array of claims:
```json
[
  {
    "text": "The survey builder needs data validation",
    "entity_type": "feature",
    "confidence": 0.9,
    "fields": {"acceptance_criteria": "validate text inputs"},
    "evidence": "We need to validate that survey text answers..."
  }
]
```

# Rules
- Extract ONLY claims with clear evidence from the signal
- Each claim should be atomic (one concept)
- Set entity_type based on what's being described
- Include field hints if the claim specifies details
- Confidence should reflect clarity of the statement
"""

CLAIM_EXTRACTION_USER_TEMPLATE = """# Signal Type
{signal_type}

# Signal Content
{signal_text}

# Existing Entities (for context)
{entity_context}

# Task
Extract all actionable claims from this signal.
Return JSON array of claims."""


# =============================================================================
# Build Graph
# =============================================================================

def build_unified_processor_graph() -> StateGraph:
    """Build the unified processor graph."""
    from langgraph.graph import StateGraph

    # Convert dataclass to work with LangGraph
    graph = StateGraph(UnifiedProcessorState)

    # Add nodes
    graph.add_node("load_signal", load_signal)
    graph.add_node("load_existing_entities", load_existing_entities)
    graph.add_node("extract_claims", extract_claims)
    graph.add_node("match_claims", match_claims_to_entities)
    graph.add_node("execute_operations", execute_operations)
    graph.add_node("queue_enrichment", queue_enrichment)

    # Add edges
    graph.set_entry_point("load_signal")
    graph.add_edge("load_signal", "load_existing_entities")
    graph.add_edge("load_existing_entities", "extract_claims")
    graph.add_edge("extract_claims", "match_claims")
    graph.add_edge("match_claims", "execute_operations")
    graph.add_edge("execute_operations", "queue_enrichment")
    graph.add_edge("queue_enrichment", END)

    return graph.compile(checkpointer=MemorySaver())


# =============================================================================
# Main Entry Point
# =============================================================================

def process_signal(
    signal_id: UUID,
    project_id: UUID,
    run_id: UUID,
) -> ProcessingResult:
    """
    Process a signal through the unified pipeline.

    Args:
        signal_id: Signal UUID
        project_id: Project UUID
        run_id: Run tracking UUID

    Returns:
        ProcessingResult with all operations performed
    """
    logger.info(
        f"Starting unified signal processing for {signal_id}",
        extra={"run_id": str(run_id), "project_id": str(project_id)},
    )

    graph = build_unified_processor_graph()

    initial_state = UnifiedProcessorState(
        signal_id=signal_id,
        project_id=project_id,
        run_id=run_id,
    )

    try:
        config = {"configurable": {"thread_id": str(run_id)}}
        final_state = graph.invoke(initial_state, config=config)

        result = ProcessingResult(
            signal_id=str(signal_id),
            project_id=str(project_id),
            claims_extracted=len(final_state.extracted_claims),
            entities_created=final_state.created_count,
            entities_updated=final_state.updated_count,
            entities_flagged_for_review=final_state.review_count,
            operations=final_state.operations,
            enrichment_queued=final_state.enrichment_queue,
            success=final_state.success,
            error=final_state.error,
        )

        logger.info(
            f"Unified processing complete: {result.entities_created} created, "
            f"{result.entities_updated} updated, {result.entities_flagged_for_review} for review",
            extra={"run_id": str(run_id)},
        )

        return result

    except Exception as e:
        logger.exception(f"Unified processing failed: {e}", extra={"run_id": str(run_id)})
        return ProcessingResult(
            signal_id=str(signal_id),
            project_id=str(project_id),
            success=False,
            error=str(e),
        )


# =============================================================================
# Convenience Functions
# =============================================================================

async def process_signal_async(
    signal_id: UUID,
    project_id: UUID,
    run_id: UUID,
) -> ProcessingResult:
    """Async wrapper for process_signal."""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(
            pool,
            lambda: process_signal(signal_id, project_id, run_id)
        )
    return result
