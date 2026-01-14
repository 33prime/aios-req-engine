"""Pydantic models for context management."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ProjectPhase(str, Enum):
    """Project lifecycle phases with clear progression."""

    DISCOVERY = "discovery"
    DEFINITION = "definition"
    VALIDATION = "validation"
    BUILD_READY = "build_ready"

    @property
    def display_name(self) -> str:
        """Human-readable phase name."""
        return {
            self.DISCOVERY: "Discovery",
            self.DEFINITION: "Definition",
            self.VALIDATION: "Validation",
            self.BUILD_READY: "Build-Ready",
        }[self]

    @property
    def goal(self) -> str:
        """Phase goal description."""
        return {
            self.DISCOVERY: "Understand the problem space and gather initial requirements",
            self.DEFINITION: "Build out comprehensive baseline PRD",
            self.VALIDATION: "Validate and refine through research and confirmations",
            self.BUILD_READY: "Final preparation for handoff to development",
        }[self]


class Blocker(BaseModel):
    """A blocking issue preventing phase progression."""

    type: str = Field(..., description="Blocker type identifier")
    message: str = Field(..., description="Human-readable description")
    severity: str = Field(..., description="critical or important")
    action_hint: str | None = Field(
        default=None, description="Suggested action to resolve"
    )


class NextAction(BaseModel):
    """A recommended next action to advance the project."""

    action: str = Field(..., description="Imperative action description")
    tool_hint: str | None = Field(
        default=None, description="Suggested tool to use"
    )
    priority: int = Field(..., ge=1, le=5, description="Priority 1-5 (1=highest)")
    rationale: str | None = Field(
        default=None, description="Why this action matters now"
    )


class PhaseCriteria(BaseModel):
    """Status of exit criteria for a phase."""

    name: str = Field(..., description="Criterion name")
    met: bool = Field(..., description="Whether criterion is satisfied")
    current_value: Any = Field(default=None, description="Current value")
    required_value: Any = Field(default=None, description="Required value to pass")


class ProjectStateFrame(BaseModel):
    """
    Structured representation of project state for context injection.

    This is the core "mental model" given to the LLM so it always knows:
    - Where the project WAS (milestones)
    - Where it IS (phase, progress, counts)
    - What's NEXT (blockers, actions)

    Target: ~800 tokens when serialized to XML.
    """

    # Phase information
    current_phase: ProjectPhase = Field(..., description="Current project phase")
    phase_progress: float = Field(
        ..., ge=0.0, le=1.0, description="Progress within current phase"
    )
    phase_goal: str = Field(..., description="Goal of current phase")
    exit_criteria: list[PhaseCriteria] = Field(
        default_factory=list, description="Status of phase exit criteria"
    )

    # Quantitative state
    counts: dict[str, int] = Field(
        default_factory=dict,
        description="Entity counts (features, personas, vp_steps, etc.)",
    )
    scores: dict[str, float] = Field(
        default_factory=dict,
        description="Score values (baseline_score, readiness_score)",
    )

    # Milestones
    completed_milestones: list[str] = Field(
        default_factory=list, description="Completed milestone names"
    )
    pending_milestones: list[str] = Field(
        default_factory=list, description="Pending milestone names"
    )

    # Blockers and next actions
    blockers: list[Blocker] = Field(
        default_factory=list, max_length=3, description="Top blocking issues"
    )
    next_actions: list[NextAction] = Field(
        default_factory=list, max_length=5, description="Recommended next actions"
    )

    # Metadata
    computed_at: datetime = Field(
        default_factory=datetime.utcnow, description="When state was computed"
    )

    def to_xml(self) -> str:
        """Serialize state frame to compact XML format for prompt injection."""
        lines = ['<project_state_frame>']

        # Phase section
        criteria_met = sum(1 for c in self.exit_criteria if c.met)
        criteria_total = len(self.exit_criteria)
        lines.append(
            f'  <phase current="{self.current_phase.value}" '
            f'progress="{self.phase_progress:.0%}">'
        )
        lines.append(f'    <goal>{self.phase_goal}</goal>')
        lines.append(f'    <criteria met="{criteria_met}" total="{criteria_total}"/>')
        lines.append('  </phase>')

        # Counts section
        lines.append('  <counts>')
        if "features" in self.counts:
            mvp = self.counts.get("mvp_features", 0)
            confirmed = self.counts.get("confirmed_features", 0)
            lines.append(
                f'    <features total="{self.counts["features"]}" '
                f'mvp="{mvp}" confirmed="{confirmed}"/>'
            )
        if "personas" in self.counts:
            lines.append(f'    <personas count="{self.counts["personas"]}"/>')
        if "vp_steps" in self.counts:
            lines.append(f'    <vp_steps count="{self.counts["vp_steps"]}"/>')
        if "prd_sections" in self.counts:
            filled = self.counts.get("prd_sections_filled", 0)
            lines.append(
                f'    <prd_sections total="{self.counts["prd_sections"]}" '
                f'filled="{filled}"/>'
            )
        if "insights" in self.counts:
            critical = self.counts.get("insights_critical", 0)
            lines.append(
                f'    <insights open="{self.counts["insights"]}" '
                f'critical="{critical}"/>'
            )
        lines.append('  </counts>')

        # Scores section
        if self.scores:
            score_attrs = " ".join(
                f'{k}="{v:.2f}"' for k, v in self.scores.items()
            )
            lines.append(f'  <scores {score_attrs}/>')

        # Milestones (compact)
        if self.completed_milestones:
            lines.append(
                f'  <milestones completed="{",".join(self.completed_milestones)}"/>'
            )

        # Blockers
        if self.blockers:
            lines.append('  <blockers>')
            for blocker in self.blockers:
                lines.append(
                    f'    <blocker type="{blocker.type}" severity="{blocker.severity}">'
                )
                lines.append(f'      {blocker.message}')
                lines.append('    </blocker>')
            lines.append('  </blockers>')

        # Next actions
        if self.next_actions:
            lines.append('  <next_actions>')
            for action in self.next_actions:
                tool_attr = f' tool="{action.tool_hint}"' if action.tool_hint else ""
                lines.append(
                    f'    <action priority="{action.priority}"{tool_attr}>'
                    f'{action.action}</action>'
                )
            lines.append('  </next_actions>')

        lines.append('</project_state_frame>')
        return "\n".join(lines)


class ChatMessage(BaseModel):
    """A message in conversation history."""

    role: str = Field(..., description="user, assistant, or system")
    content: str = Field(..., description="Message content")
    tool_calls: list[dict] | None = Field(
        default=None, description="Tool calls if any"
    )


class CompressedHistory(BaseModel):
    """Compressed conversation history with summary and recent messages."""

    summary: str | None = Field(
        default=None, description="Summary of older messages"
    )
    recent_messages: list[ChatMessage] = Field(
        default_factory=list, description="Recent messages kept verbatim"
    )
    total_messages_summarized: int = Field(
        default=0, description="Count of messages in summary"
    )

    def to_messages(self) -> list[dict[str, str]]:
        """Convert to message list for API call."""
        messages = []

        if self.summary:
            messages.append({
                "role": "user",
                "content": f"[Previous conversation summary: {self.summary}]",
            })

        for msg in self.recent_messages:
            messages.append({"role": msg.role, "content": msg.content})

        return messages


class IntentClassification(BaseModel):
    """Result of intent classification."""

    primary: str = Field(..., description="Primary intent category")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Classification confidence"
    )
    entity_focus: str | None = Field(
        default=None, description="Focused entity type if detected"
    )
    batch_likely: bool = Field(
        default=False, description="Whether batch operation is expected"
    )
    secondary_intents: list[str] = Field(
        default_factory=list, description="Secondary intent categories"
    )


class TokenAllocation(BaseModel):
    """Token budget allocation result."""

    component: str = Field(..., description="Component name")
    requested: int = Field(..., description="Tokens requested")
    allocated: int = Field(..., description="Tokens actually allocated")
    truncated: bool = Field(default=False, description="Whether truncation occurred")


class TokenBudgetResult(BaseModel):
    """Result of token budget allocation."""

    allocations: list[TokenAllocation] = Field(default_factory=list)
    total_used: int = Field(default=0)
    total_budget: int = Field(default=80000)
    remaining: int = Field(default=0)
    within_budget: bool = Field(default=True)
