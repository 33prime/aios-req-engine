# n8n Workflows

**Last Updated:** 2026-01-30

## Overview

AIOS integrates with n8n for workflow automation and research orchestration. n8n workflows can be triggered from the FastAPI backend and execute complex multi-step processes.

## Available Workflows

### Research Workflows

Currently, n8n workflows are used primarily for:
1. **Research pipeline** - Multi-source research and synthesis
2. **Document processing** - Background document analysis
3. **External API integrations** - Third-party service calls

## Integration Pattern

**Trigger Flow:**
```
FastAPI endpoint → n8n webhook → n8n workflow → FastAPI callback
```

**Example:**
1. User requests research via `/v1/research/run`
2. FastAPI creates job record
3. FastAPI triggers n8n webhook with job details
4. n8n executes multi-step workflow (search → retrieve → analyze → synthesize)
5. n8n POSTs results back to `/v1/research/ingest`
6. FastAPI processes results and updates job status

## n8n Workflow Configuration

**Webhook URL:** Configured via environment variable `N8N_WEBHOOK_URL`

**Authentication:** Shared secret in webhook headers

**Timeout:** 5 minutes for most workflows

## Future Workflows

Planned n8n integrations:
- **Email parsing** - Auto-ingest emails as signals
- **CRM sync** - Sync stakeholders to CRM
- **Slack notifications** - Post updates to Slack
- **Calendar integration** - Schedule meetings
- **Report generation** - Generate and email reports

## Workflow Development

To create new n8n workflows:
1. Design workflow in n8n UI
2. Configure webhook trigger
3. Add workflow URL to environment variables
4. Create FastAPI endpoint to trigger workflow
5. Test end-to-end flow

## Monitoring

- n8n execution logs available in n8n UI
- FastAPI job status tracking via `/v1/jobs/{job_id}`
- Webhook failures logged in FastAPI

---

**n8n Instance:** Managed via cloud or self-hosted  
**Workflow Count:** 3 active workflows
