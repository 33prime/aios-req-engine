"""
Risk Extraction Chain - Extracts risks from project signals.

Identifies technical, business, market, team, timeline, budget, compliance,
security, operational, and strategic risks.
"""

from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.risks import smart_upsert_risk
from app.db.signals import list_project_signals, list_signal_chunks

logger = get_logger(__name__)


class ExtractedRisk(BaseModel):
    """A risk extracted from signals."""

    title: str = Field(..., description="Short risk title (e.g., 'Key developer might leave', 'Regulatory approval delay')")
    description: str = Field(..., description="Detailed description of the risk")
    risk_type: str = Field(..., description="Type: technical, business, market, team, timeline, budget, compliance, security, operational, strategic")
    severity: str = Field(..., description="Impact: critical, high, medium, low")
    likelihood: str | None = Field(None, description="Probability: very_high, high, medium, low, very_low")
    impact: str | None = Field(None, description="Detailed impact if risk occurs")
    mitigation_strategy: str | None = Field(None, description="How to prevent/reduce")
    confidence: float = Field(0.0, description="Extraction confidence (0.0-1.0)")


class RiskExtractionResult(BaseModel):
    """Result of risk extraction."""

    risks: list[ExtractedRisk] = Field(default_factory=list)
    reasoning: str | None = None


async def extract_risks_from_signals(
    project_id: UUID,
    signal_ids: list[UUID] | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """
    Extract risks from project signals.

    Args:
        project_id: Project UUID
        signal_ids: Optional specific signals to analyze (if None, uses recent signals)
        limit: Max signals to process

    Returns:
        Dict with:
        - success: bool
        - risks_created: int
        - risks_updated: int
        - risks_merged: int
        - risks: list of extracted risks
        - signals_processed: int
        - error: str | None
    """
    settings = get_settings()

    result = {
        "success": False,
        "risks_created": 0,
        "risks_updated": 0,
        "risks_merged": 0,
        "risks": [],
        "signals_processed": 0,
        "error": None,
    }

    try:
        # Get signals to process
        if signal_ids:
            signals = []
            for sid in signal_ids:
                chunks = list_signal_chunks(sid)
                if chunks:
                    signals.append({
                        "id": str(sid),
                        "content": chunks[0].get("content", ""),
                        "title": chunks[0].get("content", "")[:100],
                    })
        else:
            signal_response = list_project_signals(project_id, limit=limit)
            signals = signal_response.get("signals", [])

        if not signals:
            result["error"] = "No signals to process"
            return result

        logger.info(f"Extracting risks from {len(signals)} signals for project {project_id}")

        # Process signals in batches
        for signal in signals[:limit]:
            signal_id = signal.get("id")
            if not signal_id:
                continue

            try:
                # Get signal content
                chunks = list_signal_chunks(UUID(signal_id))
                if not chunks:
                    content = signal.get("content", "")[:4000]
                else:
                    content = "\n\n".join([c.get("content", "")[:2000] for c in chunks[:3]])

                if not content:
                    continue

                # Extract risks from this signal
                parser = PydanticOutputParser(pydantic_object=RiskExtractionResult)

                system_prompt = f"""You are a risk assessment specialist. Analyze project signals and identify potential risks.

**Risk Categories:**
- technical: Architecture, infrastructure, technology choices, technical debt
- business: Revenue, market fit, business model, partnerships
- market: Competition, market timing, demand shifts
- team: Staffing, skills gaps, key person dependencies, turnover
- timeline: Schedule delays, missed milestones, underestimated effort
- budget: Cost overruns, funding gaps, resource constraints
- compliance: Regulatory, legal, privacy, security requirements
- security: Data breaches, vulnerabilities, attack vectors
- operational: Process breakdowns, scalability, reliability
- strategic: Misalignment, priority conflicts, changing requirements

**Severity Levels:**
- critical: Project-threatening, blocking, major revenue loss
- high: Significant setback, major rework, competitive disadvantage
- medium: Manageable issue, requires attention, has workarounds
- low: Minor inconvenience, edge case, cosmetic

**Instructions:**
- Identify concrete, specific risks (not vague concerns)
- Assess severity honestly - not everything is critical
- Include mitigation strategies when mentioned
- Only extract risks actually mentioned or strongly implied
- Set confidence based on how explicit the risk is

{parser.get_format_instructions()}"""

                user_prompt = f"""Analyze this signal for project risks:

{content}

Extract all identifiable risks with their type, severity, likelihood, and mitigation strategies."""

                model = ChatOpenAI(
                    model="gpt-4o",
                    temperature=0.1,
                    api_key=settings.OPENAI_API_KEY,
                )

                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ]

                response = await model.ainvoke(messages)
                extraction = parser.parse(response.content)

                result["signals_processed"] += 1

                # Upsert each extracted risk
                for risk in extraction.risks:
                    try:
                        # Build evidence
                        evidence = {
                            "signal_id": signal_id,
                            "chunk_id": chunks[0]["id"] if chunks else signal_id,
                            "text": risk.description[:500],
                            "confidence": risk.confidence,
                        }

                        # Smart upsert
                        _, action = smart_upsert_risk(
                            project_id=project_id,
                            title=risk.title,
                            description=risk.description,
                            risk_type=risk.risk_type,
                            severity=risk.severity,
                            new_evidence=[evidence],
                            source_signal_id=UUID(signal_id),
                            created_by="system",
                            likelihood=risk.likelihood or "medium",
                            impact=risk.impact,
                            mitigation_strategy=risk.mitigation_strategy,
                        )

                        # Track action
                        if action == "created":
                            result["risks_created"] += 1
                        elif action == "updated":
                            result["risks_updated"] += 1
                        elif action == "merged":
                            result["risks_merged"] += 1

                        result["risks"].append(risk.model_dump())

                        logger.debug(f"{action.capitalize()} {risk.risk_type} risk: {risk.title[:50]}")

                    except Exception as e:
                        logger.warning(f"Failed to upsert risk: {e}")

            except Exception as e:
                logger.warning(f"Failed to process signal {signal_id}: {e}")
                continue

        logger.info(
            f"Risk extraction complete: created={result['risks_created']}, "
            f"updated={result['risks_updated']}, merged={result['risks_merged']}"
        )

        result["success"] = True
        return result

    except Exception as e:
        error_msg = f"Risk extraction failed: {str(e)}"
        result["error"] = error_msg
        logger.error(error_msg, exc_info=True)
        return result
