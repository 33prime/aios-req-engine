"""Token budget management for context window optimization.

Uses tiktoken for accurate token counting with Claude-compatible encoding.
"""

from typing import Any

import tiktoken


class TokenBudgetManager:
    """Manages token counting and truncation for context assembly."""

    TOTAL_BUDGET = 80_000
    RESPONSE_BUFFER = 4_096
    SAFETY_MARGIN = 3_000

    def __init__(self, total_budget: int | None = None):
        self.total_budget = total_budget or self.TOTAL_BUDGET
        self._encoder = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        if not text:
            return 0
        return len(self._encoder.encode(text))

    def count_tokens_dict(self, data: dict | list | Any) -> int:
        """Count tokens in serialized dict/list."""
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

    def truncate_text(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token limit."""
        if not text:
            return text

        tokens = self._encoder.encode(text)
        if len(tokens) <= max_tokens:
            return text

        truncated_tokens = tokens[: max_tokens - 1]
        truncated_text = self._encoder.decode(truncated_tokens)
        return truncated_text + "..."


# Singleton instance
_budget_manager: TokenBudgetManager | None = None


def get_budget_manager() -> TokenBudgetManager:
    """Get or create singleton TokenBudgetManager."""
    global _budget_manager
    if _budget_manager is None:
        _budget_manager = TokenBudgetManager()
    return _budget_manager
