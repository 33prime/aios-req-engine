"""Page-context tool filtering for consolidated chat tools.

6 tools total. 4 always available, 2 conditional on page context.
"""

from typing import Any

from .definitions import get_tool_definitions

# Tools sent on every request regardless of page (4 core)
CORE_TOOLS = {
    "search",
    "write",
    "process",
    "suggest_actions",
}

# Additional tools per page context
PAGE_TOOLS: dict[str, set] = {
    "brd:solution-flow": {"solution_flow"},
    "collaborate": {"client_portal"},
}

# Tools that mutate project data — invalidate context frame cache after execution
_MUTATING_TOOLS = {
    "write",
    "process",
    "solution_flow",
    "client_portal",
}


def get_tools_for_context(page_context: str | None = None) -> list[dict[str, Any]]:
    """Return filtered tool definitions based on current page context.

    Always returns 4-6 tools:
    - 4 core: search, write, process, suggest_actions
    - +solution_flow on solution-flow page
    - +client_portal on collaborate page or any brd: page
    - All 6 when no page context (sidebar chat)
    """
    all_tools = get_tool_definitions()

    if page_context is None:
        # No page context — include all 6 tools
        return all_tools

    # Core + page-specific
    page_extras = PAGE_TOOLS.get(page_context, set())

    # Any brd: page gets client_portal
    if page_context.startswith("brd"):
        page_extras = page_extras | {"client_portal"}

    allowed = CORE_TOOLS | page_extras

    return [t for t in all_tools if t["name"] in allowed]
