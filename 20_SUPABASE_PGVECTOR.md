# Supabase + pgvector Rules

## One DB, one source of truth
Use Supabase Postgres (pgvector) as the vector store and canonical database.

## DB access patterns
- All DB access in app/db/*
- No DB calls inside app/chains/*
- Use small helper functions with clear contracts:
  - insert_signal(...)
  - insert_chunks(...)
  - vector_search_chunks(...)
  - upsert_requirement(...)
  - link_requirement_to_signal(...)

## Migrations
- Store SQL migrations under /migrations
- Never rely on manual console edits after first scaffold.

## Security (v1 dev)
- Use service role key in backend service.
- RLS can be off in dev; tighten later.

## pgvector conventions
- Store embeddings in signal_chunks.embedding (vector(N)).
- Store metadata + offsets so you can cite sources.
- Use cosine distance operators for similarity.

