"""Batch proposals database operations."""

from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def create_proposal(
    project_id: UUID,
    conversation_id: UUID | None,
    title: str,
    description: str | None,
    proposal_type: str,
    changes: list[dict[str, Any]],
    user_request: str | None = None,
    context_snapshot: dict[str, Any] | None = None,
    created_by: str | None = None,
) -> dict[str, Any]:
    """
    Create a new batch proposal.

    Args:
        project_id: Project UUID
        conversation_id: Optional conversation UUID
        title: Proposal title
        description: Optional description
        proposal_type: Type of proposal ('features', 'prd', 'vp', 'personas', 'mixed')
        changes: List of change objects
        user_request: Original user request text
        context_snapshot: Snapshot of project context at creation time
        created_by: Optional creator identifier

    Returns:
        Created proposal record

    Raises:
        Exception: If database operation fails
    """
    supabase = get_supabase()

    try:
        # Count change types
        creates_count = sum(1 for c in changes if c.get("operation") == "create")
        updates_count = sum(1 for c in changes if c.get("operation") == "update")
        deletes_count = sum(1 for c in changes if c.get("operation") == "delete")

        # Build proposal data
        proposal_data = {
            "project_id": str(project_id),
            "title": title,
            "description": description,
            "proposal_type": proposal_type,
            "status": "pending",
            "changes": changes,
            "creates_count": creates_count,
            "updates_count": updates_count,
            "deletes_count": deletes_count,
            "user_request": user_request,
            "context_snapshot": context_snapshot or {},
            "created_by": created_by,
        }

        if conversation_id:
            proposal_data["conversation_id"] = str(conversation_id)

        # Insert proposal
        response = supabase.table("batch_proposals").insert(proposal_data).execute()

        if not response.data:
            raise Exception("Failed to create proposal")

        proposal = response.data[0]

        logger.info(
            f"Created proposal {proposal['id']} for project {project_id}",
            extra={
                "project_id": str(project_id),
                "proposal_id": proposal["id"],
                "proposal_type": proposal_type,
                "changes_count": len(changes),
            },
        )

        return proposal

    except Exception as e:
        logger.error(
            f"Error creating proposal: {e}",
            exc_info=True,
            extra={"project_id": str(project_id)},
        )
        raise


def get_proposal(proposal_id: UUID) -> dict[str, Any] | None:
    """
    Get a proposal by ID.

    Args:
        proposal_id: Proposal UUID

    Returns:
        Proposal record or None if not found
    """
    supabase = get_supabase()

    try:
        response = supabase.table("batch_proposals").select("*").eq("id", str(proposal_id)).single().execute()

        return response.data if response.data else None

    except Exception as e:
        logger.error(
            f"Error getting proposal {proposal_id}: {e}",
            exc_info=True,
            extra={"proposal_id": str(proposal_id)},
        )
        return None


def list_pending_proposals(project_id: UUID, limit: int = 10) -> list[dict[str, Any]]:
    """
    List pending proposals for a project.

    Args:
        project_id: Project UUID
        limit: Maximum number of proposals to return

    Returns:
        List of pending proposals (most recent first)
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("batch_proposals")
            .select("*")
            .eq("project_id", str(project_id))
            .eq("status", "pending")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        return response.data or []

    except Exception as e:
        logger.error(
            f"Error listing pending proposals: {e}",
            exc_info=True,
            extra={"project_id": str(project_id)},
        )
        return []


def list_all_proposals(
    project_id: UUID,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    List proposals for a project with optional status filter.

    Args:
        project_id: Project UUID
        status: Optional status filter ('pending', 'previewed', 'applied', 'discarded')
        limit: Maximum number of proposals to return

    Returns:
        List of proposals (most recent first)
    """
    supabase = get_supabase()

    try:
        query = (
            supabase.table("batch_proposals")
            .select("*")
            .eq("project_id", str(project_id))
        )

        if status:
            query = query.eq("status", status)

        response = query.order("created_at", desc=True).limit(limit).execute()

        return response.data or []

    except Exception as e:
        logger.error(
            f"Error listing proposals: {e}",
            exc_info=True,
            extra={"project_id": str(project_id), "status": status},
        )
        return []


def mark_previewed(proposal_id: UUID) -> dict[str, Any] | None:
    """
    Mark a proposal as previewed.

    Args:
        proposal_id: Proposal UUID

    Returns:
        Updated proposal record or None if not found
    """
    supabase = get_supabase()

    try:
        from datetime import datetime, timezone

        response = (
            supabase.table("batch_proposals")
            .update({
                "status": "previewed",
                "previewed_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", str(proposal_id))
            .execute()
        )

        if not response.data:
            logger.warning(f"Proposal {proposal_id} not found")
            return None

        proposal = response.data[0]

        logger.info(
            f"Marked proposal {proposal_id} as previewed",
            extra={"proposal_id": str(proposal_id)},
        )

        return proposal

    except Exception as e:
        logger.error(
            f"Error marking proposal as previewed: {e}",
            exc_info=True,
            extra={"proposal_id": str(proposal_id)},
        )
        return None


def discard_proposal(proposal_id: UUID) -> dict[str, Any] | None:
    """
    Mark a proposal as discarded.

    Args:
        proposal_id: Proposal UUID

    Returns:
        Updated proposal record or None if not found
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("batch_proposals")
            .update({"status": "discarded"})
            .eq("id", str(proposal_id))
            .execute()
        )

        if not response.data:
            logger.warning(f"Proposal {proposal_id} not found")
            return None

        proposal = response.data[0]

        logger.info(
            f"Discarded proposal {proposal_id}",
            extra={"proposal_id": str(proposal_id)},
        )

        return proposal

    except Exception as e:
        logger.error(
            f"Error discarding proposal: {e}",
            exc_info=True,
            extra={"proposal_id": str(proposal_id)},
        )
        return None


def apply_proposal(proposal_id: UUID, applied_by: str | None = None) -> dict[str, Any]:
    """
    Apply a batch proposal atomically.

    This function:
    1. Validates proposal is in 'previewed' or 'pending' status
    2. Groups changes by entity type
    3. Applies changes using existing database functions
    4. Marks proposal as 'applied' on success
    5. Marks with error on failure

    Args:
        proposal_id: Proposal UUID
        applied_by: Optional identifier of who applied the proposal

    Returns:
        Updated proposal record with application results

    Raises:
        ValueError: If proposal is not in valid status
        Exception: If application fails
    """
    supabase = get_supabase()

    try:
        # Get proposal
        proposal = get_proposal(proposal_id)

        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        # Validate status
        if proposal["status"] not in ["pending", "previewed"]:
            raise ValueError(
                f"Proposal {proposal_id} cannot be applied (status: {proposal['status']})"
            )

        # Get changes
        changes = proposal.get("changes", [])

        if not changes:
            raise ValueError(f"Proposal {proposal_id} has no changes to apply")

        # Group changes by entity type and operation
        from collections import defaultdict

        changes_by_type = defaultdict(lambda: {"creates": [], "updates": [], "deletes": []})

        for change in changes:
            entity_type = change.get("entity_type")
            operation = change.get("operation")

            if not entity_type or not operation:
                logger.warning(f"Invalid change in proposal {proposal_id}: {change}")
                continue

            changes_by_type[entity_type][f"{operation}s"].append(change)

        # Apply changes by entity type
        project_id = UUID(proposal["project_id"])
        applied_count = 0
        errors = []

        # Derive signal_id: check proposal field, then evidence, then most recent signal
        _signal_id_str = proposal.get("signal_id")
        if not _signal_id_str:
            # Try to find from changes evidence
            for ch in changes:
                for ev in ch.get("evidence", []):
                    sid = ev.get("signal_id")
                    if sid and sid != "None":
                        _signal_id_str = sid
                        break
                if _signal_id_str:
                    break
        if not _signal_id_str:
            # Fallback: most recent signal for this project
            try:
                recent_sig = (
                    supabase.table("signals")
                    .select("id")
                    .eq("project_id", str(project_id))
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if recent_sig.data:
                    _signal_id_str = recent_sig.data[0]["id"]
            except Exception:
                pass
        _source_signal_id = UUID(_signal_id_str) if _signal_id_str else None

        # Import database functions
        from app.db.features import bulk_replace_features, list_features
        from app.db.vp import upsert_vp_step
        from app.db.personas import upsert_persona
        from app.core.similarity import find_matching_feature

        # Valid columns for features table (must match database schema)
        # Includes all enrichment columns from migrations 0008, 0015, 0016, 0031
        VALID_FEATURE_COLUMNS = {
            # Core fields (0006)
            "name",
            "category",
            "is_mvp",
            "confidence",
            "status",
            "evidence",
            # Enrichment details (0008)
            "details",
            # Lifecycle tracking (0015)
            "lifecycle_stage",
            # Confirmation status (0016/0020)
            "confirmation_status",
            # Feature enrichment (0031)
            "overview",
            "target_personas",
            "user_actions",
            "system_behaviors",
            "ui_requirements",
            "rules",
            "integrations",
            "enrichment_status",
        }

        def filter_feature_data(data: dict) -> dict:
            """Filter feature data to only include valid database columns."""
            filtered = {k: v for k, v in data.items() if k in VALID_FEATURE_COLUMNS}
            return filtered

        try:
            # Apply feature changes
            if "feature" in changes_by_type:
                feature_changes = changes_by_type["feature"]

                # Get existing features for similarity matching
                existing_features = list_features(project_id)

                # Handle creates individually with similarity checking
                for change in feature_changes["creates"]:
                    after = change.get("after")

                    if not after:
                        continue

                    # Filter to valid columns and add project_id
                    feature_data = filter_feature_data(after)
                    feature_data["project_id"] = str(project_id)

                    # Validate required field
                    feature_name = feature_data.get("name", "")
                    if not feature_name:
                        logger.warning(f"Skipping feature create: missing 'name' field")
                        errors.append("Feature missing required 'name' field")
                        continue

                    # Ensure required 'category' field has a default
                    if not feature_data.get("category"):
                        feature_data["category"] = "Core"

                    # Check for similar existing features using similarity matching
                    match_result = find_matching_feature(feature_name, existing_features)

                    if match_result.is_match and match_result.matched_item:
                        matched = match_result.matched_item
                        matched_name = matched.get("name", "")
                        matched_id = matched.get("id")

                        logger.info(
                            f"Feature '{feature_name}' matches existing '{matched_name}' "
                            f"(score: {match_result.score:.2f}, method: {match_result.strategy.value}) - merging evidence"
                        )

                        # Merge new evidence into existing feature
                        new_evidence = after.get("evidence", [])
                        if new_evidence and matched_id:
                            existing_evidence = matched.get("evidence", []) or []

                            # Deduplicate by chunk_id
                            existing_chunk_ids = {
                                e.get("chunk_id") for e in existing_evidence if e.get("chunk_id")
                            }
                            unique_new_evidence = [
                                e for e in new_evidence
                                if e.get("chunk_id") and e.get("chunk_id") not in existing_chunk_ids
                            ]

                            if unique_new_evidence:
                                combined_evidence = existing_evidence + unique_new_evidence
                                try:
                                    supabase.table("features").update({
                                        "evidence": combined_evidence,
                                        "updated_at": "now()",
                                    }).eq("id", matched_id).execute()

                                    logger.info(
                                        f"Merged {len(unique_new_evidence)} evidence items into '{matched_name}'"
                                    )
                                except Exception as merge_err:
                                    logger.warning(f"Failed to merge evidence: {merge_err}")

                        applied_count += 1  # Count as applied (merged)
                        continue  # Skip insert - merged instead

                    # No match found - insert new feature
                    insert_response = supabase.table("features").insert(feature_data).execute()

                    if insert_response.data:
                        applied_count += 1
                        # Add to existing_features list so subsequent duplicates are caught
                        existing_features.append(insert_response.data[0])
                        logger.info(f"Created feature: {feature_name}")
                    else:
                        logger.warning(f"Failed to create feature: {feature_name} - no data returned")
                        errors.append(f"Failed to create feature: {feature_name}")

                # Handle updates individually
                for change in feature_changes["updates"]:
                    entity_id = change.get("entity_id")
                    after = change.get("after")

                    if not entity_id or not after:
                        continue

                    # Filter to valid columns for update
                    feature_data = filter_feature_data(after)

                    if not feature_data:
                        logger.warning(f"Skipping feature update {entity_id}: no valid fields to update")
                        continue

                    # Update feature using supabase directly
                    update_response = (
                        supabase.table("features")
                        .update(feature_data)
                        .eq("id", entity_id)
                        .execute()
                    )

                    if update_response.data:
                        applied_count += 1
                        logger.info(f"Updated feature: {entity_id}")
                    else:
                        logger.warning(f"Failed to update feature: {entity_id} - no data returned")
                        errors.append(f"Failed to update feature: {entity_id}")

                # Handle deletes
                for change in feature_changes["deletes"]:
                    entity_id = change.get("entity_id")

                    if not entity_id:
                        continue

                    delete_response = (
                        supabase.table("features")
                        .delete()
                        .eq("id", entity_id)
                        .execute()
                    )

                    if delete_response.data:
                        applied_count += 1
                        logger.info(f"Deleted feature: {entity_id}")
                    else:
                        logger.warning(f"Failed to delete feature: {entity_id} - not found or already deleted")
                        # Don't add to errors - might just be already deleted

            # Apply workflow changes (MUST run before vp_step block)
            workflow_name_to_id: dict[str, str] = {}
            if "workflow" in changes_by_type:
                from app.db.workflows import create_workflow, pair_workflows

                workflow_changes = changes_by_type["workflow"]
                pair_requests: list[tuple[str, str, str]] = []  # (name, pair_name, pair_state)

                for change in workflow_changes["creates"]:
                    after = change.get("after")
                    if not after or "name" not in after:
                        continue

                    try:
                        wf = create_workflow(project_id, after)
                        wf_key = f"{after['name']}::{after.get('state_type', 'future')}"
                        workflow_name_to_id[wf_key] = wf["id"]
                        # Also store by bare name for step lookups
                        workflow_name_to_id[f"{after['name']}::{after.get('state_type', 'future')}::bare"] = wf["id"]
                        applied_count += 1
                        logger.info(f"Created workflow: {after['name']} ({after.get('state_type', 'future')})")

                        if after.get("pair_with_name"):
                            pair_requests.append((
                                f"{after['name']}::{after.get('state_type', 'future')}",
                                f"{after['pair_with_name']}::{after.get('pair_state', 'future')}",
                                after.get("pair_state", "future"),
                            ))
                    except Exception as wf_err:
                        logger.warning(f"Failed to create workflow '{after.get('name')}': {wf_err}")
                        errors.append(f"Failed to create workflow: {after.get('name')}")

                # Pair workflows after all are created
                for wf_key, pair_key, _pair_state in pair_requests:
                    wf_id = workflow_name_to_id.get(wf_key)
                    pair_id = workflow_name_to_id.get(pair_key)
                    if wf_id and pair_id:
                        try:
                            pair_workflows(UUID(wf_id), UUID(pair_id))
                            logger.info(f"Paired workflows: {wf_key} <-> {pair_key}")
                        except Exception as pair_err:
                            logger.warning(f"Failed to pair workflows: {pair_err}")

            # Apply VP step changes
            if "vp_step" in changes_by_type:
                from app.db.workflows import create_workflow_step

                vp_changes = changes_by_type["vp_step"]

                for change in vp_changes["creates"] + vp_changes["updates"]:
                    after = change.get("after")

                    if not after or "step_index" not in after:
                        continue

                    # Check if this step belongs to a workflow
                    wf_name = after.pop("workflow_name", None)
                    step_state = after.pop("state_type", None)

                    workflow_id = None
                    if wf_name:
                        # Look up by name + state_type in created workflows
                        wf_key = f"{wf_name}::{step_state or 'future'}"
                        workflow_id = workflow_name_to_id.get(wf_key)

                        if not workflow_id:
                            # Try existing workflows by querying DB
                            try:
                                existing_wf = (
                                    supabase.table("workflows")
                                    .select("id")
                                    .eq("project_id", str(project_id))
                                    .eq("name", wf_name)
                                    .eq("state_type", step_state or "future")
                                    .maybe_single()
                                    .execute()
                                )
                                if existing_wf.data:
                                    workflow_id = existing_wf.data["id"]
                            except Exception:
                                pass

                    if workflow_id:
                        try:
                            create_workflow_step(
                                workflow_id=UUID(workflow_id),
                                project_id=project_id,
                                data=after,
                            )
                            applied_count += 1
                        except Exception as step_err:
                            logger.warning(f"Failed to create workflow step: {step_err}")
                            errors.append(f"Failed to create workflow step: {after.get('label')}")
                    else:
                        upsert_vp_step(
                            project_id=project_id,
                            step_index=after["step_index"],
                            payload=after,
                        )
                        applied_count += 1

            # Apply persona changes
            if "persona" in changes_by_type:
                persona_changes = changes_by_type["persona"]

                for change in persona_changes["creates"] + persona_changes["updates"]:
                    after = change.get("after")

                    if not after or "slug" not in after:
                        continue

                    # Call upsert_persona with individual parameters (not payload dict)
                    upsert_persona(
                        project_id=project_id,
                        slug=after["slug"],
                        name=after.get("name", after.get("slug", "Unknown")),
                        role=after.get("role"),
                        demographics=after.get("demographics"),
                        psychographics=after.get("psychographics"),
                        goals=after.get("goals"),
                        pain_points=after.get("pain_points"),
                        description=after.get("description"),
                        related_features=after.get("related_features"),
                        related_vp_steps=after.get("related_vp_steps"),
                        confirmation_status=after.get("confirmation_status", "ai_generated"),
                    )
                    applied_count += 1

            # Apply constraint changes
            if "constraint" in changes_by_type:
                from app.db.constraints import upsert_constraint

                constraint_changes = changes_by_type["constraint"]

                for change in constraint_changes["creates"] + constraint_changes["updates"]:
                    after = change.get("after")

                    if not after or "title" not in after:
                        continue

                    upsert_constraint(
                        project_id=project_id,
                        title=after["title"],
                        constraint_type=after.get("constraint_type", "technical"),
                        description=after.get("description"),
                        severity=after.get("severity", "should_have"),
                        evidence=change.get("evidence", []),
                    )
                    applied_count += 1

            # Apply business driver changes
            if "business_driver" in changes_by_type:
                from app.db.business_drivers import smart_upsert_business_driver

                driver_changes = changes_by_type["business_driver"]

                for change in driver_changes["creates"] + driver_changes["updates"]:
                    after = change.get("after")

                    if not after or "description" not in after:
                        continue

                    # Build evidence from change
                    evidence = change.get("evidence", [])
                    new_evidence = []
                    for ev in evidence:
                        new_evidence.append({
                            "signal_id": str(_source_signal_id) if _source_signal_id else ev.get("signal_id"),
                            "chunk_id": ev.get("chunk_id"),
                            "text": ev.get("text", ev.get("excerpt", "")),
                            "confidence": ev.get("confidence", 0.8),
                        })

                    driver_type = after.get("driver_type", "goal")
                    _, action = smart_upsert_business_driver(
                        project_id=project_id,
                        driver_type=driver_type,
                        description=after["description"],
                        new_evidence=new_evidence if new_evidence else [],
                        source_signal_id=_source_signal_id,
                        created_by="system",
                        measurement=after.get("measurement"),
                        priority=after.get("priority", 3),
                    )
                    applied_count += 1
                    logger.info(f"{action.capitalize()} {driver_type}: {after['description'][:50]}")

            # Apply competitor ref changes
            if "competitor_ref" in changes_by_type:
                from app.db.competitor_refs import smart_upsert_competitor_ref

                comp_changes = changes_by_type["competitor_ref"]

                for change in comp_changes["creates"] + comp_changes["updates"]:
                    after = change.get("after")

                    if not after or "name" not in after:
                        continue

                    # Build evidence from change
                    evidence = change.get("evidence", [])
                    new_evidence = []
                    for ev in evidence:
                        new_evidence.append({
                            "signal_id": ev.get("signal_id", str(proposal["signal_id"]) if "signal_id" in proposal else None),
                            "chunk_id": ev.get("chunk_id"),
                            "text": ev.get("text", ev.get("excerpt", "")),
                            "confidence": ev.get("confidence", 0.8),
                        })

                    ref_type = after.get("reference_type", "competitor")
                    signal_id = proposal.get("signal_id")
                    _, action = smart_upsert_competitor_ref(
                        project_id=project_id,
                        reference_type=ref_type,
                        name=after["name"],
                        new_evidence=new_evidence if new_evidence else [],
                        source_signal_id=UUID(signal_id) if signal_id else None,
                        created_by="system",
                        research_notes=after.get("research_notes"),
                    )
                    applied_count += 1
                    logger.info(f"{action.capitalize()} {ref_type}: {after['name']}")

            # Apply stakeholder changes
            if "stakeholder" in changes_by_type:
                from app.db.stakeholders import smart_upsert_stakeholder

                stakeholder_changes = changes_by_type["stakeholder"]

                for change in stakeholder_changes["creates"] + stakeholder_changes["updates"]:
                    after = change.get("after")

                    if not after or "name" not in after:
                        continue

                    # Build evidence from change
                    evidence = change.get("evidence", [])
                    new_evidence = []
                    for ev in evidence:
                        new_evidence.append({
                            "signal_id": str(_source_signal_id) if _source_signal_id else ev.get("signal_id"),
                            "chunk_id": ev.get("chunk_id"),
                            "text": ev.get("text", ev.get("excerpt", "")),
                            "confidence": ev.get("confidence", 0.8),
                        })

                    # Validate stakeholder_type against allowed values
                    VALID_STAKEHOLDER_TYPES = {"champion", "sponsor", "blocker", "influencer", "end_user"}
                    raw_type = after.get("stakeholder_type")
                    stakeholder_type = raw_type if raw_type in VALID_STAKEHOLDER_TYPES else "influencer"

                    _, action = smart_upsert_stakeholder(
                        project_id=project_id,
                        name=after["name"],
                        role=after.get("role"),
                        email=after.get("email"),
                        stakeholder_type=stakeholder_type,
                        influence_level=after.get("influence_level"),
                        engagement_level=after.get("engagement_status") or after.get("engagement_level"),
                        notes=after.get("notes"),
                        new_evidence=new_evidence if new_evidence else [],
                        source_signal_id=_source_signal_id,
                        created_by="system",
                    )
                    applied_count += 1
                    logger.info(f"{action.capitalize()} stakeholder: {after['name']}")

            # Apply data entity changes
            if "data_entity" in changes_by_type:
                from app.db.data_entities import create_data_entity, update_data_entity

                de_changes = changes_by_type["data_entity"]

                for change in de_changes["creates"]:
                    after = change.get("after")
                    if not after or "name" not in after:
                        continue

                    try:
                        create_data_entity(
                            project_id=project_id,
                            data={
                                "name": after["name"],
                                "description": after.get("description", ""),
                                "entity_category": after.get("entity_category", "domain"),
                                "fields": after.get("fields", []),
                                "confirmation_status": "ai_generated",
                            },
                        )
                        applied_count += 1
                        logger.info(f"Created data entity: {after['name']}")
                    except Exception as de_err:
                        logger.warning(f"Failed to create data entity '{after.get('name')}': {de_err}")
                        errors.append(f"Failed to create data entity: {after.get('name')}")

                for change in de_changes["updates"]:
                    entity_id = change.get("entity_id")
                    after = change.get("after")
                    if not entity_id or not after:
                        continue

                    try:
                        update_data_entity(UUID(entity_id), after)
                        applied_count += 1
                        logger.info(f"Updated data entity: {entity_id}")
                    except Exception as de_err:
                        logger.warning(f"Failed to update data entity '{entity_id}': {de_err}")
                        errors.append(f"Failed to update data entity: {entity_id}")

        except Exception as apply_error:
            error_msg = f"Failed to apply changes: {str(apply_error)}"
            errors.append(error_msg)
            logger.error(
                f"Error applying proposal {proposal_id}: {apply_error}",
                exc_info=True,
                extra={"proposal_id": str(proposal_id)},
            )

            # Mark as error
            from datetime import datetime, timezone

            error_response = (
                supabase.table("batch_proposals")
                .update({
                    "error_message": error_msg,
                    "applied_at": datetime.now(timezone.utc).isoformat(),
                })
                .eq("id", str(proposal_id))
                .execute()
            )

            raise

        # Check if any changes were actually applied
        expected_count = len(changes)
        if applied_count == 0 and expected_count > 0:
            error_msg = f"No changes were applied (expected {expected_count}). Errors: {'; '.join(errors) if errors else 'Unknown'}"
            logger.error(
                f"Proposal {proposal_id} failed: {error_msg}",
                extra={"proposal_id": str(proposal_id), "errors": errors},
            )
            raise ValueError(error_msg)

        # Mark as applied
        from datetime import datetime, timezone

        update_data = {
            "status": "applied",
            "applied_at": datetime.now(timezone.utc).isoformat(),
            # Note: applied_count is tracked in-memory but not stored in DB
            # (column doesn't exist in batch_proposals table)
        }

        # Include partial errors if any
        if errors:
            update_data["error_message"] = f"Partial success ({applied_count}/{expected_count}): {'; '.join(errors[:5])}"
            logger.warning(
                f"Proposal {proposal_id} applied with errors: {errors}",
                extra={"proposal_id": str(proposal_id), "applied_count": applied_count, "errors": errors},
            )

        if applied_by:
            update_data["applied_by"] = applied_by

        response = (
            supabase.table("batch_proposals")
            .update(update_data)
            .eq("id", str(proposal_id))
            .execute()
        )

        if not response.data:
            raise Exception(f"Failed to mark proposal {proposal_id} as applied")

        updated_proposal = response.data[0]

        logger.info(
            f"Applied proposal {proposal_id} ({applied_count} changes)",
            extra={
                "proposal_id": str(proposal_id),
                "applied_count": applied_count,
            },
        )

        # Log activity and revisions for each change applied
        try:
            from app.chains.activity_feed import log_activity
            from app.db.revisions_enrichment import insert_enrichment_revision

            # Log individual entity changes for the activity feed and revisions
            for change in proposal.get("changes", []):
                entity_type = change.get("entity_type")
                operation = change.get("operation")
                entity_id = change.get("entity_id")
                after = change.get("after", {})
                before = change.get("before", {})

                # Get entity name based on type
                entity_name = (
                    after.get("name") or
                    after.get("label") or
                    after.get("title") or
                    after.get("slug") or
                    "Untitled"
                )

                # Build change summary and track changed fields
                changed_fields: list[str] = []
                if operation == "create":
                    summary = f"Created {entity_type}: {entity_name}"
                    revision_type = "created"
                elif operation == "update":
                    # List changed fields
                    changed_fields = [k for k in after.keys() if k not in ("id", "project_id", "created_at", "updated_at") and after.get(k) != before.get(k)]
                    if changed_fields:
                        summary = f"Updated {entity_type} '{entity_name}': {', '.join(changed_fields[:3])}"
                        if len(changed_fields) > 3:
                            summary += f" +{len(changed_fields) - 3} more"
                    else:
                        summary = f"Updated {entity_type}: {entity_name}"
                    revision_type = "updated"
                elif operation == "delete":
                    summary = f"Deleted {entity_type}: {entity_name}"
                    revision_type = "updated"
                else:
                    summary = f"Changed {entity_type}: {entity_name}"
                    revision_type = "updated"

                # Log to activity feed
                log_activity(
                    project_id=project_id,
                    activity_type="proposal_applied",
                    change_summary=summary,
                    entity_type=entity_type,
                    entity_id=UUID(entity_id) if entity_id else None,
                    entity_name=entity_name,
                    change_details={
                        "proposal_id": str(proposal_id),
                        "proposal_title": proposal.get("title", ""),
                        "operation": operation,
                        "changed_fields": changed_fields if changed_fields else None,
                    },
                    source_type="proposal",
                    source_id=proposal_id,
                    requires_action=False,
                )

                # Log to enrichment_revisions for entity-level history
                if entity_id:
                    try:
                        # Build changes dict showing before/after for each field
                        changes_dict = {}
                        for field in changed_fields:
                            changes_dict[field] = {
                                "before": before.get(field),
                                "after": after.get(field),
                            }

                        # Build human-readable diff summary
                        if operation == "create":
                            diff_summary = f"Created new {entity_type}: {entity_name}"
                        elif operation == "update" and changed_fields:
                            diff_summary = f"Updated {', '.join(changed_fields[:3])}"
                            if len(changed_fields) > 3:
                                diff_summary += f" +{len(changed_fields) - 3} more fields"
                        elif operation == "delete":
                            diff_summary = f"Deleted {entity_type}: {entity_name}"
                        else:
                            diff_summary = summary

                        insert_enrichment_revision(
                            project_id=project_id,
                            entity_type=entity_type,
                            entity_id=UUID(entity_id),
                            entity_label=entity_name,
                            revision_type=revision_type,
                            trigger_event=f"proposal:{proposal.get('title', 'Proposal')}",
                            snapshot=after,
                            context_summary=f"Changed via proposal: {', '.join(changed_fields[:5]) if changed_fields else 'applied'}",
                            # New enhanced fields
                            changes=changes_dict if changes_dict else None,
                            diff_summary=diff_summary,
                            created_by=applied_by or "consultant",
                        )
                    except Exception as rev_err:
                        logger.warning(f"Failed to log revision for {entity_type} {entity_id}: {rev_err}")

            logger.info(f"Logged {len(proposal.get('changes', []))} activity/revision entries for proposal {proposal_id}")

        except Exception as activity_err:
            # Don't fail the proposal application if activity logging fails
            logger.warning(f"Failed to log activity for proposal {proposal_id}: {activity_err}")

        return updated_proposal

    except Exception as e:
        logger.error(
            f"Error in apply_proposal: {e}",
            exc_info=True,
            extra={"proposal_id": str(proposal_id)},
        )
        raise


def check_proposal_staleness(proposal_id: UUID) -> str | None:
    """
    Check if a proposal is stale due to entity modifications.

    A proposal is stale when any entity it touches has been modified
    after the proposal was created.

    Args:
        proposal_id: Proposal UUID

    Returns:
        Stale reason string if stale, None if fresh
    """
    supabase = get_supabase()

    try:
        # Get proposal
        proposal = get_proposal(proposal_id)

        if not proposal:
            return None

        if proposal["status"] not in ["pending", "previewed"]:
            return None

        proposal_created = proposal["created_at"]
        changes = proposal.get("changes", [])

        if not changes:
            return None

        # Check each change for staleness
        stale_entities = []

        for change in changes:
            entity_type = change.get("entity_type")
            entity_id = change.get("entity_id")

            if not entity_id:
                continue  # New entities can't be stale

            # Get entity table name
            table_map = {
                "feature": "features",
                "vp_step": "vp_steps",
                "persona": "personas",
            }

            table_name = table_map.get(entity_type)
            if not table_name:
                continue

            # Check if entity was modified after proposal created
            try:
                response = (
                    supabase.table(table_name)
                    .select("id, updated_at")
                    .eq("id", entity_id)
                    .single()
                    .execute()
                )

                if response.data:
                    entity_updated = response.data.get("updated_at")
                    if entity_updated and entity_updated > proposal_created:
                        entity_summary = change.get("summary", f"{entity_type} {entity_id[:8]}...")
                        stale_entities.append(entity_summary)

            except Exception:
                # Entity might have been deleted
                continue

        if stale_entities:
            return f"Modified since proposal: {', '.join(stale_entities[:3])}"

        return None

    except Exception as e:
        logger.error(
            f"Error checking proposal staleness: {e}",
            exc_info=True,
            extra={"proposal_id": str(proposal_id)},
        )
        return None


def mark_proposal_stale(proposal_id: UUID, stale_reason: str) -> dict[str, Any] | None:
    """
    Mark a proposal as stale with a reason.

    Args:
        proposal_id: Proposal UUID
        stale_reason: Description of why proposal is stale

    Returns:
        Updated proposal record or None
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("batch_proposals")
            .update({"stale_reason": stale_reason})
            .eq("id", str(proposal_id))
            .execute()
        )

        if response.data:
            logger.info(
                f"Marked proposal {proposal_id} as stale: {stale_reason}",
                extra={"proposal_id": str(proposal_id)},
            )
            return response.data[0]

        return None

    except Exception as e:
        logger.error(f"Error marking proposal stale: {e}", exc_info=True)
        return None


def archive_stale_proposals(project_id: UUID, max_age_hours: int = 24) -> list[dict[str, Any]]:
    """
    Archive stale and expired proposals for a project.

    A proposal is archived if:
    1. It has a stale_reason set, OR
    2. It's older than max_age_hours and still pending/previewed

    Args:
        project_id: Project UUID
        max_age_hours: Maximum age before soft expiration (default 24h)

    Returns:
        List of archived proposal records
    """
    supabase = get_supabase()
    archived = []

    try:
        from datetime import datetime, timezone, timedelta

        cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat()

        # Get proposals to archive (stale or expired)
        response = (
            supabase.table("batch_proposals")
            .select("*")
            .eq("project_id", str(project_id))
            .in_("status", ["pending", "previewed"])
            .execute()
        )

        if not response.data:
            return archived

        for proposal in response.data:
            should_archive = False
            archive_reason = None

            # Check if stale
            if proposal.get("stale_reason"):
                should_archive = True
                archive_reason = proposal["stale_reason"]

            # Check if expired by time
            elif proposal["created_at"] < cutoff_time:
                should_archive = True
                archive_reason = f"Expired after {max_age_hours} hours"

            if should_archive:
                # Archive the proposal
                update_response = (
                    supabase.table("batch_proposals")
                    .update({
                        "status": "archived",
                        "stale_reason": archive_reason,
                    })
                    .eq("id", proposal["id"])
                    .execute()
                )

                if update_response.data:
                    archived.append(update_response.data[0])
                    logger.info(
                        f"Archived proposal {proposal['id']}: {archive_reason}",
                        extra={"proposal_id": proposal["id"]},
                    )

        return archived

    except Exception as e:
        logger.error(f"Error archiving proposals: {e}", exc_info=True)
        return archived


def list_proposals_with_conflicts(project_id: UUID) -> list[dict[str, Any]]:
    """
    List pending proposals and detect conflicts between them.

    Conflicts occur when multiple proposals modify the same entity.

    Args:
        project_id: Project UUID

    Returns:
        List of proposals with conflict information added
    """
    supabase = get_supabase()

    try:
        # Get all pending/previewed proposals
        response = (
            supabase.table("batch_proposals")
            .select("*")
            .eq("project_id", str(project_id))
            .in_("status", ["pending", "previewed"])
            .order("created_at", desc=True)
            .execute()
        )

        proposals = response.data or []

        if len(proposals) <= 1:
            return proposals

        # Build entity → proposals map
        entity_proposals: dict[str, list[str]] = {}

        for proposal in proposals:
            changes = proposal.get("changes", [])
            for change in changes:
                entity_id = change.get("entity_id")
                if entity_id:
                    key = f"{change.get('entity_type')}:{entity_id}"
                    if key not in entity_proposals:
                        entity_proposals[key] = []
                    entity_proposals[key].append(proposal["id"])

        # Find conflicts
        conflicts: dict[str, list[str]] = {}
        for entity_key, proposal_ids in entity_proposals.items():
            if len(proposal_ids) > 1:
                for pid in proposal_ids:
                    if pid not in conflicts:
                        conflicts[pid] = []
                    conflicts[pid].append(entity_key)

        # Add conflict info to proposals
        for proposal in proposals:
            proposal_conflicts = conflicts.get(proposal["id"], [])
            if proposal_conflicts:
                proposal["has_conflicts"] = True
                proposal["conflicting_entities"] = proposal_conflicts
                # Find which other proposals conflict
                conflicting_proposals = set()
                for entity_key in proposal_conflicts:
                    for pid in entity_proposals.get(entity_key, []):
                        if pid != proposal["id"]:
                            conflicting_proposals.add(pid)
                proposal["conflicting_proposals"] = list(conflicting_proposals)
            else:
                proposal["has_conflicts"] = False
                proposal["conflicting_entities"] = []
                proposal["conflicting_proposals"] = []

            # Check staleness
            stale_reason = check_proposal_staleness(UUID(proposal["id"]))
            if stale_reason and not proposal.get("stale_reason"):
                proposal["stale_reason"] = stale_reason

        return proposals

    except Exception as e:
        logger.error(f"Error listing proposals with conflicts: {e}", exc_info=True)
        return []


def batch_apply_proposals(
    proposal_ids: list[UUID],
    applied_by: str | None = None,
) -> dict[str, Any]:
    """
    Apply multiple proposals in sequence.

    Args:
        proposal_ids: List of proposal UUIDs to apply
        applied_by: Optional identifier of who applied

    Returns:
        Summary dict with applied, failed, and skipped counts
    """
    results = {
        "applied": [],
        "failed": [],
        "skipped": [],
    }

    for proposal_id in proposal_ids:
        try:
            # Check if proposal is still valid
            proposal = get_proposal(proposal_id)

            if not proposal:
                results["skipped"].append({
                    "id": str(proposal_id),
                    "reason": "Not found",
                })
                continue

            if proposal["status"] not in ["pending", "previewed"]:
                results["skipped"].append({
                    "id": str(proposal_id),
                    "reason": f"Invalid status: {proposal['status']}",
                })
                continue

            # Check for staleness
            stale_reason = check_proposal_staleness(proposal_id)
            if stale_reason:
                results["skipped"].append({
                    "id": str(proposal_id),
                    "reason": f"Stale: {stale_reason}",
                })
                continue

            # Apply the proposal
            applied = apply_proposal(proposal_id, applied_by)
            results["applied"].append({
                "id": str(proposal_id),
                "title": proposal.get("title"),
            })

        except Exception as e:
            results["failed"].append({
                "id": str(proposal_id),
                "error": str(e),
            })

    logger.info(
        f"Batch apply: {len(results['applied'])} applied, "
        f"{len(results['failed'])} failed, {len(results['skipped'])} skipped",
    )

    return results


def batch_discard_proposals(proposal_ids: list[UUID]) -> dict[str, Any]:
    """
    Discard multiple proposals.

    Args:
        proposal_ids: List of proposal UUIDs to discard

    Returns:
        Summary dict with discarded and failed counts
    """
    supabase = get_supabase()
    results = {
        "discarded": [],
        "failed": [],
    }

    for proposal_id in proposal_ids:
        try:
            response = (
                supabase.table("batch_proposals")
                .update({"status": "discarded"})
                .eq("id", str(proposal_id))
                .in_("status", ["pending", "previewed"])
                .execute()
            )

            if response.data:
                results["discarded"].append(str(proposal_id))
            else:
                results["failed"].append({
                    "id": str(proposal_id),
                    "reason": "Not found or already processed",
                })

        except Exception as e:
            results["failed"].append({
                "id": str(proposal_id),
                "error": str(e),
            })

    logger.info(
        f"Batch discard: {len(results['discarded'])} discarded, "
        f"{len(results['failed'])} failed",
    )

    return results


def set_proposal_affected_entities(
    proposal_id: UUID,
    affected_entities: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """
    Set the affected entities list for staleness tracking.

    Args:
        proposal_id: Proposal UUID
        affected_entities: List of {entity_type, entity_id, updated_at}

    Returns:
        Updated proposal record or None
    """
    supabase = get_supabase()

    try:
        response = (
            supabase.table("batch_proposals")
            .update({"affected_entities": affected_entities})
            .eq("id", str(proposal_id))
            .execute()
        )

        return response.data[0] if response.data else None

    except Exception as e:
        logger.error(f"Error setting affected entities: {e}", exc_info=True)
        return None
