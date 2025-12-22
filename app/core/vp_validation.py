"""
Value Path (VP) completeness validation utilities.

Validates VP steps for prototype readiness:
- Data schema completeness
- Business logic completeness
- Transition logic completeness
- User benefit clarity
"""

from typing import List, Dict, Any, Tuple


class VPGap:
    """Gap in VP completeness"""

    def __init__(
        self,
        step_index: int,
        step_label: str,
        gap_type: str,
        severity: str,
        description: str,
    ):
        self.step_index = step_index
        self.step_label = step_label
        self.gap_type = gap_type  # "data_schema", "business_logic", "transition_logic", "user_benefit"
        self.severity = severity  # "critical", "important", "minor"
        self.description = description

    def __repr__(self):
        return f"VP Step {self.step_index} ({self.step_label}): {self.severity.upper()} - {self.gap_type} - {self.description}"


def validate_vp_step_completeness(vp_step: Dict[str, Any]) -> List[VPGap]:
    """
    Validate a single VP step for completeness.

    Checks for:
    - Data schema (entities, fields, types)
    - Business logic (validation rules, special sauce)
    - Transition logic (what triggers next step)
    - User benefit (value created)

    Args:
        vp_step: VP step dictionary with enrichment data

    Returns:
        List of VPGap objects describing missing elements

    Example:
        >>> step = {"step_index": 1, "label": "Create route", "enrichment": {...}}
        >>> gaps = validate_vp_step_completeness(step)
        >>> for gap in gaps:
        ...     print(gap)
    """
    gaps = []
    step_index = vp_step.get("step_index", 0)
    step_label = vp_step.get("label", "Unknown")
    enrichment = vp_step.get("enrichment", {})

    # Check data schema
    data_schema = enrichment.get("data_schema")
    if not data_schema:
        gaps.append(
            VPGap(
                step_index=step_index,
                step_label=step_label,
                gap_type="data_schema",
                severity="critical",
                description="No data schema defined (entities, fields, types missing)",
            )
        )
    elif isinstance(data_schema, dict):
        # Check if schema has entities
        entities = data_schema.get("entities", [])
        if not entities:
            gaps.append(
                VPGap(
                    step_index=step_index,
                    step_label=step_label,
                    gap_type="data_schema",
                    severity="important",
                    description="Data schema has no entities defined",
                )
            )
        else:
            # Check if entities have fields
            for entity in entities:
                if isinstance(entity, dict):
                    fields = entity.get("fields", [])
                    if not fields:
                        entity_name = entity.get("name", "Unknown")
                        gaps.append(
                            VPGap(
                                step_index=step_index,
                                step_label=step_label,
                                gap_type="data_schema",
                                severity="important",
                                description=f"Entity '{entity_name}' has no fields defined",
                            )
                        )

    # Check business logic
    business_logic = enrichment.get("business_logic")
    if not business_logic:
        gaps.append(
            VPGap(
                step_index=step_index,
                step_label=step_label,
                gap_type="business_logic",
                severity="critical",
                description="No business logic defined (validation rules, special sauce missing)",
            )
        )
    elif isinstance(business_logic, (str, list)):
        # Check if business logic is substantial
        logic_text = " ".join(business_logic) if isinstance(business_logic, list) else business_logic
        if len(logic_text.strip()) < 20:
            gaps.append(
                VPGap(
                    step_index=step_index,
                    step_label=step_label,
                    gap_type="business_logic",
                    severity="important",
                    description="Business logic is too brief (needs more detail)",
                )
            )

    # Check transition logic
    transition_logic = enrichment.get("transition_logic")
    if not transition_logic:
        gaps.append(
            VPGap(
                step_index=step_index,
                step_label=step_label,
                gap_type="transition_logic",
                severity="important",
                description="No transition logic defined (unclear what triggers next step)",
            )
        )

    # Check user benefit
    user_benefit = vp_step.get("user_benefit_pain") or enrichment.get("user_benefit")
    if not user_benefit:
        gaps.append(
            VPGap(
                step_index=step_index,
                step_label=step_label,
                gap_type="user_benefit",
                severity="important",
                description="No user benefit defined (unclear value created)",
            )
        )
    elif isinstance(user_benefit, str) and len(user_benefit.strip()) < 15:
        gaps.append(
            VPGap(
                step_index=step_index,
                step_label=step_label,
                gap_type="user_benefit",
                severity="minor",
                description="User benefit is too brief (needs more explanation)",
            )
        )

    return gaps


def validate_vp_completeness(vp_steps: List[Dict[str, Any]]) -> Tuple[List[VPGap], Dict[str, Any]]:
    """
    Validate all VP steps for completeness.

    Args:
        vp_steps: List of VP step dictionaries

    Returns:
        Tuple of (gaps, summary)
        - gaps: List of all VPGap objects
        - summary: Dictionary with statistics

    Example:
        >>> gaps, summary = validate_vp_completeness(vp_steps)
        >>> print(f"Completeness: {summary['completeness_percent']}%")
        >>> print(f"Critical gaps: {summary['critical_count']}")
        >>> for gap in gaps:
        ...     if gap.severity == "critical":
        ...         print(gap)
    """
    all_gaps = []

    for step in vp_steps:
        step_gaps = validate_vp_step_completeness(step)
        all_gaps.extend(step_gaps)

    # Calculate summary statistics
    total_steps = len(vp_steps)
    steps_with_gaps = len(set(g.step_index for g in all_gaps))
    complete_steps = total_steps - steps_with_gaps

    critical_gaps = [g for g in all_gaps if g.severity == "critical"]
    important_gaps = [g for g in all_gaps if g.severity == "important"]
    minor_gaps = [g for g in all_gaps if g.severity == "minor"]

    # Group gaps by type
    gaps_by_type = {}
    for gap in all_gaps:
        if gap.gap_type not in gaps_by_type:
            gaps_by_type[gap.gap_type] = []
        gaps_by_type[gap.gap_type].append(gap)

    summary = {
        "total_steps": total_steps,
        "complete_steps": complete_steps,
        "steps_with_gaps": steps_with_gaps,
        "completeness_percent": int((complete_steps / total_steps * 100)) if total_steps > 0 else 0,
        "total_gaps": len(all_gaps),
        "critical_count": len(critical_gaps),
        "important_count": len(important_gaps),
        "minor_count": len(minor_gaps),
        "gaps_by_type": {k: len(v) for k, v in gaps_by_type.items()},
        "is_prototype_ready": len(critical_gaps) == 0,  # No critical gaps = ready
    }

    return all_gaps, summary


def format_vp_gaps_for_prompt(gaps: List[VPGap]) -> str:
    """
    Format VP gaps for inclusion in LLM prompt.

    Args:
        gaps: List of VPGap objects

    Returns:
        Formatted string for prompt

    Example:
        >>> formatted = format_vp_gaps_for_prompt(gaps)
        >>> prompt = f"Current VP gaps:\n{formatted}\n\nAnalyze..."
    """
    if not gaps:
        return "No VP completeness gaps detected. All steps have data schemas, business logic, and transitions defined."

    lines = ["VP COMPLETENESS GAPS:\n"]

    # Group by severity
    critical = [g for g in gaps if g.severity == "critical"]
    important = [g for g in gaps if g.severity == "important"]
    minor = [g for g in gaps if g.severity == "minor"]

    if critical:
        lines.append("CRITICAL (blocks prototyping):")
        for gap in critical:
            lines.append(f"  • Step {gap.step_index} ({gap.step_label}): {gap.description}")
        lines.append("")

    if important:
        lines.append("IMPORTANT (should address):")
        for gap in important:
            lines.append(f"  • Step {gap.step_index} ({gap.step_label}): {gap.description}")
        lines.append("")

    if minor:
        lines.append("MINOR (nice to have):")
        for gap in minor:
            lines.append(f"  • Step {gap.step_index} ({gap.step_label}): {gap.description}")

    return "\n".join(lines)
