"""Deterministic TSX Cleanup — fix common TypeScript errors without LLM calls.

Runs regex-based passes to remove unused imports and unused state declarations
from generated page files. This runs BEFORE the Sonnet finisher agent, reducing
the number of issues the LLM needs to handle and saving tokens.

Covers ~70%+ of tsc --noEmit errors from Haiku-generated pages.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


# =============================================================================
# Pass 1 — Remove unused imports
# =============================================================================


def _remove_unused_imports(tsx: str) -> tuple[str, int]:
    """Remove imported symbols that aren't referenced in the file body.

    Handles:
      - Named imports: import { A, B, C } from '...'
      - Default imports: import X from '...'
      - Mixed: import X, { A, B } from '...'
      - Multiline named imports (braces spanning multiple lines)

    Returns (cleaned_source, number_of_symbols_removed).
    """
    lines = tsx.split("\n")
    fix_count = 0

    # First, collect all import blocks (may be multiline).
    # Each entry: (start_line_idx, end_line_idx, full_import_text)
    import_blocks: list[tuple[int, int, str]] = []

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip non-import lines
        if not stripped.startswith("import "):
            i += 1
            continue

        # Accumulate multiline imports (open brace without close on same line)
        start = i
        full_text = line
        while i < len(lines) - 1 and (
            # Brace opened but not closed on this accumulated text
            "{" in full_text and "}" not in full_text.split("{", 1)[1]
        ):
            i += 1
            full_text += "\n" + lines[i]

        import_blocks.append((start, i, full_text))
        i += 1

    if not import_blocks:
        return tsx, 0

    # Build the "body" — everything after the last import block
    last_import_end = import_blocks[-1][1]
    body_lines = lines[last_import_end + 1 :]
    body = "\n".join(body_lines)

    # Process each import block in reverse order so line indices stay valid
    for start_idx, end_idx, import_text in reversed(import_blocks):
        # Skip side-effect imports: import '...' or import "..."
        if re.match(r"^\s*import\s+['\"]", import_text):
            continue

        # Skip type-only imports — leave them for tsc to handle
        if re.match(r"^\s*import\s+type\s+", import_text):
            continue

        # Parse the import structure
        default_symbol, named_symbols, from_path = _parse_import(import_text)

        if default_symbol is None and not named_symbols:
            # Couldn't parse — skip
            continue

        # Check usage of each symbol in body
        used_default = default_symbol and _is_symbol_used(default_symbol, body)
        used_named = [s for s in named_symbols if _is_symbol_used(s, body)]

        removed_count = 0
        if default_symbol and not used_default:
            removed_count += 1
        removed_count += len(named_symbols) - len(used_named)

        if removed_count == 0:
            # Everything is used — leave it alone
            continue

        # Build replacement
        if not used_default and not used_named:
            # Nothing is used — remove entire import
            logger.debug(
                "Removing entire import: %s",
                import_text.replace("\n", " ").strip()[:80],
            )
            for idx in range(start_idx, end_idx + 1):
                lines[idx] = None  # type: ignore[assignment]
            fix_count += removed_count
            continue

        # Reconstruct with only used symbols
        parts = []
        if used_default:
            parts.append(default_symbol)

        if used_named:
            named_str = "{ " + ", ".join(used_named) + " }"
            parts.append(named_str)

        new_import = f"import {', '.join(parts)} from {from_path}"

        # Determine original indentation
        indent = ""
        original_first = lines[start_idx]
        indent_match = re.match(r"^(\s*)", original_first)
        if indent_match:
            indent = indent_match.group(1)

        # Replace the block
        for idx in range(start_idx, end_idx + 1):
            lines[idx] = None  # type: ignore[assignment]
        lines[start_idx] = indent + new_import

        removed_names = set(named_symbols) - set(used_named)
        if default_symbol and not used_default:
            removed_names.add(default_symbol)
        logger.debug("Trimmed import: removed %s", ", ".join(sorted(removed_names)))
        fix_count += removed_count

    # Reassemble, dropping removed lines
    cleaned = "\n".join(line for line in lines if line is not None)
    return cleaned, fix_count


def _parse_import(import_text: str) -> tuple[str | None, list[str], str]:
    """Parse an import statement into (default_symbol, named_symbols, from_clause).

    Returns (None, [], '') if the import cannot be parsed.
    The from_clause includes the quotes, e.g. \"'react'\".
    """
    # Normalize multiline to single line for parsing
    normalized = re.sub(r"\s*\n\s*", " ", import_text).strip()

    # Extract from clause
    from_match = re.search(r"\bfrom\s+(['\"].+?['\"])\s*;?\s*$", normalized)
    if not from_match:
        return None, [], ""
    from_path = from_match.group(1)

    # Get everything between 'import' and 'from'
    after_import = normalized[len("import") : from_match.start()].strip()

    # Remove 'type' keyword if present (shouldn't reach here, but safety)
    after_import = re.sub(r"^type\s+", "", after_import)

    default_symbol = None
    named_symbols: list[str] = []

    # Check for named imports in braces
    brace_match = re.search(r"\{([^}]*)\}", after_import)
    if brace_match:
        raw_names = brace_match.group(1)
        for name in raw_names.split(","):
            name = name.strip()
            if not name:
                continue
            # Handle 'X as Y' — the local name is Y
            if " as " in name:
                name = name.split(" as ")[-1].strip()
            named_symbols.append(name)

        # Check for default import before the braces
        before_brace = after_import[: brace_match.start()].strip().rstrip(",").strip()
        if before_brace:
            default_symbol = before_brace
    else:
        # No braces — must be a default import
        clean = after_import.strip().rstrip(",").strip()
        if clean and re.match(r"^[A-Za-z_$][A-Za-z0-9_$]*$", clean):
            default_symbol = clean

    return default_symbol, named_symbols, from_path


def _is_symbol_used(symbol: str, body: str) -> bool:
    """Check if a symbol is referenced in the body text using word boundaries."""
    pattern = r"\b" + re.escape(symbol) + r"\b"
    return bool(re.search(pattern, body))


# =============================================================================
# Pass 2 — Remove unused state declarations
# =============================================================================


def _remove_unused_state_vars(tsx: str) -> tuple[str, int]:
    """Remove or simplify unused useState declarations.

    Handles two cases:
      1. Both value and setter are unused → remove entire line
      2. Only the setter is unused → rewrite to `const [value] = useState(...)`

    Returns (cleaned_source, number_of_fixes_applied).
    """
    lines = tsx.split("\n")
    fix_count = 0

    # Match: const [foo, setFoo] = useState(...)
    # Captures: indent, value_name, setter_name, full line
    use_state_pattern = re.compile(r"^(\s*)const\s+\[(\w+),\s*(set\w+)\]\s*=\s*useState")

    # Process in reverse so removals don't shift indices
    for i in range(len(lines) - 1, -1, -1):
        match = use_state_pattern.match(lines[i])
        if not match:
            continue

        value_name = match.group(2)
        setter_name = match.group(3)

        # Build body excluding this line (and any already-removed lines)
        body_lines = [ln for j, ln in enumerate(lines) if j != i and ln is not None]
        body = "\n".join(body_lines)

        value_used = _is_symbol_used(value_name, body)
        setter_used = _is_symbol_used(setter_name, body)

        if not value_used and not setter_used:
            # Neither is used — remove the entire line
            logger.debug("Removing unused state: [%s, %s]", value_name, setter_name)
            lines[i] = None  # type: ignore[assignment]
            fix_count += 1

        elif value_used and not setter_used:
            # Setter unused — simplify to const [value] = useState(...)
            # Preserve everything after useState including the initializer
            old_line = lines[i]
            # Replace the destructuring pattern, keeping the rest
            new_line = re.sub(
                r"\[" + re.escape(value_name) + r",\s*" + re.escape(setter_name) + r"\]",
                f"[{value_name}]",
                old_line,
            )
            if new_line != old_line:
                logger.debug("Simplified state: removed unused setter %s", setter_name)
                lines[i] = new_line
                fix_count += 1

        # If value is unused but setter is used, leave it — that's valid React

    cleaned = "\n".join(line for line in lines if line is not None)
    return cleaned, fix_count


# =============================================================================
# Main entry point
# =============================================================================


def cleanup_tsx_files(files: dict[str, str]) -> tuple[dict[str, str], int]:
    """Run deterministic cleanup on TSX page files.

    Only processes files matching ``src/pages/*.tsx``. Applies:
      1. Unused import removal
      2. Unused state declaration removal / simplification

    Args:
        files: All prototype files as {relative_path: source_content}.

    Returns:
        (cleaned_files, total_fix_count) — cleaned_files is the full dict
        with page files patched in-place. Non-page files pass through unchanged.
    """
    total_fixes = 0
    result = dict(files)

    page_files = [name for name in files if name.startswith("src/pages/") and name.endswith(".tsx")]

    if not page_files:
        logger.info("Cleanup: no page files found — skipping")
        return result, 0

    logger.info("Cleanup: processing %d page files", len(page_files))

    for name in sorted(page_files):
        source = result[name]
        file_fixes = 0

        # Pass 1: unused imports
        source, n = _remove_unused_imports(source)
        file_fixes += n

        # Pass 2: unused state vars
        source, n = _remove_unused_state_vars(source)
        file_fixes += n

        if file_fixes > 0:
            logger.info("Cleanup: %s — %d fix(es)", name, file_fixes)
            result[name] = source
            total_fixes += file_fixes

    logger.info("Cleanup: %d total fix(es) across %d files", total_fixes, len(page_files))
    return result, total_fixes
