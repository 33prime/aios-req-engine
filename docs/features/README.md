# Consultant Workflow Features

This directory contains documentation for the enhanced consultant workflow features implemented in Phases 2-7.

## Overview

These features enhance the consultant experience with AI-powered insights, tracking, and collaboration tools:

1. **Change Logs** - Track enrichment evolution with context
2. **Personas Enhancement** - Interactive card view with detailed modals
3. **Feature Lifecycle** - Manage feature progression through discovery, refinement, and confirmation
4. **PRD Summary** - AI-generated executive summaries
5. **Meeting Agent** - Generate structured agendas from confirmations

## Features Documentation

- [**Change Logs**](./change-logs.md) - Enrichment revision tracking and timeline display
- [**Personas**](./personas.md) - Dual-view persona display with card grid and modals
- [**Feature Lifecycle**](./feature-lifecycle.md) - Three-stage feature progression system
- [**PRD Summary**](./prd-summary.md) - Executive summary generation and display
- [**Meeting Agent**](./meeting-agent.md) - AI-powered meeting agenda generation

## Quick Start

### Enable Features

All features are enabled by default. To disable specific features:

```bash
# In .env file
ENABLE_ENRICHMENT_REVISIONS=false  # Disable change logs
ENABLE_PRD_SUMMARY_AUTO_UPDATE=true  # Enable auto-regeneration of summaries
ENABLE_MEETING_AGENT=false  # Disable meeting agenda generation
```

### Common Workflows

#### View Change History

1. Navigate to any PRD section, VP step, or feature detail
2. Scroll to "Change Log" section
3. Expand timeline to see enrichment evolution
4. View context like "Based on 5 new signals"

#### Work with Personas

1. Go to PRD → Personas section
2. Toggle between Text and Card views
3. Click any persona card to open detailed modal
4. Explore related features and VP steps

#### Manage Feature Lifecycle

1. View any feature in Features tab
2. See lifecycle badge (Discovered/Refined/Confirmed)
3. Click lifecycle stages to progress
4. Provide evidence when confirming

#### Generate PRD Summary

1. Go to PRD tab
2. Click "Regenerate" on Executive Summary card
3. Wait for generation (~10 seconds)
4. Review TL;DR and prototype requirements

#### Create Meeting Agenda

1. Go to Actions tab
2. Click "Generate Meeting Agenda"
3. Select confirmations to discuss
4. Click "Generate Agenda"
5. Review and export (Markdown/Text)

## Implementation Status

| Feature | Status | Database | Backend | Frontend | Docs |
|---------|--------|----------|---------|----------|------|
| Change Logs | ✅ Complete | ✅ | ✅ | ✅ | ✅ |
| Personas | ✅ Complete | N/A | ✅ | ✅ | ✅ |
| Feature Lifecycle | ✅ Complete | ✅ | ✅ | ✅ | ✅ |
| PRD Summary | ✅ Complete | ✅ | ✅ | ✅ | ✅ |
| Meeting Agent | ✅ Complete | ✅ | ✅ | ✅ | ✅ |

## Architecture

### Database Tables

- `enrichment_revisions` - Tracks enrichment changes over time
- `features` - Extended with lifecycle_stage, confirmed_evidence, confirmation_date
- `prd_sections` - Extended with is_summary, summary_attribution for summaries
- `meeting_agendas` (future) - Will store generated agendas

### Backend Components

**Graphs (LangGraph Agents)**:
- `enrich_prd_graph.py` - PRD enrichment with revision tracking
- `enrich_vp_graph.py` - VP enrichment with revision tracking
- `enrich_features_graph.py` - Feature enrichment with auto-lifecycle progression
- `generate_prd_summary_graph.py` - PRD summary generation
- (Meeting agent uses chain, not graph)

**Chains (LLM Calls)**:
- `generate_prd_summary.py` - LLM chain for summary generation
- `generate_meeting_agenda.py` - LLM chain for agenda generation

**Database Operations**:
- `db/revisions_enrichment.py` - Revision CRUD operations
- `db/features.py` - Extended with lifecycle functions
- `db/confirmations.py` - Extended with batch ID lookup

**API Endpoints**:
- `/state/{entity_type}/{entity_id}/revisions` - List revisions
- `/features/{feature_id}/lifecycle` - Update lifecycle
- `/agents/generate-prd-summary` - Generate summary
- `/agents/generate-meeting-agenda` - Generate agenda

### Frontend Components

**Revisions**:
- `components/revisions/ChangeLogTimeline.tsx`
- `components/revisions/EnrichmentContext.tsx`

**Personas**:
- `components/personas/PersonaCard.tsx`
- `components/personas/PersonaModal.tsx`
- `lib/persona-utils.ts`

**Features**:
- `components/features/FeatureLifecycleView.tsx`

**Meeting**:
- `components/meeting/MeetingAgendaBuilder.tsx`
- `components/meeting/MeetingAgendaDisplay.tsx`
- `lib/export-utils.ts`

## Configuration Reference

```python
# Models
PRD_SUMMARY_MODEL = "gpt-4o-mini"  # or "claude-3-5-sonnet-20241022"
MEETING_AGENDA_MODEL = "gpt-4o-mini"

# Feature Flags
ENABLE_ENRICHMENT_REVISIONS = True
ENABLE_PRD_SUMMARY_AUTO_UPDATE = False  # Default off for safety
ENABLE_MEETING_AGENT = True
```

## Performance Benchmarks

| Operation | Typical Time | Notes |
|-----------|--------------|-------|
| Load revisions | < 100ms | First 50 revisions |
| Parse personas | < 50ms | Client-side parsing |
| Update lifecycle | < 200ms | Database update |
| Generate summary | 8-12s | LLM call |
| Generate agenda | 10-15s | LLM call |

## API Rate Limits

No specific rate limits for these features. Standard OpenAI API limits apply:
- GPT-4o-mini: 10,000 requests/day (Tier 1)
- Consider implementing rate limiting for summary/agenda generation in production

## Security Considerations

1. **Evidence Privacy**: Confirmation evidence may contain sensitive client data - ensure proper access control
2. **Meeting Agendas**: Generated agendas may expose internal discussions - review before external sharing
3. **Attribution**: summary_attribution and created_by fields track user emails - ensure GDPR compliance

## Troubleshooting

### Change logs not appearing

- Check `ENABLE_ENRICHMENT_REVISIONS` is true
- Verify enrichment actually ran (check run_id)
- Check browser console for API errors

### Personas not parsing

- Verify persona section exists with slug='personas'
- Check enrichment.enhanced_fields.personas structure
- Review browser console for parsing errors

### Feature lifecycle not updating

- Confirm feature exists with valid ID
- Check lifecycle_stage constraint (must be valid stage)
- Verify user has permission to update features

### Summary generation fails

- Check OpenAI API key is valid
- Verify project has PRD sections to summarize
- Review backend logs for LLM errors

### Meeting agenda generation fails

- Ensure at least one confirmation selected
- Verify confirmations exist with provided IDs
- Check OpenAI API quota

## Support

For issues or questions:
1. Check feature-specific documentation above
2. Review API endpoint documentation
3. Check backend logs for error details
4. Review browser console for frontend errors

## Future Roadmap

### Phase 8: Analytics & Reporting
- Track enrichment frequency and quality metrics
- Feature confirmation rate analytics
- Meeting agenda effectiveness metrics

### Phase 9: Collaboration
- Multi-user annotation on PRD sections
- Comment threads on confirmations
- Shared meeting agendas with attendee feedback

### Phase 10: Integrations
- Calendar integration for meeting scheduling
- Email templates for agenda distribution
- Notion/Confluence export for documentation
- Slack notifications for confirmations

## Contributing

When extending these features:

1. **Database**: Add migrations in sequential order (0001_*.sql)
2. **Backend**: Follow existing patterns (graphs for multi-step, chains for single LLM call)
3. **Frontend**: Use existing UI components (Card, Button, Modal)
4. **Documentation**: Update relevant feature docs in this directory
5. **Testing**: Add integration tests for new workflows

## License

Internal use only. Not for external distribution.
