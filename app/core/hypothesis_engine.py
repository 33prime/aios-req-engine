"""Hypothesis engine — surfaces testable beliefs and tracks their lifecycle.

Hypotheses are beliefs with mid-range confidence (0.4-0.84) that have at least
one supporting fact. They can be:
- proposed: newly identified as testable
- testing: actively being validated
- graduated: confidence reached 0.85+ (became a strong belief)
- rejected: confidence dropped to 0.3 or below

Scanning is deterministic (no LLM). Test suggestions use Haiku optionally.
"""

import time
from uuid import UUID

from app.core.logging import get_logger
from app.core.schemas_briefing import Hypothesis, HypothesisStatus

logger = get_logger(__name__)

# Confidence thresholds
HYPOTHESIS_MIN_CONFIDENCE = 0.4
HYPOTHESIS_MAX_CONFIDENCE = 0.84
GRADUATE_THRESHOLD = 0.85
REJECT_THRESHOLD = 0.3


def scan_for_hypotheses(project_id: UUID) -> list[Hypothesis]:
    """Find beliefs suitable for hypothesis tracking.

    Criteria:
    - Belief type, active
    - Confidence between 0.4 and 0.84
    - Has at least 1 supporting edge (not purely speculative)
    """
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()
    pid = str(project_id)

    try:
        result = (
            supabase.table("memory_nodes")
            .select("id, content, summary, confidence, belief_domain, hypothesis_status, evidence_for_count, evidence_against_count")
            .eq("project_id", pid)
            .eq("node_type", "belief")
            .eq("is_active", True)
            .gte("confidence", HYPOTHESIS_MIN_CONFIDENCE)
            .lte("confidence", HYPOTHESIS_MAX_CONFIDENCE)
            .order("confidence", desc=True)
            .limit(20)
            .execute()
        )

        hypotheses: list[Hypothesis] = []
        for node in result.data or []:
            # Already tracked as hypothesis — include regardless
            if node.get("hypothesis_status"):
                hypotheses.append(_node_to_hypothesis(node))
                continue

            # Need at least 1 evidence edge to be worth tracking
            evidence_for = node.get("evidence_for_count", 0) or 0
            if evidence_for > 0:
                hypotheses.append(_node_to_hypothesis(node))

        return hypotheses[:10]

    except Exception as e:
        logger.warning(f"Hypothesis scan failed: {e}")
        return []


def get_active_hypotheses(project_id: UUID) -> list[Hypothesis]:
    """Get all hypotheses with an active status (proposed or testing)."""
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()
    pid = str(project_id)

    try:
        result = (
            supabase.table("memory_nodes")
            .select("id, content, summary, confidence, belief_domain, hypothesis_status, evidence_for_count, evidence_against_count")
            .eq("project_id", pid)
            .eq("node_type", "belief")
            .eq("is_active", True)
            .in_("hypothesis_status", ["proposed", "testing"])
            .order("confidence", desc=True)
            .limit(10)
            .execute()
        )

        return [_node_to_hypothesis(n) for n in (result.data or [])]
    except Exception as e:
        logger.warning(f"Active hypotheses query failed: {e}")
        return []


def promote_to_hypothesis(node_id: UUID) -> dict:
    """Promote a belief to hypothesis status='proposed'."""
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()

    try:
        response = (
            supabase.table("memory_nodes")
            .update({"hypothesis_status": "proposed"})
            .eq("id", str(node_id))
            .eq("node_type", "belief")
            .execute()
        )
        if response.data:
            logger.info(f"Promoted node {node_id} to hypothesis")
            return response.data[0]
        return {}
    except Exception as e:
        logger.error(f"Failed to promote hypothesis {node_id}: {e}")
        raise


def update_hypothesis_evidence(node_id: UUID) -> dict | None:
    """Recount evidence edges and auto-graduate/reject.

    Called by memory agent after new edges are created.
    Returns updated node or None if no change needed.
    """
    from app.db.memory_graph import count_edges_to_node, get_node
    from app.db.supabase_client import get_supabase

    supabase = get_supabase()
    node = get_node(node_id)
    if not node or node.get("node_type") != "belief":
        return None

    # Count evidence
    for_count = count_edges_to_node(node_id, edge_type="supports")
    against_count = count_edges_to_node(node_id, edge_type="contradicts")
    confidence = node.get("confidence", 0.5)

    updates: dict = {
        "evidence_for_count": for_count,
        "evidence_against_count": against_count,
    }

    # Auto-graduate if confidence >= 0.85
    if confidence >= GRADUATE_THRESHOLD and node.get("hypothesis_status") in ("proposed", "testing"):
        updates["hypothesis_status"] = "graduated"
        logger.info(f"Hypothesis {node_id} graduated (confidence={confidence:.2f})")

    # Auto-reject if confidence <= 0.3
    elif confidence <= REJECT_THRESHOLD and node.get("hypothesis_status") in ("proposed", "testing"):
        updates["hypothesis_status"] = "rejected"
        logger.info(f"Hypothesis {node_id} rejected (confidence={confidence:.2f})")

    try:
        response = (
            supabase.table("memory_nodes")
            .update(updates)
            .eq("id", str(node_id))
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception as e:
        logger.warning(f"Failed to update hypothesis evidence for {node_id}: {e}")
        return None


async def generate_test_suggestions(
    hypotheses: list[Hypothesis],
    project_id: str | None = None,
) -> list[dict]:
    """Generate test suggestions for hypotheses via Haiku.

    Only called for newly proposed hypotheses. Cost: ~$0.0003.
    Returns list of {hypothesis_id, test_suggestion}.
    """
    if not hypotheses:
        return []

    # Only generate for proposed hypotheses without existing suggestions
    to_suggest = [h for h in hypotheses if h.status == HypothesisStatus.PROPOSED and not h.test_suggestion]
    if not to_suggest:
        return []

    from anthropic import AsyncAnthropic

    from app.core.config import get_settings
    from app.core.llm_usage import log_llm_usage

    import json

    HAIKU_MODEL = "claude-haiku-4-5-20251001"

    lines = []
    for h in to_suggest[:5]:
        lines.append(f"- [{h.hypothesis_id}] {h.statement} (confidence: {h.confidence:.0%}, {h.evidence_for} supporting, {h.evidence_against} contradicting)")

    settings = get_settings()
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    start = time.time()
    response = await client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=512,
        temperature=0.3,
        system="You suggest how a consultant could test/validate project beliefs. "
               "For each hypothesis, suggest ONE concrete action (ask a stakeholder, review a doc, run a test). "
               "Be specific. Return JSON array of {id, suggestion}. No markdown fences.",
        messages=[{"role": "user", "content": f"Hypotheses to test:\n" + "\n".join(lines)}],
    )
    duration_ms = int((time.time() - start) * 1000)

    usage = response.usage
    log_llm_usage(
        workflow="hypothesis_test_suggestions",
        model=HAIKU_MODEL,
        provider="anthropic",
        tokens_input=usage.input_tokens,
        tokens_output=usage.output_tokens,
        duration_ms=duration_ms,
        chain="generate_test_suggestions",
        project_id=project_id,
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        suggestions = json.loads(text)
        return [
            {"hypothesis_id": s.get("id", ""), "test_suggestion": s.get("suggestion", "")}
            for s in suggestions
            if s.get("suggestion")
        ]
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning(f"Failed to parse test suggestions: {e}")
        return []


def _node_to_hypothesis(node: dict) -> Hypothesis:
    """Convert a memory_node dict to a Hypothesis model."""
    status_str = node.get("hypothesis_status")
    try:
        status = HypothesisStatus(status_str) if status_str else HypothesisStatus.PROPOSED
    except ValueError:
        status = HypothesisStatus.PROPOSED

    return Hypothesis(
        hypothesis_id=node["id"],
        statement=node.get("summary") or node.get("content", "")[:120],
        status=status,
        confidence=node.get("confidence", 0.5),
        evidence_for=node.get("evidence_for_count", 0) or 0,
        evidence_against=node.get("evidence_against_count", 0) or 0,
        domain=node.get("belief_domain"),
    )
