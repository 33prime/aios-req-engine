# Testing & Quality Rules

## Test layers
1) Unit tests: policy + derivations (no LLM, no DB)
2) Integration tests: DB layer against dev Supabase (optional local)
3) Contract tests: LLM outputs validated against schemas

## Fixtures
- Put sample inputs in tests/fixtures:
  - sample_email.txt
  - sample_transcript.txt
  - sample_notes.txt

## LLM tests
- Mock LLM by default.
- Have an opt-in test marker (e.g., -m llm) for real calls.
- Always assert schema validity, not exact wording.

## CI expectations
- `ruff check .`
- `pytest -q`
- type checking optional (mypy) once stable

