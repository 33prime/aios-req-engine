"""Memory compaction using Claude Haiku.

Keeps memory lean while preserving critical information.
Token threshold triggers compaction, landmarks are auto-detected and preserved.
"""

import re
from typing import Any
from uuid import UUID

from anthropic import Anthropic

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Use Haiku for compaction - fast and cheap
COMPACTION_MODEL = "claude-3-5-haiku-20241022"

# Token thresholds
MAX_MEMORY_TOKENS = 2000  # Trigger compaction above this
TARGET_MEMORY_TOKENS = 800  # Target after compaction
CHARS_PER_TOKEN = 4  # Rough estimate


def estimate_tokens(text: str) -> int:
    """Estimate token count from text length."""
    return len(text) // CHARS_PER_TOKEN


def should_compact(memory_content: str) -> bool:
    """Check if memory needs compaction."""
    tokens = estimate_tokens(memory_content)
    return tokens > MAX_MEMORY_TOKENS


# =============================================================================
# Landmark Detection
# =============================================================================

LANDMARK_KEYWORDS = [
    "pivot", "pivoted", "changed direction", "major decision",
    "decided against", "removed", "cancelled", "strategic",
    "architecture", "tech stack", "framework", "platform",
    "launch", "release", "milestone", "phase",
    "client approved", "client rejected", "budget", "timeline",
    "scope change", "requirements change",
]

LANDMARK_DECISION_TYPES = [
    "initialization", "architecture", "strategic", "scope", "pivot",
]


def is_landmark_decision(decision: dict) -> bool:
    """
    Auto-detect if a decision is a landmark that should never be compacted.

    Landmarks are detected by:
    - Decision type (initialization, architecture, strategic)
    - High confidence (> 0.9)
    - Keywords in title/decision text
    - Affects multiple entity types
    - Explicitly marked as landmark
    """
    # Explicitly marked
    if decision.get("is_landmark"):
        return True

    # Decision type
    if decision.get("decision_type") in LANDMARK_DECISION_TYPES:
        return True

    # High confidence
    if (decision.get("confidence") or 0) >= 0.9:
        return True

    # Keyword detection
    text = f"{decision.get('title', '')} {decision.get('decision', '')}".lower()
    for keyword in LANDMARK_KEYWORDS:
        if keyword in text:
            return True

    # Affects multiple gates/entities
    affects = decision.get("affects_gates") or []
    if len(affects) >= 2:
        return True

    return False


def detect_landmarks(decisions: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Separate decisions into landmarks and regular decisions.

    Returns:
        (landmarks, regular_decisions)
    """
    landmarks = []
    regular = []

    for d in decisions:
        if is_landmark_decision(d):
            landmarks.append(d)
        else:
            regular.append(d)

    # Always keep the first decision (project init) as landmark
    if regular and not landmarks:
        landmarks.append(regular.pop(0))

    return landmarks, regular


# =============================================================================
# Pre-filtering (No LLM - Free)
# =============================================================================

def prefilter_content(content: str) -> str:
    """
    Apply heuristic pre-filtering to reduce content before LLM compaction.
    This is free (no API calls) and catches obvious redundancy.
    """
    lines = content.split('\n')
    filtered_lines = []
    seen_decisions = set()

    for line in lines:
        # Skip empty lines in sequences
        if not line.strip() and filtered_lines and not filtered_lines[-1].strip():
            continue

        # Dedupe repeated decision titles
        if line.strip().startswith('###') or line.strip().startswith('**['):
            normalized = re.sub(r'\d{4}-\d{2}-\d{2}', 'DATE', line.lower())
            if normalized in seen_decisions:
                continue
            seen_decisions.add(normalized)

        # Trim excessive whitespace
        line = re.sub(r'  +', ' ', line)

        filtered_lines.append(line)

    return '\n'.join(filtered_lines)


# =============================================================================
# LLM Compaction
# =============================================================================

COMPACTION_PROMPT = """You are compacting project memory to stay within token limits while preserving critical information.

## Rules

1. PRESERVE exactly:
   - Project name and core problem statement
   - All landmark decisions (marked with [LANDMARK])
   - Names of features, personas, and value path steps
   - Open questions
   - Current focus/priorities

2. COMPRESS:
   - Verbose rationale → key point only
   - Multiple similar learnings → single insight
   - Historical decisions → one-line summaries
   - Resolved questions → brief mention or remove

3. STRUCTURE (keep this exact format):
   ```
   # Project Memory: {name}

   ## Overview
   {1-2 sentences: what, why, for whom}

   ## Key Entities
   - Features: {comma-separated names}
   - Personas: {comma-separated names}
   - Value Path: {step count} steps defined

   ## Landmark Decisions
   {keep these in full}

   ## Recent Decisions
   {last 3-5 as one-liners}

   ## Key Learnings
   {3-5 bullet points max}

   ## Current Focus
   {what's active now}

   ## Open Questions
   {unresolved items}
   ```

4. TARGET: ~{target_tokens} tokens (currently ~{current_tokens})

## Current Memory to Compact

{memory_content}

## Landmark Decisions (MUST preserve in full)

{landmarks}

## Output

Return ONLY the compacted memory document, no explanations."""


def compact_with_llm(
    memory_content: str,
    landmarks: list[dict],
    target_tokens: int = TARGET_MEMORY_TOKENS,
) -> str:
    """
    Use Haiku to intelligently compact memory.

    Args:
        memory_content: Current memory content
        landmarks: Decisions that must be preserved in full
        target_tokens: Target token count after compaction

    Returns:
        Compacted memory content
    """
    settings = get_settings()
    current_tokens = estimate_tokens(memory_content)

    # Format landmarks for preservation
    landmark_text = ""
    if landmarks:
        landmark_parts = []
        for d in landmarks:
            date = d.get("created_at", "")[:10] if d.get("created_at") else "Unknown"
            landmark_parts.append(
                f"[LANDMARK] {date}: {d.get('title', 'Decision')}\n"
                f"- Decision: {d.get('decision', '')}\n"
                f"- Rationale: {d.get('rationale', '')}"
            )
        landmark_text = "\n\n".join(landmark_parts)
    else:
        landmark_text = "No landmarks identified."

    prompt = COMPACTION_PROMPT.format(
        target_tokens=target_tokens,
        current_tokens=current_tokens,
        memory_content=memory_content,
        landmarks=landmark_text,
    )

    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    logger.info(f"Compacting memory: {current_tokens} tokens → target {target_tokens}")

    response = client.messages.create(
        model=COMPACTION_MODEL,
        max_tokens=target_tokens * 2,  # Allow some headroom
        messages=[{"role": "user", "content": prompt}],
    )

    compacted = response.content[0].text if response.content else memory_content
    new_tokens = estimate_tokens(compacted)

    logger.info(f"Memory compacted: {current_tokens} → {new_tokens} tokens ({100 - (new_tokens * 100 // current_tokens)}% reduction)")

    return compacted


# =============================================================================
# Main Compaction Function
# =============================================================================

def compact_memory(project_id: UUID) -> dict[str, Any]:
    """
    Compact project memory if it exceeds the token threshold.

    Flow:
    1. Check if compaction needed
    2. Fetch current memory and decisions
    3. Auto-detect landmark decisions
    4. Pre-filter (free heuristics)
    5. LLM compaction (Haiku)
    6. Save compacted memory

    Args:
        project_id: Project UUID

    Returns:
        dict with compaction results
    """
    from app.db.project_memory import (
        get_project_memory,
        get_recent_decisions,
        update_project_memory,
    )

    # Get current memory
    memory = get_project_memory(project_id)
    if not memory:
        return {"compacted": False, "reason": "No memory exists"}

    content = memory.get("content", "")
    if not content:
        return {"compacted": False, "reason": "Memory is empty"}

    # Check if compaction needed
    current_tokens = estimate_tokens(content)
    if current_tokens <= MAX_MEMORY_TOKENS:
        return {
            "compacted": False,
            "reason": f"Below threshold ({current_tokens} <= {MAX_MEMORY_TOKENS})",
            "current_tokens": current_tokens,
        }

    # Fetch decisions for landmark detection
    decisions = get_recent_decisions(project_id, limit=50, active_only=False)
    landmarks, regular = detect_landmarks(decisions)

    logger.info(f"Detected {len(landmarks)} landmark decisions, {len(regular)} regular")

    # Pre-filter (free)
    filtered_content = prefilter_content(content)
    filtered_tokens = estimate_tokens(filtered_content)

    logger.info(f"Pre-filter: {current_tokens} → {filtered_tokens} tokens")

    # If pre-filtering was enough, skip LLM
    if filtered_tokens <= MAX_MEMORY_TOKENS:
        update_project_memory(
            project_id=project_id,
            content=filtered_content,
            updated_by="compaction_prefilter",
        )
        return {
            "compacted": True,
            "method": "prefilter_only",
            "before_tokens": current_tokens,
            "after_tokens": filtered_tokens,
            "landmarks_preserved": len(landmarks),
        }

    # LLM compaction needed
    compacted_content = compact_with_llm(
        memory_content=filtered_content,
        landmarks=landmarks,
        target_tokens=TARGET_MEMORY_TOKENS,
    )

    final_tokens = estimate_tokens(compacted_content)

    # Save compacted memory
    update_project_memory(
        project_id=project_id,
        content=compacted_content,
        updated_by="compaction_llm",
    )

    # Mark landmarks in the database for future reference
    from app.db.supabase_client import get_supabase
    supabase = get_supabase()

    for landmark in landmarks:
        try:
            supabase.table("project_decisions").update({
                "is_landmark": True
            }).eq("id", landmark["id"]).execute()
        except Exception as e:
            logger.warning(f"Failed to mark landmark {landmark.get('id')}: {e}")

    return {
        "compacted": True,
        "method": "llm",
        "before_tokens": current_tokens,
        "after_tokens": final_tokens,
        "reduction_percent": 100 - (final_tokens * 100 // current_tokens),
        "landmarks_preserved": len(landmarks),
        "landmarks": [d.get("title") for d in landmarks],
    }


def maybe_compact_memory(project_id: UUID) -> dict[str, Any] | None:
    """
    Check and compact memory if needed. Safe to call frequently.

    Returns None if no compaction needed, otherwise returns compaction results.
    """
    from app.db.project_memory import get_project_memory

    memory = get_project_memory(project_id)
    if not memory:
        return None

    content = memory.get("content", "")
    if not should_compact(content):
        return None

    return compact_memory(project_id)
