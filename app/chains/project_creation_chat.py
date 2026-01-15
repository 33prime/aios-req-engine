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
    has_client_info: bool
    client_info: str | None
    ready_to_create: bool


PROJECT_CREATION_SYSTEM_PROMPT = """You are helping a consultant create a new project. Be friendly, warm, and guide them through a structured conversation.

## Conversation Flow

Follow this exact sequence:

1. **Project Name** - Ask what they want to call the project
2. **Problem Statement** - Ask what problem they're trying to solve
3. **Summary + Users Question** - Briefly summarize what you've heard, then ask who the primary users/beneficiaries are
4. **Summary + Features Question** - Summarize the users, then ask about 2-4 core features they're envisioning
5. **Final Summary** - Provide a nice summary of everything gathered
6. **Client Info Question** - In a NEW message, ask about client details (client name, website, why they want to build this now)
7. **Create Project** - After they respond about client info, signal ready to create

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
- `[[STEP:client_info|NAME:<name>]]` - After summary, waiting for client info response
- `[[READY_TO_CREATE|NAME:<name>|DESCRIPTION:<full context>]]` - Ready to create project

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
You: Excellent! Here's what we have so far:

**Auto Intelligence App**
- **Problem:** Efficient inventory management for car dealerships
- **Users:** Dealership managers & sales staff
- **Core Features:**
  • Real-time inventory tracking
  • Automated pricing suggestions
  • Mobile app for sales staff

Now for some quick client details - **what's the client's name, their website (if any), and why do they want to build this now?**
[[STEP:client_info|NAME:Auto Intelligence App]]

User: Acme Motors, acmemotors.com, they're losing sales due to inventory visibility issues
You: Perfect! Creating your project now with all that context.
[[READY_TO_CREATE|NAME:Auto Intelligence App|DESCRIPTION:Inventory management solution for car dealerships. Client: Acme Motors (acmemotors.com). Users: dealership managers and sales staff. Features: real-time inventory tracking, automated pricing suggestions, mobile app for sales staff. Motivation: losing sales due to inventory visibility issues.]]

User: No, I don't have that info yet
You: No problem! I'll create your project with what we have. You can always add client details later.
[[READY_TO_CREATE|NAME:Auto Intelligence App|DESCRIPTION:Inventory management solution for car dealerships. Users: dealership managers and sales staff. Features: real-time inventory tracking, automated pricing suggestions, mobile app for sales staff.]]

## Important

- ALWAYS include the marker at the end of EVERY response
- Keep summaries brief in markers (under 100 chars each)
- The DESCRIPTION in READY_TO_CREATE should capture all key info gathered
- The client info question should be AFTER the summary, asking for: client name, website, and why now"""


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
        "has_client_info": False,
        "client_info": None,
        "ready_to_create": False,
    }

    # Check for [[READY_TO_CREATE|NAME:<name>|DESCRIPTION:<desc>]] marker
    ready_match = re.search(
        r"\[\[READY_TO_CREATE\|NAME:([^|]+)\|DESCRIPTION:([^\]]+)\]\]",
        last_response
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

    # Look for client information in the last user message if we're at client_info step
    if "[[STEP:client_info" in last_response or "STEP:client_info" in str(messages):
        # The next user response after client_info step is the client info
        pass

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

    # CRITICAL: Remove incomplete markers that are still being streamed
    # This catches [[STEP:... or [[READY_TO_CREATE... without closing ]]
    # The marker starts with [[ and goes to end of string
    cleaned = re.sub(r"\s*\[\[(?:STEP|READY_TO_CREATE)[^\]]*$", "", cleaned)

    # Even more aggressive: remove any [[ followed by anything to end of string
    # This catches any incomplete double-bracket marker
    cleaned = re.sub(r"\s*\[\[[^\]]*$", "", cleaned)

    return cleaned.strip()
