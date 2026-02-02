# AIOS Req Engine - System Architecture

**Last Updated:** 2026-01-30  
**Version:** 0.1.0

## Executive Summary

AIOS Req Engine is a LangGraph-powered FastAPI microservice that serves as the backend for AIOS (AI Operating System), a client portal platform for consultants. The system handles requirements compilation, strategic analysis, document processing, and AI-powered agents for consultant workflows.

## Core Technology Stack

- **Backend Framework:** FastAPI 
- **AI Orchestration:** LangGraph (state machines for multi-step LLM workflows)
- **Database:** Supabase (PostgreSQL + pgvector for embeddings)
- **LLM Providers:** Anthropic Claude (primary), OpenAI (fallback)
- **Embeddings:** Voyage AI
- **Deployment:** Railway (production), Netlify (frontend)

## Architecture Layers

### 1. API Layer (`app/api/`)
**Purpose:** HTTP endpoints for request validation and orchestration

**Key Modules:**
- `activity.py` - Activity feed and timeline management
- `admin.py` - Admin operations
- `agents.py` - Agent execution endpoints
- `analytics.py` - Analytics and metrics
- `auth.py` - Authentication and authorization
- `baseline.py` - Baseline scoring and gates
- `business_drivers.py` - Business driver management
- `chat.py` - Chat interface for consultants
- `client_portal.py` - Client-facing portal endpoints
- `collaboration.py` - Team collaboration features
- `di_agent.py` - Design Intelligence Agent endpoints
- `discovery_prep.py` - Discovery session preparation
- `document_uploads.py` - Document upload and processing
- `evidence.py` - Evidence collection and management
- `n8n_research.py` - n8n workflow integration
- `projects.py` - Project lifecycle management
- `proposals.py` - Proposal generation
- `research.py` - Research pipeline
- `signals.py` - Signal extraction and processing
- `signal_stream.py` - Real-time signal streaming
- `stakeholders.py` - Stakeholder management
- `state.py` - Project state management
- `tasks.py` - Task management

**Total API Endpoints:** 50+ endpoints across 40+ modules

### 2. Graph Layer (`app/graphs/`)
**Purpose:** LangGraph state machines for complex multi-step workflows

**Key Graphs:**
- `build_state_graph.py` - Project state construction
- `bulk_signal_graph.py` - Batch signal processing
- `document_processing_graph.py` - Document ingestion pipeline
- `enrich_features_graph.py` - Feature enrichment workflow
- `enrich_personas_graph.py` - Persona enrichment workflow
- `enrich_vp_graph.py` - Value proposition enrichment
- `extract_facts_graph.py` - Fact extraction from sources
- `onboarding_graph.py` - User/project onboarding flow
- `research_agent_graph.py` - Multi-source research orchestration
- `surgical_update_graph.py` - Targeted entity updates

### 3. Chain Layer (`app/chains/`)
**Purpose:** LLM prompts, parsers, and single-step transformations

**Key Chains (60+ modules):**
- **Extraction:** Extract facts, claims, stakeholders, risks, constraints
- **Enrichment:** Enrich personas, features, value propositions, KPIs, goals
- **Generation:** Generate agendas, questions, patches, narratives
- **Analysis:** Analyze gaps, detect blind spots, validate changes
- **Synthesis:** Build state, consolidate extractions, strategic context

### 4. Core Layer (`app/core/`)
**Purpose:** Configuration, schemas, policies, shared utilities

**Key Modules:**
- `config.py` - Environment and settings
- `llm.py` - LLM client abstraction
- `embeddings.py` - Vector embedding generation
- `schemas_*.py` - Pydantic models for all entities (20+ schema files)
- `signal_pipeline.py` - Signal processing pipeline
- `chunking.py` - Document chunking strategies
- `similarity.py` - Semantic similarity utilities
- `baseline_scoring.py` - Readiness score calculation
- `document_processing/` - PDF/image extraction, classification, contextual chunking

### 5. Database Layer (`app/db/`)
**Purpose:** Supabase/PostgreSQL data access layer

**Key Tables (40+ tables):**
- **Projects:** projects, project_members, project_state, project_gates
- **Entities:** personas, features, stakeholders, risks, constraints, business_drivers
- **Documents:** facts, signals, evidence, sources, document_uploads
- **Workflows:** creative_briefs, proposals, meetings, discovery_prep
- **AI:** agent_runs, di_logs, di_cache, memory_graph
- **Organizations:** organizations, organization_members, organization_invitations
- **Users:** users, profiles

### 6. Agent Layer (`app/agents/`)
**Purpose:** Specialized LangGraph agents for domain-specific tasks

**Key Agents:**
- `di_agent.py` - Design Intelligence Agent (foundation building)
- `memory_agent.py` - Project memory and context synthesis
- `stakeholder_suggester.py` - Stakeholder identification
- `discovery_prep/` - Discovery session preparation agents
- `research/` - Multi-source research agent

## Data Flow Patterns

### Signal Processing Pipeline
```
Document Upload → PDF/Text Extraction → Chunking → 
Classification → Fact Extraction → Signal Generation → 
Entity Enrichment → State Update
```

### Research Pipeline
```
Research Request → Query Generation → Source Search → 
Content Retrieval → Chunk Processing → Analysis → 
Synthesis → Report Generation
```

### DI Agent Flow
```
User Input → Intent Classification → Memory Retrieval → 
Tool Execution → Entity Updates → Response Generation → 
Memory Update
```

## Key Design Patterns

### 1. LangGraph State Machines
- All complex workflows use LangGraph for orchestration
- State is passed through nodes with full traceability
- Conditional branching based on intermediate results

### 2. Clean Architecture
- API layer depends on graphs/chains
- Graphs depend on chains
- Chains depend on core
- Database layer is isolated
- No circular dependencies

### 3. Schema-Driven Development
- Pydantic models for all entities
- Type-safe throughout the stack
- Automatic validation and serialization

### 4. Signal-Based Updates
- Changes create signals
- Signals are classified and routed
- Entities updated based on signals
- Full audit trail maintained

### 5. RAG with pgvector
- Documents chunked and embedded
- Semantic search for context retrieval
- Hybrid search (vector + keyword)
- Contextual chunking for better retrieval

## Integration Points

### External Services
- **Anthropic API** - Primary LLM (Claude Sonnet 4)
- **OpenAI API** - Fallback LLM, embeddings
- **Voyage AI** - Primary embeddings
- **Firecrawl** - Web content extraction
- **n8n** - Workflow automation
- **Supabase** - Database, auth, storage

### Frontend Applications
- **AIOS RTG** (Netlify) - Main consultant interface
- **Client Portal** - Client-facing views
- **Workbench** - Internal tools

## Deployment Architecture

### Production (Railway)
- FastAPI application on Railway
- Automatic deployments from main branch
- Environment variables managed via Railway
- HTTPS with Railway proxy

### Database (Supabase)
- Managed PostgreSQL instance
- pgvector extension for embeddings
- Row-level security policies
- Automatic backups

## Performance Characteristics

### Response Times
- Simple queries: <100ms
- LLM operations: 2-10s (streaming)
- Document processing: 10-60s (background)
- Research queries: 30-120s (multi-step)

### Scalability
- Stateless API design
- Background job processing
- Rate limiting on LLM calls
- Connection pooling for database

## Security Model

### Authentication
- Supabase Auth integration
- JWT token validation
- API key authentication for services

### Authorization
- Row-level security in Supabase
- Organization-based access control
- Project membership validation

### Data Protection
- HTTPS only
- Secrets in environment variables
- No API keys in logs or responses

## Domain Models

### Strategic Foundation Entities
- **Persona** - User archetype with goals, pain points, motivations
- **Feature** - Product capability mapped to personas
- **Value Proposition** - Core value delivery mechanism
- **Business Driver** - Strategic business goal or KPI
- **Stakeholder** - Key decision maker or influencer
- **Risk** - Potential blocker or concern
- **Constraint** - Budget, time, technical limitation

### Process Entities
- **Signal** - Extracted insight from source material
- **Fact** - Validated claim with evidence
- **Evidence** - Source material supporting facts
- **Proposal** - Generated deliverable (SOW, brief, etc.)
- **Task** - Action item with assignee and deadline

## Future Architecture Considerations

### Planned Enhancements
1. **Real-time collaboration** - WebSocket support for multi-user editing
2. **Advanced caching** - Redis for hot-path data
3. **Event sourcing** - Full event log for time-travel debugging
4. **Microservice split** - Separate document processing service
5. **GraphQL API** - More flexible client queries

### Technical Debt
1. **Test coverage** - Increase from current ~40% to >80%
2. **API documentation** - Auto-generate OpenAPI specs
3. **Observability** - Add structured logging and tracing
4. **Type coverage** - Mypy strict mode across entire codebase
5. **Migration cleanup** - Consolidate old migrations

---

**Maintainer:** Matt  
**Primary Use Case:** Consultant workflow automation and strategic analysis  
**License:** Proprietary
