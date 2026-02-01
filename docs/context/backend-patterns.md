# Backend Patterns

Reference patterns for backend development. Mirror these when adding new code.

## API Route

```python
@router.post("/endpoint")
async def endpoint_handler(project_id: UUID, req: RequestModel):
    # Pydantic validates input automatically
    result = await db_function(project_id, req.field)
    return ResponseModel(...)
```

Routes live in `app/api/`. Register new routers in `app/api/__init__.py`.

## LangGraph Node

```python
def node_function(state: StateType) -> StateType:
    # Pure function: read from state, return new state
    # Never mutate, always return new dict
    result = do_work(state["input"])
    return {**state, "output": result}
```

Chains (prompts + parsing) live in `app/chains/`. Graphs (state machines) live in `app/graphs/`.

## Database Access

```python
# app/db/entity_name.py
async def get_entity(id: UUID) -> EntityType | None:
    result = await supabase.table("entities").select("*").eq("id", id).execute()
    return result.data[0] if result.data else None
```

## Testing

```bash
uv run pytest tests/ -v
uv run pytest tests/test_similarity.py -v
```

- Mock Supabase client for unit tests
- Use `pytest-mock` fixtures
- Test files mirror source structure: `app/core/similarity.py` -> `tests/test_similarity.py`
