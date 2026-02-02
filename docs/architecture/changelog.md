# Architecture Changelog

**Last Updated:** 2026-01-30

This document tracks significant architecture changes to the AIOS Req Engine. Weekly updates capture major additions, refactors, and breaking changes.

---

## Week of January 27 - January 30, 2026

### Major Changes

**Document Processing Pipeline Fixes**
- Fixed signal content parameters to properly pass through processing
- Implemented expandable UI for document analysis results
- Added delete and withdraw functionality for uploaded documents
- Implemented proper error handling for document processing failures

**Memory & Intelligence System**
- Launched unified memory synthesis combining project memory + knowledge graph
- Implemented automatic cache invalidation on data changes
- Added memory compaction at 2000 token threshold
- Built memory visualization graph (nodes, edges, belief history)
- Added 3-tier memory system: decisions, learnings, questions

**DI Agent Enhancements**
- Improved gap analysis with requirements validation
- Added gate-based readiness scoring
- Implemented tool result caching
- Enhanced reasoning trace logging
- Added gap fix suggestion endpoint

**Frontend Integration**
- Deployed new Memory & Intelligence panel with graph visualization
- Added Sources tab with usage statistics
- Improved signal processing UI with expandable sections
- Enhanced error messaging for failed operations

### Breaking Changes
- None this week

### Deprecations
- `GET /projects/{project_id}/memory` - Use unified memory endpoint instead

---

## Week of January 20 - January 26, 2026

### Major Changes

**Project Foundation System**
- Launched DI Agent with OBSERVE → THINK → DECIDE → ACT pattern
- Implemented 7-gate readiness model (foundation, solution, prototype, build)
- Added automatic extraction: core pain, persona, wow moment, business case, constraints
- Built foundation caching and invalidation system

**Research Pipeline**
- Integrated n8n workflows for multi-source research
- Added research job tracking and status monitoring
- Implemented hybrid search (vector + keyword) for evidence
- Added evidence gap analysis and statistics

**API Expansion**
- Added 15+ new endpoints for DI Agent and foundation
- Implemented research and evidence endpoints
- Added project memory CRUD operations
- Created gap analysis endpoints

### Breaking Changes
- `project_gates` table schema updated with new gate types
- `project_foundation` table created (migrate existing data)

---

## Week of January 13 - January 19, 2026

### Major Changes

**Signal Processing Improvements**
- Refactored signal pipeline for better modularity
- Added contextual chunking for improved RAG
- Implemented signal classification (market research, competitive analysis, etc.)
- Added source tracking and usage statistics

**Database Optimizations**
- Added ivfflat index on `signal_chunks.embedding` for faster vector search
- Optimized project state snapshot generation
- Implemented readiness score caching
- Added batch operations for entity updates

**Testing Infrastructure**
- Added 37 new tests for document processing pipeline
- Implemented integration tests for DI Agent
- Added test fixtures for common scenarios
- Improved test coverage to ~40%

### Breaking Changes
- `signals.metadata` structure changed (added `source_type` field)

---

## Week of January 6 - January 12, 2026

### Major Changes

**LangGraph Migration**
- Migrated all workflows to LangGraph state machines
- Implemented graph-based orchestration for complex flows
- Added run_id tracking for distributed tracing
- Built job monitoring system

**Multi-Tenancy**
- Added organizations table and membership model
- Implemented project sharing within organizations
- Added role-based access control (owner, editor, viewer)
- Built organization invitation system

**Enrichment Workflows**
- Created enrich_personas_graph for persona enrichment
- Created enrich_features_graph for feature enrichment
- Created enrich_vp_graph for value proposition generation
- Added surgical update graph for targeted entity updates

### Breaking Changes
- All enrichment endpoints now require `run_id` parameter
- Graph invocations return `LangGraph` state objects

---

## December 2025

### Major Changes

**Initial Architecture**
- Established clean architecture pattern (API → Graphs → Chains → Core → DB)
- Implemented Supabase integration with pgvector
- Added Anthropic Claude integration
- Created baseline signal processing pipeline
- Built initial entity models (personas, features, VP)

**Core Systems**
- Implemented JWT authentication via Supabase
- Added structured logging
- Created readiness scoring system
- Built state snapshot system

---

## Migration History

| Date | Migration | Description |
|------|-----------|-------------|
| 2026-01-25 | add_memory_graph_tables | Added memory_graph, memory_edges, memory_history |
| 2026-01-22 | add_project_foundation | Added project_foundation table |
| 2026-01-20 | add_di_agent_tables | Added di_logs, di_cache tables |
| 2026-01-15 | add_document_uploads | Added document_uploads table |
| 2026-01-10 | add_organizations | Added organizations, organization_members |
| 2026-01-05 | add_ivfflat_index | Added vector index on signal_chunks |
| 2025-12-20 | add_project_gates | Added project_gates table |
| 2025-12-15 | add_cached_readiness | Added cached readiness fields to projects |
| 2025-12-10 | add_signal_chunks | Added signal_chunks table with embeddings |
| 2025-12-01 | initial_schema | Initial schema creation |

---

## Upcoming Architecture Changes

**Next Quarter (Q1 2026):**
- WebSocket support for real-time collaboration
- Redis caching layer
- Event sourcing for full audit trail
- GraphQL API layer
- Microservice split (document processing service)

**Technical Debt Roadmap:**
- Increase test coverage to >80%
- Add Mypy strict mode
- Consolidate old migrations
- Improve observability (structured logging, tracing)
- Auto-generate OpenAPI specs

---

**Note:** This changelog is updated weekly. For daily changes, see git commit history.
