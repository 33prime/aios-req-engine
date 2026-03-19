"""Sub-assistant profiles — page-specific tool, retrieval, and intelligence gating.

Each ChatMode defines the optimal configuration for a workspace page.
Replaces ad-hoc gating with a single, clean configuration per page.
"""

from dataclasses import dataclass, field


@dataclass
class ChatMode:
    """Configuration profile for a specific workspace page."""

    name: str
    tools: list[str] = field(default_factory=list)
    retrieval_strategy: str = "light"  # "none" | "light" | "full"
    load_forge: bool = False
    load_horizon: bool = False
    load_confidence: bool = False
    load_warm_memory: bool = True
    max_tokens: int = 1500
    thinking_eligible: bool = False
    primary_entity_type: str | None = None


# ── Mode Definitions ──────────────────────────────────────────────

_MODES: dict[str, ChatMode] = {
    "brd:features": ChatMode(
        name="brd",
        tools=["search", "write", "process", "suggest_actions", "client_portal"],
        retrieval_strategy="light",
        load_confidence=True,
        load_forge=True,
        max_tokens=1500,
        primary_entity_type="feature",
    ),
    "brd:personas": ChatMode(
        name="brd",
        tools=["search", "write", "process", "suggest_actions", "client_portal"],
        retrieval_strategy="light",
        load_confidence=True,
        max_tokens=1500,
        primary_entity_type="persona",
    ),
    "brd:workflows": ChatMode(
        name="brd",
        tools=["search", "write", "process", "suggest_actions", "client_portal"],
        retrieval_strategy="light",
        load_confidence=True,
        max_tokens=1500,
        primary_entity_type="workflow",
    ),
    "brd:stakeholders": ChatMode(
        name="brd",
        tools=["search", "write", "process", "suggest_actions", "client_portal"],
        retrieval_strategy="light",
        load_confidence=True,
        max_tokens=1500,
        primary_entity_type="stakeholder",
    ),
    "brd:constraints": ChatMode(
        name="brd",
        tools=["search", "write", "process", "suggest_actions", "client_portal"],
        retrieval_strategy="light",
        load_confidence=True,
        max_tokens=1500,
        primary_entity_type="constraint",
    ),
    "brd:business-drivers": ChatMode(
        name="brd",
        tools=["search", "write", "process", "suggest_actions", "client_portal"],
        retrieval_strategy="light",
        load_confidence=True,
        max_tokens=1500,
        primary_entity_type="business_driver",
    ),
    "brd:data-entities": ChatMode(
        name="brd",
        tools=["search", "write", "process", "suggest_actions", "client_portal"],
        retrieval_strategy="light",
        load_confidence=True,
        max_tokens=1500,
        primary_entity_type="data_entity",
    ),
    "brd:unlocks": ChatMode(
        name="brd",
        tools=["search", "write", "process", "suggest_actions", "client_portal"],
        retrieval_strategy="light",
        load_confidence=True,
        load_forge=True,
        max_tokens=1500,
        primary_entity_type="unlock",
    ),
    "brd:solution-flow": ChatMode(
        name="solution_flow",
        tools=["search", "write", "solution_flow", "suggest_actions"],
        retrieval_strategy="light",
        load_horizon=True,
        load_confidence=True,
        max_tokens=1500,
        thinking_eligible=True,
        primary_entity_type="solution_flow_step",
    ),
    "data-ai": ChatMode(
        name="data_ai",
        tools=["suggest_actions"],
        retrieval_strategy="none",
        max_tokens=1200,
    ),
    "build": ChatMode(
        name="build",
        tools=["process", "suggest_actions"],
        retrieval_strategy="light",
        load_forge=True,
        max_tokens=1200,
    ),
    "collaborate": ChatMode(
        name="collaborate",
        tools=["write", "client_portal", "suggest_actions"],
        retrieval_strategy="light",
        load_confidence=True,
        max_tokens=1500,
        primary_entity_type="stakeholder",
    ),
    "overview": ChatMode(
        name="overview",
        tools=["suggest_actions"],
        retrieval_strategy="none",
        max_tokens=1000,
    ),
}

# Default mode for unknown pages
_DEFAULT_MODE = ChatMode(
    name="default",
    tools=["search", "write", "process", "solution_flow", "client_portal", "suggest_actions"],
    retrieval_strategy="light",
    load_confidence=True,
    max_tokens=1500,
)


def get_chat_mode(page_context: str | None) -> ChatMode:
    """Get the ChatMode profile for a page context."""
    if not page_context:
        return _DEFAULT_MODE
    return _MODES.get(page_context, _DEFAULT_MODE)
