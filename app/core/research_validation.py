"""
Research data validation utilities.

Provides additional validation beyond Pydantic schema validation:
- Content quality checks
- Data completeness scoring
- Warning detection
"""

from typing import List, Dict, Any, Tuple
from app.core.schemas_research import ResearchReport


class ValidationWarning:
    """Warning about research data quality"""

    def __init__(self, field: str, message: str, severity: str = "warning"):
        self.field = field
        self.message = message
        self.severity = severity  # "info", "warning", "error"

    def __repr__(self):
        return f"{self.severity.upper()}: {self.field} - {self.message}"


def validate_research_report(report: ResearchReport) -> Tuple[bool, List[ValidationWarning]]:
    """
    Validate research report for data quality and completeness.

    Args:
        report: ResearchReport to validate

    Returns:
        Tuple of (is_valid, warnings)
        - is_valid: False if critical errors, True otherwise
        - warnings: List of ValidationWarning objects

    Example:
        >>> is_valid, warnings = validate_research_report(report)
        >>> if not is_valid:
        ...     raise ValueError(f"Invalid report: {warnings}")
        >>> for warning in warnings:
        ...     logger.warning(str(warning))
    """
    warnings = []
    is_valid = True

    # Check title and summary
    if not report.title or len(report.title.strip()) < 5:
        warnings.append(
            ValidationWarning(
                "title",
                "Title is too short or empty (should be at least 5 characters)",
                "error",
            )
        )
        is_valid = False

    if not report.summary or len(report.summary.strip()) < 20:
        warnings.append(
            ValidationWarning(
                "summary",
                "Summary is too short or empty (should be at least 20 characters)",
                "error",
            )
        )
        is_valid = False

    # Check idea analysis
    if not report.idea_analysis.content or len(report.idea_analysis.content.strip()) < 50:
        warnings.append(
            ValidationWarning(
                "idea_analysis.content",
                "Idea analysis content is too short (should be at least 50 characters)",
                "warning",
            )
        )

    # Check feature matrix
    if not report.feature_matrix.must_have:
        warnings.append(
            ValidationWarning(
                "feature_matrix.must_have",
                "No must-have features listed",
                "warning",
            )
        )

    if len(report.feature_matrix.must_have) < 2:
        warnings.append(
            ValidationWarning(
                "feature_matrix.must_have",
                "Very few must-have features (less than 2)",
                "info",
            )
        )

    # Check personas
    if not report.user_personas:
        warnings.append(
            ValidationWarning(
                "user_personas",
                "No user personas defined",
                "warning",
            )
        )

    if len(report.user_personas) < 2:
        warnings.append(
            ValidationWarning(
                "user_personas",
                "Only one persona defined (consider adding more)",
                "info",
            )
        )

    # Check risks
    if not report.risks_and_mitigations:
        warnings.append(
            ValidationWarning(
                "risks_and_mitigations",
                "No risks identified",
                "warning",
            )
        )

    # Check pain points
    if not report.market_pain_points.macro_pressures and not report.market_pain_points.company_specific:
        warnings.append(
            ValidationWarning(
                "market_pain_points",
                "No pain points identified (macro or company-specific)",
                "warning",
            )
        )

    # Check USPs
    if not report.unique_selling_propositions:
        warnings.append(
            ValidationWarning(
                "unique_selling_propositions",
                "No USPs defined",
                "warning",
            )
        )

    # Check market data
    if not report.market_data.content or len(report.market_data.content.strip()) < 50:
        warnings.append(
            ValidationWarning(
                "market_data.content",
                "Market data is missing or too short",
                "info",
            )
        )

    return is_valid, warnings


def get_completeness_score(report: ResearchReport) -> Dict[str, Any]:
    """
    Calculate completeness score for research report.

    Returns a score (0-100) based on how many key sections are populated.

    Args:
        report: ResearchReport to score

    Returns:
        Dictionary with:
        - score: 0-100 completeness score
        - missing_sections: List of missing/incomplete sections
        - section_scores: Dict of individual section scores

    Example:
        >>> score_data = get_completeness_score(report)
        >>> print(f"Completeness: {score_data['score']}%")
        >>> if score_data['score'] < 70:
        ...     logger.warning(f"Incomplete research: {score_data['missing_sections']}")
    """
    section_scores = {}
    missing_sections = []

    # Score each section (True = 1 point, False = 0 points)
    checks = {
        "title": bool(report.title and len(report.title.strip()) >= 5),
        "summary": bool(report.summary and len(report.summary.strip()) >= 20),
        "verdict": bool(report.verdict and len(report.verdict.strip()) >= 10),
        "idea_analysis": bool(
            report.idea_analysis.content and len(report.idea_analysis.content.strip()) >= 50
        ),
        "market_pain_points": bool(
            report.market_pain_points.macro_pressures
            or report.market_pain_points.company_specific
        ),
        "feature_matrix_must_have": bool(report.feature_matrix.must_have),
        "feature_matrix_unique": bool(report.feature_matrix.unique_advanced),
        "goals_and_benefits": bool(
            report.goals_and_benefits.organizational_goals
            or report.goals_and_benefits.stakeholder_benefits
        ),
        "usps": bool(report.unique_selling_propositions),
        "personas": bool(report.user_personas),
        "risks": bool(report.risks_and_mitigations),
        "market_data": bool(
            report.market_data.content and len(report.market_data.content.strip()) >= 50
        ),
    }

    for section, is_complete in checks.items():
        section_scores[section] = 1 if is_complete else 0
        if not is_complete:
            missing_sections.append(section)

    # Calculate overall score
    total_sections = len(checks)
    completed_sections = sum(section_scores.values())
    score = int((completed_sections / total_sections) * 100)

    return {
        "score": score,
        "completed_sections": completed_sections,
        "total_sections": total_sections,
        "missing_sections": missing_sections,
        "section_scores": section_scores,
    }


def get_content_statistics(report: ResearchReport) -> Dict[str, Any]:
    """
    Get content statistics for research report.

    Useful for logging and monitoring research quality.

    Args:
        report: ResearchReport to analyze

    Returns:
        Dictionary with counts and metrics

    Example:
        >>> stats = get_content_statistics(report)
        >>> logger.info(
        ...     "Research stats",
        ...     extra={
        ...         "must_have_features": stats["feature_counts"]["must_have"],
        ...         "personas": stats["persona_count"],
        ...         "risks": stats["risk_count"],
        ...     }
        ... )
    """
    return {
        "title_length": len(report.title),
        "summary_length": len(report.summary),
        "verdict_length": len(report.verdict),
        "feature_counts": {
            "must_have": len(report.feature_matrix.must_have),
            "unique_advanced": len(report.feature_matrix.unique_advanced),
            "total": len(report.feature_matrix.must_have)
            + len(report.feature_matrix.unique_advanced),
        },
        "persona_count": len(report.user_personas),
        "risk_count": len(report.risks_and_mitigations),
        "usp_count": len(report.unique_selling_propositions),
        "pain_point_counts": {
            "macro": len(report.market_pain_points.macro_pressures),
            "company": len(report.market_pain_points.company_specific),
            "total": len(report.market_pain_points.macro_pressures)
            + len(report.market_pain_points.company_specific),
        },
        "goal_counts": {
            "organizational": len(report.goals_and_benefits.organizational_goals),
            "stakeholder": len(report.goals_and_benefits.stakeholder_benefits),
            "total": len(report.goals_and_benefits.organizational_goals)
            + len(report.goals_and_benefits.stakeholder_benefits),
        },
        "market_data_length": len(report.market_data.content),
    }
