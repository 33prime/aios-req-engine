# Core Engineering Rules (AIOS Req Engine)

## Prime Directive
Produce production-quality code: readable, testable, typed, and deterministic where possible.

## Non-negotiables
- No giant files. Prefer small modules (<= 200–300 lines) with single responsibility.
- No "magic" globals. Use dependency injection via explicit parameters.
- No side effects inside pure logic modules.
- No silent failures. Raise typed exceptions or return structured errors.
- Every public function has type hints and docstring (short, practical).
- Never print; use structured logging.

## Style
- Python 3.11+
- ruff for lint, black formatting, pytest for tests
- Prefer dataclasses/Pydantic models for schemas.
- Use explicit naming over clever naming.

## Clean architecture boundaries
- app/api: HTTP only (request validation + orchestration)
- app/graphs: LangGraph orchestration only (no DB writes directly)
- app/chains: LLM prompts + parsers only
- app/core: config, schemas, policy, logging
- app/db: all Supabase/Postgres access
- tests: fast unit tests + fixtures

## Determinism + safety
- LLM outputs must validate against schemas.
- Never let LLM directly write to DB.
- Canonical state updates must go through policy rules.

## Output rules for Cursor
- Provide complete files when creating new modules.
- If modifying a file: show a minimal diff or clearly marked replacement sections.
- Always include the import list and keep it sorted.

## Definition of Done
- Type hints present
- Schema validation implemented
- Tests for policy changes
- No mixed concerns

