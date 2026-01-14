"""
Confirmation Resolution from Client Signals

Automatically resolves open confirmation items when client signals
(emails, meeting transcripts) contain answers to pending questions.

Flow:
1. Client signal arrives (email, transcript)
2. Get all open confirmation items for project
3. For each confirmation, check if signal content answers the "ask"
4. If confidence >= 80%, auto-resolve and update entity status
5. Link signal as resolution evidence
"""

import json
from typing import Any
from uuid import UUID

from openai import OpenAI

from app.core.logging import get_logger
from app.core.config import get_settings
from app.db.confirmations import (
    list_confirmation_items,
    set_confirmation_status,
)
from app.db.prd import update_prd_section
from app.db.features import update_feature
from app.db.vp import update_vp_step

logger = get_logger(__name__)

# Confidence threshold for auto-resolution
AUTO_RESOLVE_THRESHOLD = 0.80


RESOLUTION_CHECK_PROMPT = """You are analyzing whether a client communication resolves an open question/confirmation.

**Open Confirmation:**
Title: {title}
Question/Ask: {ask}
Why needed: {why}
{proposed_value_text}

**Client Signal (email/transcript):**
{signal_content}

**Task:**
Determine if this client communication answers or resolves the open question.

Return JSON with:
- "resolves": boolean - Does the signal clearly answer the question?
- "confidence": float (0.0-1.0) - How confident are you?
- "extracted_answer": string - The specific answer/value extracted from signal (null if not resolved)
- "relevant_excerpt": string - The exact excerpt from signal that answers the question (max 200 chars)
- "reasoning": string - Brief explanation of your determination

Be conservative - only mark as resolved if the signal CLEARLY and DIRECTLY answers the question.
A vague or partial mention is NOT sufficient. Confidence should be high (>0.8) only for clear, explicit answers.

Return ONLY valid JSON, no markdown.
"""


async def check_signal_resolves_confirmations(
    project_id: UUID,
    signal_id: UUID,
    signal_content: str,
    signal_source: str,
    run_id: UUID | None = None,
) -> dict[str, Any]:
    """
    Check if a client signal resolves any open confirmation items.

    Args:
        project_id: Project UUID
        signal_id: Signal UUID (for evidence linking)
        signal_content: Raw text content of the signal
        signal_source: Source identifier (email, transcript, etc.)
        run_id: Processing run UUID for tracking

    Returns:
        Dictionary with:
        - checked: Number of confirmations checked
        - resolved: Number auto-resolved
        - resolutions: List of resolution details
    """
    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    results = {
        "checked": 0,
        "resolved": 0,
        "resolutions": [],
    }

    try:
        # Get all open confirmation items
        open_confirmations = list_confirmation_items(project_id, status="open")

        if not open_confirmations:
            logger.info(f"No open confirmations to check for project {project_id}")
            return results

        logger.info(
            f"Checking {len(open_confirmations)} open confirmations against signal {signal_id}"
        )

        # Truncate signal content if too long
        max_content_length = 4000
        truncated_content = signal_content[:max_content_length]
        if len(signal_content) > max_content_length:
            truncated_content += "\n... [content truncated]"

        for confirmation in open_confirmations:
            results["checked"] += 1

            try:
                resolution = await _check_single_confirmation(
                    client=client,
                    settings=settings,
                    confirmation=confirmation,
                    signal_content=truncated_content,
                    signal_id=signal_id,
                    signal_source=signal_source,
                )

                if resolution and resolution.get("resolved"):
                    results["resolved"] += 1
                    results["resolutions"].append(resolution)

                    logger.info(
                        f"Auto-resolved confirmation {confirmation['id']}: {confirmation.get('title')}"
                    )

            except Exception as e:
                logger.warning(
                    f"Error checking confirmation {confirmation['id']}: {e}"
                )
                continue

        logger.info(
            f"Signal resolution check complete: {results['resolved']}/{results['checked']} resolved"
        )

        return results

    except Exception as e:
        logger.error(f"Error checking signal resolutions: {e}", exc_info=True)
        return results


async def _check_single_confirmation(
    client: OpenAI,
    settings: Any,
    confirmation: dict[str, Any],
    signal_content: str,
    signal_id: UUID,
    signal_source: str,
) -> dict[str, Any] | None:
    """
    Check if signal resolves a single confirmation item.

    Returns resolution details if resolved, None otherwise.
    """
    # Build proposed value text if available
    proposed_value_text = ""
    created_from = confirmation.get("created_from", {})
    if created_from and created_from.get("proposed_changes"):
        proposed_value_text = f"A-Team proposed: {json.dumps(created_from.get('proposed_changes'))}"

    prompt = RESOLUTION_CHECK_PROMPT.format(
        title=confirmation.get("title", "Untitled"),
        ask=confirmation.get("ask", ""),
        why=confirmation.get("why", ""),
        proposed_value_text=proposed_value_text,
        signal_content=signal_content,
    )

    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL_MINI,  # Use fast model for checks
            temperature=0.1,
            max_tokens=500,
            messages=[
                {"role": "system", "content": "You are a precise analyst determining if client communications answer open questions. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
        )

        raw = response.choices[0].message.content.strip()

        # Strip markdown if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        result = json.loads(raw)

        # Check if resolved with sufficient confidence
        if result.get("resolves") and result.get("confidence", 0) >= AUTO_RESOLVE_THRESHOLD:
            # Auto-resolve the confirmation
            resolution_evidence = {
                "type": "auto_from_signal",
                "signal_id": str(signal_id),
                "signal_source": signal_source,
                "excerpt": result.get("relevant_excerpt", "")[:200],
                "extracted_answer": result.get("extracted_answer"),
                "confidence": result.get("confidence"),
                "reasoning": result.get("reasoning", ""),
            }

            # Update confirmation status
            set_confirmation_status(
                confirmation_id=UUID(confirmation["id"]),
                status="resolved",
                resolution_evidence=resolution_evidence,
            )

            # Update the target entity's confirmation_status
            target_table = confirmation.get("target_table")
            target_id = confirmation.get("target_id")

            if target_table and target_id:
                _update_entity_to_confirmed_client(
                    target_table=target_table,
                    target_id=UUID(target_id),
                    extracted_answer=result.get("extracted_answer"),
                )

            return {
                "resolved": True,
                "confirmation_id": confirmation["id"],
                "confirmation_title": confirmation.get("title"),
                "confidence": result.get("confidence"),
                "extracted_answer": result.get("extracted_answer"),
                "excerpt": result.get("relevant_excerpt"),
            }

        return None

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse resolution check JSON: {e}")
        return None
    except Exception as e:
        logger.warning(f"Resolution check failed: {e}")
        return None


def _update_entity_to_confirmed_client(
    target_table: str,
    target_id: UUID,
    extracted_answer: str | None = None,
) -> None:
    """
    Update target entity's confirmation_status to 'confirmed_client'.

    Also applies the extracted answer if available and applicable.
    """
    try:
        update_data = {"confirmation_status": "confirmed_client"}

        if target_table == "prd_sections":
            update_prd_section(target_id, update_data)
        elif target_table == "features":
            update_feature(target_id, update_data, run_id=None)
        elif target_table == "vp_steps":
            update_vp_step(target_id, update_data, run_id=None)
        else:
            logger.warning(f"Unknown target table: {target_table}")
            return

        logger.info(
            f"Updated {target_table} {target_id} confirmation_status to 'confirmed_client'"
        )

    except Exception as e:
        logger.warning(f"Failed to update entity confirmation status: {e}")


async def process_client_signal_for_confirmations(
    project_id: UUID,
    signal_id: UUID,
    signal_content: str,
    signal_type: str,
    signal_source: str,
    metadata: dict[str, Any] | None = None,
    run_id: UUID | None = None,
) -> dict[str, Any]:
    """
    Main entry point for processing a client signal for confirmation resolution.

    Only processes signals with authority="client".

    Args:
        project_id: Project UUID
        signal_id: Signal UUID
        signal_content: Raw text content
        signal_type: Type (email, transcript, note, etc.)
        signal_source: Source identifier
        metadata: Signal metadata (must have authority="client")
        run_id: Processing run UUID

    Returns:
        Resolution results
    """
    # Only process client signals
    authority = (metadata or {}).get("authority", "").lower()

    if authority != "client":
        logger.debug(
            f"Skipping non-client signal {signal_id} for confirmation check (authority={authority})"
        )
        return {"checked": 0, "resolved": 0, "resolutions": [], "skipped": True}

    # Check for client signal types
    client_signal_types = {"email", "transcript", "note", "meeting", "call"}

    if signal_type.lower() not in client_signal_types:
        logger.debug(
            f"Skipping signal type {signal_type} for confirmation check"
        )
        return {"checked": 0, "resolved": 0, "resolutions": [], "skipped": True}

    logger.info(
        f"Processing client {signal_type} signal {signal_id} for confirmation resolution"
    )

    return await check_signal_resolves_confirmations(
        project_id=project_id,
        signal_id=signal_id,
        signal_content=signal_content,
        signal_source=signal_source,
        run_id=run_id,
    )
