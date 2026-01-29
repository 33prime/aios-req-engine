"""Prep Stage Configuration.

Defines stage-specific settings for generating prep materials:
- Question goals and categories
- Document strategy and priorities
- Agenda sections
- Typical duration

This configuration drives the stage-aware prep generation system.
"""

from dataclasses import dataclass, field
from typing import Optional

from app.core.schemas_collaboration import CollaborationPhase


@dataclass
class PrepStageConfig:
    """Configuration for a specific collaboration phase's prep generation."""

    phase: CollaborationPhase

    # Question generation settings
    question_goal: str
    question_categories: list[str] = field(default_factory=list)

    # Document recommendation settings
    document_strategy: str = ""
    document_priorities: list[str] = field(default_factory=list)

    # Agenda generation settings
    agenda_sections: list[str] = field(default_factory=list)

    # Meeting settings
    typical_duration: int = 30  # minutes

    # LLM temperature (higher = more creative)
    question_temperature: float = 0.4
    document_temperature: float = 0.3


# Pre-Discovery: Before the first discovery call
PRE_DISCOVERY_CONFIG = PrepStageConfig(
    phase=CollaborationPhase.PRE_DISCOVERY,
    question_goal="Extract requirements and understand the problem space",
    question_categories=[
        "Current workflow and pain points",
        "Success criteria and business goals",
        "Constraints and dependencies",
        "User types and stakeholders",
    ],
    document_strategy="Fill knowledge gaps before first conversation",
    document_priorities=[
        "process_docs",
        "org_chart",
        "sample_data",
        "screenshots",
        "existing_specs",
    ],
    agenda_sections=[
        "Opening & Introductions",
        "Current State Deep Dive",
        "Future State Vision",
        "Requirements Discussion",
        "Next Steps & Timeline",
    ],
    typical_duration=45,
    question_temperature=0.4,
)

# Discovery: During active discovery
DISCOVERY_CONFIG = PrepStageConfig(
    phase=CollaborationPhase.DISCOVERY,
    question_goal="Explore requirements and capture detailed needs",
    question_categories=[
        "Workflow specifics and edge cases",
        "User needs and preferences",
        "Technical requirements",
        "Business rules and logic",
    ],
    document_strategy="Capture evidence for requirements being discussed",
    document_priorities=[
        "workflow_examples",
        "data_samples",
        "user_feedback",
        "technical_docs",
    ],
    agenda_sections=[
        "Review Previous Findings",
        "Deep Dive Topics",
        "Open Questions",
        "Action Items",
    ],
    typical_duration=60,
    question_temperature=0.4,
)

# Validation: Confirming extracted requirements
VALIDATION_CONFIG = PrepStageConfig(
    phase=CollaborationPhase.VALIDATION,
    question_goal="Validate extracted requirements and confirm priorities",
    question_categories=[
        "Feature accuracy confirmation",
        "Priority and MVP scope",
        "Missing requirements identification",
        "Acceptance criteria clarity",
    ],
    document_strategy="Support requirement validation with specifics",
    document_priorities=[
        "feature_specs",
        "acceptance_criteria",
        "priority_matrix",
        "user_stories",
    ],
    agenda_sections=[
        "Requirements Overview",
        "Feature Walkthrough",
        "Priority Discussion",
        "Gap Identification",
        "Confirmation & Sign-off",
    ],
    typical_duration=30,
    question_temperature=0.3,  # More focused
)

# Prototype: Getting feedback on designs
PROTOTYPE_CONFIG = PrepStageConfig(
    phase=CollaborationPhase.PROTOTYPE,
    question_goal="Gather feedback on design and user experience",
    question_categories=[
        "Visual design direction",
        "Workflow and interaction feedback",
        "Missing screens or features",
        "Edge cases and error states",
    ],
    document_strategy="Provide design context and references",
    document_priorities=[
        "brand_guide",
        "design_references",
        "competitor_screenshots",
        "user_flow_diagrams",
    ],
    agenda_sections=[
        "Prototype Overview",
        "Screen-by-Screen Walkthrough",
        "Feedback Discussion",
        "Priority Changes",
        "Next Iteration Planning",
    ],
    typical_duration=30,
    question_temperature=0.4,
)

# Proposal: Finalizing scope and sign-off
PROPOSAL_CONFIG = PrepStageConfig(
    phase=CollaborationPhase.PROPOSAL,
    question_goal="Finalize scope, timeline, and investment",
    question_categories=[
        "Scope confirmation",
        "Timeline expectations",
        "Budget alignment",
        "Risk and dependencies",
    ],
    document_strategy="Provide comprehensive proposal documentation",
    document_priorities=[
        "scope_document",
        "timeline",
        "budget_breakdown",
        "terms",
    ],
    agenda_sections=[
        "Proposal Overview",
        "Scope Review",
        "Timeline & Milestones",
        "Investment Discussion",
        "Questions & Next Steps",
    ],
    typical_duration=45,
    question_temperature=0.2,  # Very focused
)

# Build: Ongoing development feedback
BUILD_CONFIG = PrepStageConfig(
    phase=CollaborationPhase.BUILD,
    question_goal="Gather feedback on implementation progress",
    question_categories=[
        "Feature acceptance",
        "Bug reports and issues",
        "Change requests",
        "Testing feedback",
    ],
    document_strategy="Track changes and gather testing evidence",
    document_priorities=[
        "test_reports",
        "bug_reports",
        "change_requests",
        "user_feedback",
    ],
    agenda_sections=[
        "Progress Update",
        "Demo of Completed Features",
        "Feedback Review",
        "Upcoming Sprint",
        "Blockers & Risks",
    ],
    typical_duration=30,
    question_temperature=0.3,
)

# Delivery: Final handoff
DELIVERY_CONFIG = PrepStageConfig(
    phase=CollaborationPhase.DELIVERY,
    question_goal="Ensure smooth handoff and gather final feedback",
    question_categories=[
        "Documentation completeness",
        "Training needs",
        "Support expectations",
        "Future roadmap",
    ],
    document_strategy="Provide comprehensive handoff documentation",
    document_priorities=[
        "user_guides",
        "technical_docs",
        "admin_guides",
        "support_info",
    ],
    agenda_sections=[
        "Final Demo",
        "Documentation Review",
        "Training Walkthrough",
        "Support Handoff",
        "Future Opportunities",
    ],
    typical_duration=60,
    question_temperature=0.2,
)

# Main configuration map
PREP_CONFIG: dict[CollaborationPhase, PrepStageConfig] = {
    CollaborationPhase.PRE_DISCOVERY: PRE_DISCOVERY_CONFIG,
    CollaborationPhase.DISCOVERY: DISCOVERY_CONFIG,
    CollaborationPhase.VALIDATION: VALIDATION_CONFIG,
    CollaborationPhase.PROTOTYPE: PROTOTYPE_CONFIG,
    CollaborationPhase.PROPOSAL: PROPOSAL_CONFIG,
    CollaborationPhase.BUILD: BUILD_CONFIG,
    CollaborationPhase.DELIVERY: DELIVERY_CONFIG,
}


def get_prep_config(phase: CollaborationPhase) -> PrepStageConfig:
    """Get prep configuration for a specific phase.

    Args:
        phase: The collaboration phase

    Returns:
        PrepStageConfig for the phase, defaults to PRE_DISCOVERY if not found
    """
    return PREP_CONFIG.get(phase, PRE_DISCOVERY_CONFIG)
