"""Project creation chat prompts and conversation logic.

Uses Claude Haiku 3.5 for fast, intelligent project creation conversations.
"""

import re
from typing import TypedDict

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConversationState(TypedDict):
    """State extracted from conversation."""

    project_name: str | None
    problem: str | None
    users: str | None
    features: str | None
    org_fit: str | None
    has_client_info: bool
    client_info: str | None
    ready_to_create: bool
    summary_ready: bool


PROJECT_CREATION_SYSTEM_PROMPT = """You are helping a consultant create a new project. Be friendly, warm, and guide them through a structured conversation.

## Conversation Flow

Collect exactly 5 things in this order:

1. **Project Name** - Ask what they want to call the project
2. **Problem Statement** - Ask what problem they're trying to solve
3. **Target Users** - Ask who the primary users/beneficiaries are
4. **Key Features** - Ask about 2-4 core features or capabilities
5. **Organizational Fit** - Ask how this fits into the organization (why now, what it replaces, strategic context)

After collecting all 5, provide a concise summary and signal ready.

## Response Guidelines

- Use **bold** for emphasis and key terms
- Keep each response to 2-3 sentences max
- Be conversational and encouraging
- Personalize follow-up questions based on their answers
- When summarizing, use bullet points for clarity

## Internal Markers (REQUIRED - always include at end of response)

After each response, include ONE of these markers on a new line:
- `[[STEP:name]]` - After greeting, waiting for project name
- `[[STEP:problem|NAME:<project name>]]` - Have name, waiting for problem
- `[[STEP:users|NAME:<name>|PROBLEM:<brief summary>]]` - Have problem, waiting for users
- `[[STEP:features|NAME:<name>|USERS:<brief summary>]]` - Have users, waiting for features
- `[[STEP:org_fit|NAME:<name>]]` - Have features, waiting for org fit
- `[[SUMMARY_READY|NAME:<name>|PROBLEM:<problem>|USERS:<users>|FEATURES:<features>|ORG_FIT:<org_fit>]]` - All 5 collected

## Example Conversation

User: (opens chat)
You: Hi! I'm here to help you set up your new project. **What would you like to call it?**
[[STEP:name]]

User: Auto Intelligence App
You: Great name! **What problem is Auto Intelligence App trying to solve?**
[[STEP:problem|NAME:Auto Intelligence App]]

User: Helping car dealerships manage their inventory more efficiently
You: Got it - inventory management for car dealerships. **Who are the primary users** that will benefit from this solution?
[[STEP:users|NAME:Auto Intelligence App|PROBLEM:inventory management for car dealerships]]

User: Dealership managers and sales staff
You: Perfect! So we're building for:
- **Dealership managers** - likely need oversight and reporting
- **Sales staff** - need quick access to inventory info

**What are 2-4 core features** you're envisioning for Auto Intelligence App?
[[STEP:features|NAME:Auto Intelligence App|USERS:dealership managers and sales staff]]

User: Real-time inventory tracking, automated pricing suggestions, and a mobile app for sales staff
You: Those are solid features. Last question — **how does this fit into the organization?** What are they using today, and why is now the right time to build this?
[[STEP:org_fit|NAME:Auto Intelligence App]]

User: They're using spreadsheets and it's becoming unmanageable as they expand to 5 locations
You: Here's a summary of everything:

**Auto Intelligence App**
- **Problem:** Efficient inventory management for car dealerships
- **Users:** Dealership managers & sales staff
- **Features:** Real-time inventory tracking, automated pricing, mobile app
- **Context:** Replacing spreadsheets as they scale to 5 locations
[[SUMMARY_READY|NAME:Auto Intelligence App|PROBLEM:Efficient inventory management for car dealerships|USERS:Dealership managers and sales staff|FEATURES:Real-time inventory tracking, automated pricing suggestions, mobile app for sales staff|ORG_FIT:Replacing spreadsheets as they scale to 5 locations]]

## Important

- ALWAYS include the marker at the end of EVERY response
- Keep summaries brief in markers (under 100 chars each)
- The chat does NOT create the project — it collects info and signals summary_ready
- After the summary, stop — the frontend handles the next steps (client card, stakeholder card, launch)"""


def get_initial_greeting() -> str:
    """Get the initial AI greeting message."""
    return "Hi! I'm here to help you set up your new project. **What would you like to call it?**"


def parse_conversation_state(messages: list[dict], last_response: str) -> ConversationState:
    """
    Parse conversation to extract project creation state.

    Args:
        messages: List of conversation messages (role, content)
        last_response: The assistant's most recent response

    Returns:
        ConversationState with extracted information
    """
    state: ConversationState = {
        "project_name": None,
        "problem": None,
        "users": None,
        "features": None,
        "org_fit": None,
        "has_client_info": False,
        "client_info": None,
        "ready_to_create": False,
        "summary_ready": False,
    }

    # Check for [[SUMMARY_READY|NAME:...|PROBLEM:...|USERS:...|FEATURES:...|ORG_FIT:...]] marker
    summary_match = re.search(
        r"\[\[SUMMARY_READY\|NAME:([^|]+)\|PROBLEM:([^|]+)\|USERS:([^|]+)\|FEATURES:([^|]+)\|ORG_FIT:([^\]]+)\]\]",
        last_response,
    )
    if summary_match:
        state["project_name"] = summary_match.group(1).strip()
        state["problem"] = summary_match.group(2).strip()
        state["users"] = summary_match.group(3).strip()
        state["features"] = summary_match.group(4).strip()
        state["org_fit"] = summary_match.group(5).strip()
        state["summary_ready"] = True
        return state

    # Legacy support: check for [[READY_TO_CREATE|NAME:<name>|DESCRIPTION:<desc>]] marker
    ready_match = re.search(
        r"\[\[READY_TO_CREATE\|NAME:([^|]+)\|DESCRIPTION:([^\]]+)\]\]",
        last_response,
    )
    if ready_match:
        state["project_name"] = ready_match.group(1).strip()
        state["client_info"] = ready_match.group(2).strip()
        state["has_client_info"] = True
        state["ready_to_create"] = True
        return state

    # Check for other step markers to extract name
    name_match = re.search(r"\[\[STEP:[^|]+\|NAME:([^|\]]+)", last_response)
    if name_match:
        state["project_name"] = name_match.group(1).strip()

    return state


def strip_markers_from_response(response: str) -> str:
    """
    Remove internal markers from the response before showing to user.

    Handles both complete markers (with closing ]]) and incomplete markers
    that are still being streamed (starting with [[ but no closing yet).

    Args:
        response: Raw response with markers

    Returns:
        Clean response for display
    """
    # Remove complete [[STEP:...]] markers
    cleaned = re.sub(r"\s*\[\[STEP:.*?\]\]", "", response, flags=re.DOTALL)
    # Remove complete [[READY_TO_CREATE|...]] markers
    cleaned = re.sub(r"\s*\[\[READY_TO_CREATE.*?\]\]", "", cleaned, flags=re.DOTALL)
    # Remove any other complete double-bracket markers
    cleaned = re.sub(r"\s*\[\[.*?\]\]", "", cleaned, flags=re.DOTALL)
    # Remove old style markers just in case
    cleaned = re.sub(r"\s*\[HAS_NAME:.*?\]", "", cleaned)
    cleaned = re.sub(r"\s*\[READY_TO_CREATE\]", "", cleaned)

    # Remove complete [[SUMMARY_READY|...]] markers
    cleaned = re.sub(r"\s*\[\[SUMMARY_READY.*?\]\]", "", cleaned, flags=re.DOTALL)

    # CRITICAL: Remove incomplete markers that are still being streamed
    # This catches [[STEP:... or [[READY_TO_CREATE... or [[SUMMARY_READY... without closing ]]
    # The marker starts with [[ and goes to end of string
    cleaned = re.sub(r"\s*\[\[(?:STEP|READY_TO_CREATE|SUMMARY_READY)[^\]]*$", "", cleaned)

    # Even more aggressive: remove any [[ followed by anything to end of string
    # This catches any incomplete double-bracket marker
    cleaned = re.sub(r"\s*\[\[[^\]]*$", "", cleaned)

    return cleaned.strip()
