"""Token budget management for context window optimization.

Uses tiktoken for accurate token counting with Claude-compatible encoding.
Manages allocation across system prompt, conversation history, and tool results.
"""

from dataclasses import dataclass
from typing import Any

import tiktoken

from app.context.models import TokenAllocation, TokenBudgetResult


@dataclass
class ComponentBudget:
    """Budget configuration for a context component."""

    min_tokens: int
    target_tokens: int
    max_tokens: int
    priority: int  # Lower = higher priority (allocated first)


class TokenBudgetManager:
    """
    Manages token allocation across context components.

    Budget allocation strategy:
    1. Reserve fixed allocations (response buffer, safety margin)
    2. Allocate to high-priority components first
    3. Distribute remaining tokens to lower-priority components
    4. Truncate components that exceed their max allocation
    """

    # Total context budget
    TOTAL_BUDGET = 80_000
    RESPONSE_BUFFER = 4_096
    SAFETY_MARGIN = 3_000

    # Component budgets (priority: lower = allocate first)
    COMPONENT_BUDGETS: dict[str, ComponentBudget] = {
        "system_prompt_base": ComponentBudget(
            min_tokens=1_500, target_tokens=2_000, max_tokens=2_500, priority=1
        ),
        "state_frame": ComponentBudget(
            min_tokens=500, target_tokens=800, max_tokens=1_000, priority=2
        ),
        "phase_instructions": ComponentBudget(
            min_tokens=300, target_tokens=500, max_tokens=800, priority=3
        ),
        "tool_definitions": ComponentBudget(
            min_tokens=800, target_tokens=1_200, max_tokens=1_500, priority=4
        ),
        "conversation_summary": ComponentBudget(
            min_tokens=500, target_tokens=1_000, max_tokens=2_000, priority=5
        ),
        "recent_messages": ComponentBudget(
            min_tokens=3_000, target_tokens=10_000, max_tokens=15_000, priority=6
        ),
        "tool_results": ComponentBudget(
            min_tokens=0, target_tokens=5_000, max_tokens=10_000, priority=7
        ),
    }

    # Per-tool result size caps
    TOOL_RESULT_CAPS: dict[str, int] = {
        "list_insights": 2_000,
        "search_research": 1_500,
        "get_project_status": 1_000,
        "assess_readiness": 1_500,
        "analyze_gaps": 2_000,
        "semantic_search_research": 2_500,
        "propose_features": 2_000,
        "preview_proposal": 3_000,
        "find_evidence_gaps": 2_000,
        "_default": 5_000,
    }

    def __init__(self, total_budget: int | None = None):
        """Initialize budget manager.

        Args:
            total_budget: Override total budget (default 80K)
        """
        self.total_budget = total_budget or self.TOTAL_BUDGET
        # Use cl100k_base encoding (closest to Claude's tokenizer)
        self._encoder = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken.

        Args:
            text: Text to count tokens for

        Returns:
            Token count
        """
        if not text:
            return 0
        return len(self._encoder.encode(text))

    def count_tokens_dict(self, data: dict | list | Any) -> int:
        """Count tokens in serialized dict/list.

        Args:
            data: Data structure to serialize and count

        Returns:
            Token count for JSON serialization
        """
        import json

        if data is None:
            return 0
        try:
            text = json.dumps(data, default=str)
            return self.count_tokens(text)
        except (TypeError, ValueError):
            return 0

    def get_available_budget(self) -> int:
        """Get available tokens after reserving response buffer and margin."""
        return self.total_budget - self.RESPONSE_BUFFER - self.SAFETY_MARGIN

    def get_tool_result_cap(self, tool_name: str) -> int:
        """Get max tokens for a specific tool's result.

        Args:
            tool_name: Name of the tool

        Returns:
            Max token count for tool result
        """
        return self.TOOL_RESULT_CAPS.get(tool_name, self.TOOL_RESULT_CAPS["_default"])

    def allocate_budget(
        self, components: dict[str, str | dict]
    ) -> TokenBudgetResult:
        """
        Allocate tokens to components within budget constraints.

        Args:
            components: Dict mapping component names to content

        Returns:
            TokenBudgetResult with allocations and totals
        """
        available = self.get_available_budget()
        allocations: list[TokenAllocation] = []
        total_used = 0

        # Count tokens for each component
        component_tokens: dict[str, int] = {}
        for name, content in components.items():
            if isinstance(content, str):
                component_tokens[name] = self.count_tokens(content)
            else:
                component_tokens[name] = self.count_tokens_dict(content)

        # Sort components by priority
        sorted_components = sorted(
            components.keys(),
            key=lambda c: self.COMPONENT_BUDGETS.get(
                c, ComponentBudget(0, 5000, 10000, 99)
            ).priority,
        )

        # Allocate in priority order
        for name in sorted_components:
            tokens = component_tokens[name]
            budget = self.COMPONENT_BUDGETS.get(name)

            if budget:
                max_allowed = min(budget.max_tokens, available - total_used)
                allocated = min(tokens, max_allowed)
                truncated = tokens > allocated
            else:
                # No budget defined - use default cap
                max_allowed = min(5000, available - total_used)
                allocated = min(tokens, max_allowed)
                truncated = tokens > allocated

            allocations.append(
                TokenAllocation(
                    component=name,
                    requested=tokens,
                    allocated=allocated,
                    truncated=truncated,
                )
            )
            total_used += allocated

        return TokenBudgetResult(
            allocations=allocations,
            total_used=total_used,
            total_budget=self.total_budget,
            remaining=available - total_used,
            within_budget=total_used <= available,
        )

    def truncate_text(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token limit.

        Args:
            text: Text to truncate
            max_tokens: Maximum tokens allowed

        Returns:
            Truncated text (with ... suffix if truncated)
        """
        if not text:
            return text

        tokens = self._encoder.encode(text)
        if len(tokens) <= max_tokens:
            return text

        # Truncate and decode, leaving room for ellipsis
        truncated_tokens = tokens[: max_tokens - 1]
        truncated_text = self._encoder.decode(truncated_tokens)
        return truncated_text + "..."

    def truncate_list(
        self, items: list, max_items: int, max_tokens: int
    ) -> tuple[list, bool]:
        """Truncate a list to fit within item and token limits.

        Args:
            items: List of items to potentially truncate
            max_items: Maximum number of items
            max_tokens: Maximum total tokens for serialized list

        Returns:
            Tuple of (truncated list, was_truncated)
        """
        if len(items) <= max_items:
            result = items
        else:
            result = items[:max_items]
            was_truncated = True

        # Check token count
        import json

        current_tokens = self.count_tokens(json.dumps(result, default=str))
        if current_tokens <= max_tokens:
            return result, len(result) < len(items)

        # Need to reduce further
        while len(result) > 1 and current_tokens > max_tokens:
            result = result[:-1]
            current_tokens = self.count_tokens(json.dumps(result, default=str))

        return result, True

    def format_budget_report(self, result: TokenBudgetResult) -> str:
        """Format a human-readable budget report.

        Args:
            result: Budget allocation result

        Returns:
            Formatted report string
        """
        lines = ["Token Budget Report", "=" * 40]

        for alloc in result.allocations:
            status = " [TRUNCATED]" if alloc.truncated else ""
            lines.append(
                f"  {alloc.component}: {alloc.allocated:,} / {alloc.requested:,}{status}"
            )

        lines.append("-" * 40)
        lines.append(f"  Total Used: {result.total_used:,}")
        lines.append(f"  Budget: {result.total_budget:,}")
        lines.append(f"  Remaining: {result.remaining:,}")
        lines.append(f"  Within Budget: {result.within_budget}")

        return "\n".join(lines)


# Singleton instance for convenience
_budget_manager: TokenBudgetManager | None = None


def get_budget_manager() -> TokenBudgetManager:
    """Get or create singleton TokenBudgetManager."""
    global _budget_manager
    if _budget_manager is None:
        _budget_manager = TokenBudgetManager()
    return _budget_manager
