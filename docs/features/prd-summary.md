# PRD Summary Generation

## Overview

The PRD Summary agent generates an executive summary of the entire PRD, providing:
- **TL;DR**: 2-3 sentence overview
- **What's Needed for Prototype**: High-level requirements list
- **Key Risks**: Major concerns and blockers
- **Estimated Complexity**: Low/Medium/High assessment
- **Section Summaries**: Brief summaries of each PRD section

## How It Works

### Input Gathering

The agent collects comprehensive context:

1. **PRD Sections**: All enriched sections (overview, personas, goals, etc.)
2. **Features**: All features with enrichment details
3. **VP Steps**: Complete value proposition steps

### LLM Analysis

Using the configured `PRD_SUMMARY_MODEL` (default: gpt-4o-mini), the agent:

1. Analyzes all PRD content holistically
2. Identifies key themes and requirements
3. Extracts prototype requirements
4. Assesses risks and complexity
5. Generates section summaries

### Output Format

```python
class PrdSummaryOutput(BaseModel):
    tldr: str  # Executive overview
    what_needed_for_prototype: str  # Prototype requirements
    key_risks: str | None  # Major concerns
    estimated_complexity: str  # Low/Medium/High
    section_summaries: dict[str, str]  # Brief summaries per section
```

### Storage

The summary is stored as a special PRD section:
- `slug = 'executive_summary'`
- `is_summary = true`
- `summary_attribution` contains creation metadata

## UI Display

### Summary Card

Displayed at the top of the PRD sections list in `PrdList.tsx`:

```tsx
{summarySection && (
  <Card className="border-2 border-brand-primary/30">
    <CardHeader
      title={<><Sparkles /> Executive Summary</>}
      actions={
        <Button onClick={handleRegenerate}>
          <RefreshCw /> Regenerate
        </Button>
      }
    />
    {/* TL/DR */}
    {/* What's Needed for Prototype */}
    {/* Key Risks */}
    {/* Estimated Complexity */}
    {/* Attribution */}
  </Card>
)}
```

**Visual Styling**:
- Distinct border color (brand primary)
- Gradient background
- Sparkles icon for AI-generated content
- Prominent positioning at top of list

### Attribution Display

Shows who created/approved the summary:

```json
{
  "created_by": "consultant@example.com",
  "confirmed_by": ["client@example.com"],
  "run_id": "uuid",
  "created_at": "2025-01-15T10:30:00Z"
}
```

## API Endpoints

### Generate PRD Summary

```
POST /v1/agents/generate-prd-summary
```

**Request Body**:
```json
{
  "project_id": "uuid",
  "created_by": "consultant@example.com"
}
```

**Response**:
```json
{
  "run_id": "uuid",
  "job_id": "uuid",
  "summary_section_id": "uuid",
  "summary": "Successfully generated PRD summary with 8 section summaries"
}
```

### Async Job Tracking

The summary generation runs as an async job. Track progress:

```
GET /v1/jobs/{job_id}
```

## LangGraph Agent

### State Definition

```python
@dataclass
class GeneratePRDSummaryState:
    project_id: UUID
    run_id: UUID
    trigger: str  # 'manual' | 'auto_after_enrich'
    created_by: str | None
    # ... loaded data fields
```

### Graph Nodes

1. **load_prd_data**: Fetch all PRD sections, features, VP steps
2. **generate_summary**: Call LLM to generate summary
3. **persist_summary**: Save as special PRD section

### Error Handling

If generation fails:
- Previous summary (if exists) remains unchanged
- Error logged with full context
- 500 error returned to client with details

## Configuration

### Model Selection

```python
# In .env
PRD_SUMMARY_MODEL=gpt-4o-mini  # Default
# or
PRD_SUMMARY_MODEL=claude-3-5-sonnet-20241022  # For higher quality
```

### Auto-Update (Optional)

Enable automatic regeneration after enrichment:

```python
ENABLE_PRD_SUMMARY_AUTO_UPDATE=false  # Default: false (manual only)
```

**⚠️ Warning**: Auto-update is disabled by default to prevent:
- Unexpected summary changes
- Overwriting consultant edits
- Excessive LLM costs

When enabled, summary regenerates after:
- PRD section enrichment
- Feature enrichment (if significant changes)
- VP enrichment

## Manual Workflow

### When to Generate

Generate or regenerate summary when:

1. **Initial PRD Complete**: All sections enriched for first time
2. **Major Updates**: Significant new signals or research added
3. **Before Client Review**: Ensure summary reflects latest state
4. **After Feature Confirmation**: Update prototype requirements

### Regeneration Process

1. Click "Regenerate" button on summary card
2. Wait for async job to complete (~10-15 seconds)
3. Page auto-refreshes with updated summary
4. Review changes and share with client

## Use Cases

### Executive Briefing

Share the TL;DR and prototype requirements with:
- Client executives
- Engineering leadership
- Product stakeholders

**Format**: Copy directly from summary card or export full PRD

### Prototype Planning

Use "What's Needed for Prototype" to:
- Scope MVP features
- Estimate development timeline
- Plan sprint 0 activities

### Risk Assessment

Review "Key Risks" section to:
- Identify blockers early
- Plan mitigation strategies
- Set client expectations

### Complexity Estimation

Use complexity rating (Low/Medium/High) to:
- Estimate project duration
- Allocate resources
- Price engagement

## Section Summaries

Each PRD section gets a 1-2 sentence summary:

```
{
  "overview": "Platform for connecting freelance designers with clients...",
  "personas": "Primary users are Sarah (product manager) and Alex (freelance designer)...",
  "goals": "Core objectives include reducing time-to-hire by 50% and improving match quality...",
  ...
}
```

**Use Case**: Quick navigation and stakeholder briefings

## Attribution and Approval

### Created By

Records who triggered the generation (consultant email).

### Confirmed By

Optional: Array of stakeholders who approved the summary.

**Future**: Allow multiple approvers with approval workflow.

### Run ID

Links summary to specific agent run for audit trail and debugging.

## Best Practices

### For Consultants

1. **Generate Early**: Create summary after initial enrichment
2. **Review Before Sharing**: Always review AI-generated content
3. **Update Regularly**: Regenerate when PRD changes significantly
4. **Customize if Needed**: Edit summary section directly if AI output needs tweaking
5. **Track Attribution**: Note who created and approved summary

### For Clients

1. **Start with TL;DR**: Get high-level understanding quickly
2. **Review Prototype Requirements**: Align on MVP scope
3. **Discuss Risks**: Address concerns before development
4. **Approve Summary**: Provide written approval for documentation

## Performance

**Typical Generation Time**: 8-12 seconds

**Factors Affecting Performance**:
- Number of PRD sections (more sections = longer processing)
- Feature count (100+ features adds ~2-3 seconds)
- Model selection (Sonnet slower but higher quality than GPT-4o-mini)

**Optimization**:
- Async job prevents blocking UI
- Cached settings reduce overhead
- Limited context sent to LLM (only essential data)

## Future Enhancements

- Export summary to PowerPoint/PDF
- Compare summaries across versions
- Approval workflow with multiple stakeholders
- Automatic summary updates with change notifications
- Summary templates for different project types
- Integration with project management tools
