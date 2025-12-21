-- migrations/0001_phase0.sql

create extension if not exists pgcrypto;
create extension if not exists vector;

-- =========================
-- signals: raw inputs
-- =========================
create table if not exists public.signals (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null,
  signal_type text not null,         -- email | transcript | note | file_text | etc
  source text not null,              -- gmail, zoom, upload, manual, etc
  raw_text text not null,
  metadata jsonb not null default '{}'::jsonb,
  run_id uuid not null,
  created_at timestamptz not null default now()
);

create index if not exists idx_signals_project_id on public.signals(project_id);
create index if not exists idx_signals_created_at on public.signals(created_at);

-- =========================
-- signal_chunks: chunked text + embeddings
-- =========================
create table if not exists public.signal_chunks (
  id uuid primary key default gen_random_uuid(),
  signal_id uuid not null references public.signals(id) on delete cascade,
  chunk_index int not null,
  content text not null,
  start_char int not null,
  end_char int not null,
  embedding vector(1536) not null,
  metadata jsonb not null default '{}'::jsonb,
  run_id uuid not null,
  created_at timestamptz not null default now(),
  unique(signal_id, chunk_index)
);

create index if not exists idx_signal_chunks_signal_id on public.signal_chunks(signal_id);
create index if not exists idx_signal_chunks_created_at on public.signal_chunks(created_at);
create index if not exists idx_signal_chunks_embedding on public.signal_chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- =========================
-- requirements: placeholder canonical objects (Phase 0 minimal)
-- =========================
create table if not exists public.requirements (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null,
  title text not null,
  status text not null default 'draft',
  canonical jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_requirements_project_id on public.requirements(project_id);

-- =========================
-- requirement_links: provenance
-- =========================
create table if not exists public.requirement_links (
  id uuid primary key default gen_random_uuid(),
  requirement_id uuid not null references public.requirements(id) on delete cascade,
  signal_id uuid not null references public.signals(id) on delete cascade,
  chunk_id uuid null references public.signal_chunks(id) on delete set null,
  excerpt text null,
  strength real not null default 0.0,
  created_at timestamptz not null default now()
);

create index if not exists idx_requirement_links_requirement_id on public.requirement_links(requirement_id);
create index if not exists idx_requirement_links_signal_id on public.requirement_links(signal_id);

-- =========================
-- jobs: run tracking
-- =========================
create table if not exists public.jobs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid null,
  job_type text not null,
  status text not null default 'queued',
  input jsonb not null default '{}'::jsonb,
  output jsonb not null default '{}'::jsonb,
  run_id uuid not null,
  error text null,
  started_at timestamptz null,
  completed_at timestamptz null,
  created_at timestamptz not null default now()
);

create index if not exists idx_jobs_run_id on public.jobs(run_id);

-- =========================
-- Vector match function
-- =========================
create or replace function public.match_signal_chunks(
  query_embedding vector(1536),
  match_count int,
  filter_project_id uuid default null
)
returns table (
  chunk_id uuid,
  signal_id uuid,
  chunk_index int,
  content text,
  start_char int,
  end_char int,
  similarity float4,
  chunk_metadata jsonb,
  signal_metadata jsonb
)
language sql
stable
as $$
  select
    sc.id as chunk_id,
    sc.signal_id,
    sc.chunk_index,
    sc.content,
    sc.start_char,
    sc.end_char,
    (1 - (sc.embedding <=> query_embedding))::float4 as similarity,
    sc.metadata as chunk_metadata,
    s.metadata as signal_metadata
  from public.signal_chunks sc
  join public.signals s on s.id = sc.signal_id
  where (filter_project_id is null or s.project_id = filter_project_id)
  order by sc.embedding <=> query_embedding
  limit match_count;
$$;
