"""Tool result truncation for context window optimization.

Truncates large tool results to fit within token budgets while
preserving the most relevant information for each tool type.
"""

import json
from typing import Any

from app.context.token_budget import TokenBudgetManager, get_budget_manager
from app.core.logging import get_logger

logger = get_logger(__name__)


# Per-tool configuration
TOOL_CONFIGS: dict[str, dict] = {
    "list_insights": {
        "max_tokens": 2000,
        "max_items": 10,
        "list_field": "insights",
        "truncate_fields": ["finding", "why"],
        "truncate_length": 200,
    },
    "search": {
        "max_tokens": 2500,
        "max_items": 10,
        "list_field": "results",
        "truncate_fields": ["content", "excerpt"],
        "truncate_length": 300,
    },
    "get_project_status": {
        "max_tokens": 1000,
        "max_items": None,  # No list truncation
        "list_field": None,
    },
    "assess_readiness": {
        "max_tokens": 1500,
        "max_items": 5,
        "list_field": "blockers",  # Also truncate warnings, recommendations
        "truncate_fields": [],
    },
    "suggest_actions": {
        "max_tokens": 3000,
        "max_items": 8,
        "list_field": "cards",
        "truncate_fields": ["body", "quote", "resolution"],
        "truncate_length": 500,
    },
}

DEFAULT_CONFIG = {
    "max_tokens": 5000,
    "max_items": 20,
    "list_field": None,
    "truncate_fields": [],
    "truncate_length": 200,
}


def truncate_tool_result(
    tool_name: str,
    result: dict | list | Any,
    max_tokens: int | None = None,
) -> dict:
    """
    Truncate a tool result to fit within token budget.

    Args:
        tool_name: Name of the tool
        result: Raw tool result
        max_tokens: Override max tokens (uses per-tool config if None)

    Returns:
        Truncated result dict with optional metadata about truncation
    """
    if result is None:
        return {"result": None}

    # Get config for this tool
    config = TOOL_CONFIGS.get(tool_name, DEFAULT_CONFIG)
    token_limit = max_tokens or config["max_tokens"]

    budget_manager = get_budget_manager()

    # Handle non-dict results
    if not isinstance(result, dict):
        if isinstance(result, list):
            result = {"items": result}
        else:
            result = {"result": result}

    # Check current size
    current_tokens = budget_manager.count_tokens_dict(result)
    if current_tokens <= token_limit:
        return result

    # Apply truncation strategies
    truncated = _truncate_result(result, config, budget_manager, token_limit)

    # Add truncation metadata
    new_tokens = budget_manager.count_tokens_dict(truncated)
    if new_tokens < current_tokens:
        truncated["_truncated"] = True
        truncated["_original_tokens"] = current_tokens
        truncated["_truncated_tokens"] = new_tokens

    return truncated


def _truncate_result(
    result: dict,
    config: dict,
    budget_manager: TokenBudgetManager,
    token_limit: int,
) -> dict:
    """Apply truncation strategies to a result dict."""
    truncated = result.copy()

    # Strategy 1: Truncate list items
    list_field = config.get("list_field")
    max_items = config.get("max_items")

    if list_field and list_field in truncated and isinstance(truncated[list_field], list):
        items = truncated[list_field]
        if max_items and len(items) > max_items:
            truncated[list_field] = items[:max_items]
            truncated[f"_{list_field}_total"] = len(items)
            truncated[f"_{list_field}_shown"] = max_items

    # Handle multiple gap list fields
    gap_fields = config.get("gap_list_fields", [])
    for field in gap_fields:
        if field in truncated and isinstance(truncated[field], dict):
            gap_data = truncated[field]
            if "items" in gap_data and isinstance(gap_data["items"], list):
                items = gap_data["items"]
                if max_items and len(items) > max_items:
                    gap_data["items"] = items[:max_items]
                    gap_data["_total"] = len(items)

    # Strategy 2: Truncate text fields within items
    truncate_fields = config.get("truncate_fields", [])
    truncate_length = config.get("truncate_length", 200)

    if list_field and list_field in truncated:
        items = truncated[list_field]
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    for field in truncate_fields:
                        if field in item and isinstance(item[field], str):
                            if len(item[field]) > truncate_length:
                                item[field] = item[field][:truncate_length] + "..."

    # Strategy 3: Truncate other known large fields
    for field in ["blockers", "warnings", "recommendations"]:
        if field in truncated and isinstance(truncated[field], list):
            max_field_items = config.get("max_items", 5)
            if len(truncated[field]) > max_field_items:
                truncated[field] = truncated[field][:max_field_items]
                truncated[f"_{field}_total"] = len(result.get(field, []))

    # Check if still over limit
    current_tokens = budget_manager.count_tokens_dict(truncated)
    if current_tokens > token_limit:
        # Aggressive truncation: reduce items further
        truncated = _aggressive_truncate(truncated, budget_manager, token_limit)

    return truncated


def _aggressive_truncate(
    result: dict,
    budget_manager: TokenBudgetManager,
    token_limit: int,
) -> dict:
    """Aggressively truncate when still over budget."""
    truncated = result.copy()

    # Find and reduce all lists
    for key, value in list(truncated.items()):
        if isinstance(value, list) and len(value) > 3:
            truncated[key] = value[:3]
            truncated[f"_{key}_truncated_to"] = 3

        if isinstance(value, dict):
            # Recursively check nested dicts
            for nested_key, nested_value in list(value.items()):
                if isinstance(nested_value, list) and len(nested_value) > 3:
                    value[nested_key] = nested_value[:3]

    # Check again
    current_tokens = budget_manager.count_tokens_dict(truncated)
    if current_tokens > token_limit:
        # Last resort: truncate the entire result as JSON
        result_json = json.dumps(truncated, default=str)
        truncated_json = budget_manager.truncate_text(result_json, token_limit - 100)
        try:
            # Try to parse back (may fail if truncated mid-structure)
            truncated = json.loads(truncated_json)
        except json.JSONDecodeError:
            # Return a summary instead
            truncated = {
                "_error": "Result too large, truncated",
                "_original_tokens": budget_manager.count_tokens(result_json),
                "_token_limit": token_limit,
            }

    return truncated


def estimate_result_size(tool_name: str, result: dict) -> dict:
    """
    Estimate the token size of a tool result.

    Args:
        tool_name: Name of the tool
        result: Tool result dict

    Returns:
        Dict with token count and whether truncation is needed
    """
    config = TOOL_CONFIGS.get(tool_name, DEFAULT_CONFIG)
    budget_manager = get_budget_manager()

    current_tokens = budget_manager.count_tokens_dict(result)
    max_tokens = config["max_tokens"]

    return {
        "tool_name": tool_name,
        "current_tokens": current_tokens,
        "max_tokens": max_tokens,
        "needs_truncation": current_tokens > max_tokens,
        "excess_tokens": max(0, current_tokens - max_tokens),
    }


def get_tool_token_cap(tool_name: str) -> int:
    """Get the token cap for a specific tool."""
    config = TOOL_CONFIGS.get(tool_name, DEFAULT_CONFIG)
    return config["max_tokens"]
