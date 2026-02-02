# AIOS Req Engine - Architecture Documentation

**Last Updated:** 2026-01-30  
**Maintained By:** Matt

## Overview

This directory contains comprehensive architecture documentation for the AIOS Req Engine. Documents are updated weekly to reflect the current state of the system.

## Document Index

### Core Architecture
- **[overview.md](./overview.md)** - System architecture overview, tech stack, design patterns
- **[database-schema.md](./database-schema.md)** - Complete database schema with ~40 tables
- **[api-endpoints.md](./api-endpoints.md)** - All 50+ API endpoints organized by category
- **[agents.md](./agents.md)** - LangGraph agents (DI Agent, Memory Agent, Research Agent)
- **[workflows.md](./workflows.md)** - n8n workflow integrations
- **[changelog.md](./changelog.md)** - Weekly architecture changes and migrations

## Quick Links

**For New Developers:**
1. Start with [overview.md](./overview.md) for the big picture
2. Review [database-schema.md](./database-schema.md) to understand data model
3. Check [api-endpoints.md](./api-endpoints.md) for available endpoints

**For Feature Development:**
1. Find relevant endpoints in [api-endpoints.md](./api-endpoints.md)
2. Check [agents.md](./agents.md) if building AI features
3. Review [database-schema.md](./database-schema.md) for data access

**For Integration:**
1. Review [api-endpoints.md](./api-endpoints.md) for available APIs
2. Check [workflows.md](./workflows.md) for n8n integration patterns

## Documentation Philosophy

These docs are:
- **Living documents** - Updated weekly with architecture changes
- **Code-derived** - Generated from actual codebase, not aspirational
- **Maintainable** - Structured for easy updates (eventually automated)
- **Practical** - Focused on what developers need to know

## Weekly Update Process

Every week (Fridays):
1. Review [changelog.md](./changelog.md) for the week
2. Update relevant architecture docs if major changes occurred
3. Commit with message: `docs: weekly architecture update - [date]`

## Future Automation

Plans to automate doc generation:
- **API docs** - Auto-generate from FastAPI schema
- **Database schema** - Extract from Supabase migrations
- **Agents** - Parse agent files for capabilities
- **Changelog** - Git commit summaries + manual curation

## Related Documentation

- **[/docs/](../)** - Feature-specific guides and implementation docs
- **[/README.md](../../README.md)** - Project README with setup instructions
- **[/tests/](../../tests/)** - Test documentation and examples

---

**Questions?** Reach out to Matt or check the main repo README.
