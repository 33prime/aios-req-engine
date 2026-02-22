"""Client Pulse & Activity endpoints for the Collaborate view.

Lightweight aggregation endpoints that power the consultant-side
collaboration dashboard.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends

from app.core.auth_middleware import get_current_user
from app.db.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/collaboration/projects/{project_id}",
    tags=["collaboration"],
)


@router.get("/pulse")
async def get_client_pulse(
    project_id: str,
    user=Depends(get_current_user),
):
    """Lightweight engagement metrics: pending counts, unread, next meeting."""
    sb = get_supabase()

    # Pending items in review queue (not yet packaged)
    pending_review_resp = (
        sb.table("pending_items")
        .select("id", count="exact")
        .eq("project_id", project_id)
        .eq("status", "pending")
        .execute()
    )
    pending_count = pending_review_resp.count or 0

    # Unread: package questions answered but not reviewed by consultant
    unread_resp = (
        sb.table("package_questions")
        .select("id, package_id", count="exact")
        .not_.is_("answer_text", "null")
        .execute()
    )
    # Filter to this project's packages
    if unread_resp.data:
        pkg_ids = {q["package_id"] for q in unread_resp.data}
        project_pkgs = sb.table("client_packages").select("id").eq(
            "project_id", project_id
        ).in_("id", list(pkg_ids)).execute()
        project_pkg_ids = {p["id"] for p in (project_pkgs.data or [])}
        unread_count = sum(1 for q in unread_resp.data if q["package_id"] in project_pkg_ids)
    else:
        unread_count = 0

    # Next meeting
    now_iso = datetime.utcnow().isoformat()
    meeting_resp = (
        sb.table("meetings")
        .select("title, meeting_date")
        .eq("project_id", project_id)
        .eq("status", "scheduled")
        .gte("meeting_date", now_iso)
        .order("meeting_date")
        .limit(1)
        .execute()
    )
    next_meeting = None
    if meeting_resp.data:
        m = meeting_resp.data[0]
        next_meeting = {"title": m["title"], "date": m["meeting_date"]}

    # Last client activity — check multiple sources for the most recent
    last_timestamps = []

    # From info_requests
    ir_resp = (
        sb.table("info_requests")
        .select("updated_at")
        .eq("project_id", project_id)
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )
    if ir_resp.data:
        last_timestamps.append(ir_resp.data[0]["updated_at"])

    # From package_questions (answered_at)
    try:
        pq_resp = (
            sb.table("client_packages")
            .select("id")
            .eq("project_id", project_id)
            .execute()
        )
        if pq_resp.data:
            pkg_ids = [p["id"] for p in pq_resp.data]
            ans_resp = (
                sb.table("package_questions")
                .select("answered_at")
                .in_("package_id", pkg_ids)
                .not_.is_("answered_at", "null")
                .order("answered_at", desc=True)
                .limit(1)
                .execute()
            )
            if ans_resp.data:
                last_timestamps.append(ans_resp.data[0]["answered_at"])
    except Exception:
        pass  # Table may not have data yet

    last_client_activity = max(last_timestamps) if last_timestamps else None

    return {
        "pending_count": pending_count,
        "unread_count": unread_count,
        "next_meeting": next_meeting,
        "last_client_activity": last_client_activity,
    }


@router.get("/client-activity")
async def get_client_activity(
    project_id: str,
    limit: int = 30,
    user=Depends(get_current_user),
):
    """Unified timeline of client actions: answers, uploads, views, confirmations, package events."""
    sb = get_supabase()

    items = []

    # 1. Package question answers
    try:
        pkgs_resp = sb.table("client_packages").select("id").eq("project_id", project_id).execute()
        pkg_ids = [p["id"] for p in (pkgs_resp.data or [])]
        if pkg_ids:
            answers_resp = (
                sb.table("package_questions")
                .select("id, question_text, answer_text, answered_by_name, answered_at")
                .in_("package_id", pkg_ids)
                .not_.is_("answer_text", "null")
                .order("answered_at", desc=True)
                .limit(limit)
                .execute()
            )
            for row in answers_resp.data or []:
                q_text = row.get("question_text", "a question")
                if len(q_text) > 60:
                    q_text = q_text[:57] + "..."
                items.append({
                    "id": f"pkg-answer-{row['id']}",
                    "type": "answer",
                    "actor_name": row.get("answered_by_name") or "Client",
                    "description": f'answered "{q_text}"',
                    "timestamp": row.get("answered_at") or "",
                })
    except Exception as e:
        logger.debug(f"Package questions query failed: {e}")

    # 2. File uploads
    try:
        if pkg_ids:
            uploads_resp = (
                sb.table("package_uploaded_files")
                .select("id, file_name, uploaded_by_name, uploaded_at")
                .in_("package_id", pkg_ids)
                .order("uploaded_at", desc=True)
                .limit(limit)
                .execute()
            )
            for row in uploads_resp.data or []:
                items.append({
                    "id": f"upload-{row['id']}",
                    "type": "upload",
                    "actor_name": row.get("uploaded_by_name") or "Client",
                    "description": f'uploaded "{row.get("file_name", "a file")}"',
                    "timestamp": row.get("uploaded_at") or "",
                })
    except Exception as e:
        logger.debug(f"File uploads query failed: {e}")

    # 3. Packages sent (consultant action, but contextual)
    try:
        sent_resp = (
            sb.table("client_packages")
            .select("id, questions_count, action_items_count, sent_at")
            .eq("project_id", project_id)
            .not_.is_("sent_at", "null")
            .order("sent_at", desc=True)
            .limit(10)
            .execute()
        )
        for row in sent_resp.data or []:
            q = row.get("questions_count", 0)
            items.append({
                "id": f"pkg-sent-{row['id']}",
                "type": "package_sent",
                "actor_name": "You",
                "description": f"sent package with {q} question{'s' if q != 1 else ''}",
                "timestamp": row.get("sent_at") or "",
            })
    except Exception as e:
        logger.debug(f"Packages sent query failed: {e}")

    # 4. Prototype sessions
    try:
        sessions_resp = (
            sb.table("prototype_sessions")
            .select("id, created_at, duration_seconds")
            .eq("project_id", project_id)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )
        for row in sessions_resp.data or []:
            duration = row.get("duration_seconds") or 0
            mins = round(duration / 60)
            items.append({
                "id": f"proto-{row['id']}",
                "type": "prototype_view",
                "actor_name": "Client",
                "description": f"reviewed prototype{f' ({mins} min)' if mins > 0 else ''}",
                "timestamp": row.get("created_at") or "",
            })
    except Exception as e:
        logger.debug(f"Prototype sessions query failed: {e}")

    # 5. Legacy info_request completions (answers from older system)
    try:
        legacy_resp = (
            sb.table("info_requests")
            .select("id, title, completed_at, best_answered_by")
            .eq("project_id", project_id)
            .eq("status", "completed")
            .order("completed_at", desc=True)
            .limit(limit)
            .execute()
        )
        for row in legacy_resp.data or []:
            items.append({
                "id": f"legacy-answer-{row['id']}",
                "type": "answer",
                "actor_name": row.get("best_answered_by") or "Client",
                "description": f'answered "{row.get("title", "a question")}"',
                "timestamp": row.get("completed_at") or "",
            })
    except Exception as e:
        logger.debug(f"Legacy info_requests query failed: {e}")

    # Sort by timestamp descending, deduplicate
    items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    return {"items": items[:limit]}
