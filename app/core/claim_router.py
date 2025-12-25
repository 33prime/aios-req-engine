"""Claim router for surgical updates.

Groups claims by target entity and separates new object proposals.

Phase 1: Surgical Updates for Features
"""

from collections import defaultdict
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.core.schemas_claims import Claim

logger = get_logger(__name__)


def route_claims(
    claims: list[Claim],
) -> tuple[dict[tuple[str, UUID], list[Claim]], list[Claim]]:
    """Route claims to their target entities and separate new proposals.

    Args:
        claims: List of extracted claims

    Returns:
        Tuple of:
        - grouped_claims: Dict mapping (entity_type, entity_id) -> list of claims
        - new_object_proposals: List of claims proposing new entities

    Example:
        >>> grouped, proposals = route_claims(claims)
        >>> grouped[("feature", feature_uuid)]  # All claims for this feature
        >>> proposals  # Claims suggesting new features/personas/etc
    """
    grouped_claims: dict[tuple[str, UUID], list[Claim]] = defaultdict(list)
    new_object_proposals: list[Claim] = []

    for claim in claims:
        if claim.action == "propose_new_object":
            # Proposals for new entities (always escalated)
            new_object_proposals.append(claim)
            logger.debug(
                f"Routed claim to new object proposal: {claim.target.type}",
                extra={"claim": claim.claim},
            )
        elif claim.target.id is not None:
            # Route to existing entity
            key = (claim.target.type, claim.target.id)
            grouped_claims[key].append(claim)
            logger.debug(
                f"Routed claim to {claim.target.type} {claim.target.id}",
                extra={"claim": claim.claim, "field": claim.target.field},
            )
        else:
            # Claim has action="update" but no target ID - this is invalid
            logger.warning(
                f"Skipping claim with action=update but no target ID: {claim.claim}",
                extra={"claim_dict": claim.model_dump()},
            )

    logger.info(
        f"Routed {len(claims)} claims: {len(grouped_claims)} entities targeted, "
        f"{len(new_object_proposals)} new proposals",
        extra={
            "total_claims": len(claims),
            "entities_targeted": len(grouped_claims),
            "new_proposals": len(new_object_proposals),
        },
    )

    return dict(grouped_claims), new_object_proposals


def get_claims_by_entity(
    grouped_claims: dict[tuple[str, UUID], list[Claim]],
    entity_type: str,
    entity_id: UUID,
) -> list[Claim]:
    """Get all claims for a specific entity.

    Args:
        grouped_claims: Output from route_claims()
        entity_type: Type of entity (feature, persona, etc.)
        entity_id: Entity UUID

    Returns:
        List of claims for this entity
    """
    key = (entity_type, entity_id)
    return grouped_claims.get(key, [])


def get_entities_with_claims(
    grouped_claims: dict[tuple[str, UUID], list[Claim]],
) -> list[tuple[str, UUID, int]]:
    """Get list of entities that have claims.

    Args:
        grouped_claims: Output from route_claims()

    Returns:
        List of (entity_type, entity_id, claim_count) tuples
    """
    return [
        (entity_type, entity_id, len(claims))
        for (entity_type, entity_id), claims in grouped_claims.items()
    ]


def filter_claims_by_confidence(
    claims: list[Claim],
    min_confidence: float = 0.7,
) -> tuple[list[Claim], list[Claim]]:
    """Filter claims by confidence threshold.

    Args:
        claims: List of claims to filter
        min_confidence: Minimum confidence threshold (default 0.7)

    Returns:
        Tuple of (high_confidence_claims, low_confidence_claims)
    """
    high_confidence = []
    low_confidence = []

    for claim in claims:
        if claim.confidence >= min_confidence:
            high_confidence.append(claim)
        else:
            low_confidence.append(claim)

    logger.debug(
        f"Filtered claims by confidence: {len(high_confidence)} high, {len(low_confidence)} low",
        extra={"min_confidence": min_confidence},
    )

    return high_confidence, low_confidence
