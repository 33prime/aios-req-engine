"""Relatability scoring for business drivers.

Computes how deeply a driver is woven into the project graph,
weighted by confirmation status of linked entities.
"""

from typing import Any


_CONFIRMED_STATUSES = {"confirmed_consultant", "confirmed_client"}


def _is_confirmed(entity_id: str, entities: list[dict[str, Any]]) -> bool:
    for e in entities:
        if e.get("id") == entity_id:
            return e.get("confirmation_status") in _CONFIRMED_STATUSES
    return False


def compute_relatability_score(
    driver: dict[str, Any],
    project_entities: dict[str, list[dict[str, Any]]],
) -> float:
    """Compute relatability score for a business driver.

    Score = sum of weighted links.
    Confirmed links are worth 3x unconfirmed.

    Args:
        driver: Raw business driver dict from DB.
        project_entities: Dict with keys features, personas, vp_steps, drivers.

    Returns:
        Rounded score (1 decimal).
    """
    score = 0.0

    # Feature links (strongest signal — a feature addresses this driver)
    for fid in driver.get("linked_feature_ids") or []:
        score += 3.0 if _is_confirmed(str(fid), project_entities.get("features", [])) else 1.0

    # Persona links (who experiences this)
    for pid in driver.get("linked_persona_ids") or []:
        score += 3.0 if _is_confirmed(str(pid), project_entities.get("personas", [])) else 1.0

    # Workflow links (where in the process)
    for vid in driver.get("linked_vp_step_ids") or []:
        score += 2.0 if _is_confirmed(str(vid), project_entities.get("vp_steps", [])) else 0.5

    # Related driver links (connected to other drivers)
    for did in driver.get("linked_driver_ids") or []:
        score += 1.0 if _is_confirmed(str(did), project_entities.get("drivers", [])) else 0.3

    # Evidence depth bonus
    evidence_count = len(driver.get("evidence") or [])
    score += evidence_count * 0.5

    # Vision alignment bonus
    va = driver.get("vision_alignment")
    if va == "high":
        score += 3.0
    elif va == "medium":
        score += 1.5
    elif va == "low":
        score += 0.5

    # Self-confirmation bonus
    if driver.get("confirmation_status") in _CONFIRMED_STATUSES:
        score += 5.0

    return round(score, 1)
