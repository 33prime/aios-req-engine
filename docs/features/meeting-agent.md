# Meeting Agenda Generation

## Overview

The Meeting Agent generates structured, intelligent meeting agendas from selected client confirmations. It automatically:
- **Groups related confirmations** by theme, feature, or persona
- **Sequences topics logically** from broad context-setting to specific details
- **Estimates time allocations** for each discussion topic (5-15 minutes)
- **Suggests discussion approaches** for effective facilitation
- **Generates key questions** to guide the conversation

## Workflow

### 1. Select Confirmations

In the Actions tab, click "Generate Meeting Agenda" to open the selection builder.

**Eligible Confirmations**:
- Status: `open` or `queued`
- Any kind: PRD, VP, Feature, Insight, Gate

**Selection Process**:
- Browse available confirmations
- Check boxes to select items for meeting
- See estimated duration update in real-time (~8 min per item)
- Click "Generate Agenda"

### 2. AI Generation

The agent processes confirmations through:

**Input Analysis**:
- Extract confirmation details (title, why, ask, priority, evidence)
- Identify related themes and topics
- Assess complexity and priority

**Intelligent Grouping**:
- Group by kind (PRD, VP, Feature)
- Group by theme/feature mentioned
- Group by priority level
- Consider suggested method (meeting vs email)

**Logical Sequencing**:
- Start with overview/context topics
- Move to specific features or decisions
- End with next steps or action items

**Time Estimation**:
- Allocate 5-15 minutes per topic
- Consider complexity and number of confirmations
- Aim for 30-90 minute total duration

**Discussion Planning**:
- Suggest presentation approach
- Generate open-ended questions
- Identify key decision points

### 3. Review and Export

**Display**:
- Structured agenda with topics and time allocations
- Expandable items showing discussion approach and questions
- Related confirmations grouped under each topic
- Total estimated duration

**Export Options**:
- **Markdown**: For documentation and sharing
- **Text**: For email or calendar invites

## UI Components

### MeetingAgendaBuilder

Modal for selecting confirmations:

```tsx
<MeetingAgendaBuilder
  confirmations={confirmations}
  onGenerate={handleGenerateMeetingAgenda}
  onClose={() => setShowAgendaBuilder(false)}
/>
```

**Features**:
- Multi-select checkboxes
- Select all / Deselect all controls
- Real-time duration estimate
- Filtering to eligible confirmations only
- Visual feedback (selected items highlighted)

### MeetingAgendaDisplay

Interactive agenda viewer:

```tsx
<MeetingAgendaDisplay
  agenda={meetingAgenda}
  onClose={handleCloseMeetingAgenda}
/>
```

**Features**:
- Collapsible agenda items
- Expand all / Collapse all controls
- Export to Markdown/Text
- Visual progress indicators (agenda item numbers)
- Duration and confirmation count stats

## API Endpoints

### Generate Meeting Agenda

```
POST /v1/agents/generate-meeting-agenda
```

**Request Body**:
```json
{
  "project_id": "uuid",
  "confirmation_ids": ["uuid1", "uuid2", "uuid3"],
  "created_by": "consultant@example.com"
}
```

**Response**:
```json
{
  "title": "Client Alignment Meeting - Product Features & UX",
  "summary": "Review and confirm key product features, user personas, and UX decisions",
  "suggested_duration_minutes": 60,
  "agenda_items": [
    {
      "topic": "User Personas & Target Audience",
      "time_allocation_minutes": 15,
      "discussion_approach": "Present personas and gather feedback on demographics and goals",
      "related_confirmation_ids": ["uuid1", "uuid2"],
      "key_questions": [
        "Do these personas align with your understanding of the target users?",
        "Are there any missing user segments we should consider?"
      ]
    }
  ],
  "confirmation_count": 3
}
```

## LLM Chain

### System Prompt

Instructs the LLM to:
- Output ONLY valid JSON (no markdown)
- Group related confirmations logically
- Sequence broad → specific
- Allocate realistic time
- Suggest facilitation approach
- Generate open-ended questions

### Context Building

```python
context_parts = []
for conf in confirmations:
    context_parts.append(f"[{conf.kind.upper()}] {conf.title}")
    context_parts.append(f"Priority: {conf.priority}")
    context_parts.append(f"Why: {conf.why}")
    context_parts.append(f"Ask: {conf.ask}")
```

### Output Schema

```python
class AgendaItem(BaseModel):
    topic: str
    time_allocation_minutes: int
    discussion_approach: str
    related_confirmation_ids: list[str]
    key_questions: list[str]

class MeetingAgendaOutput(BaseModel):
    title: str
    summary: str
    suggested_duration_minutes: int
    agenda_items: list[AgendaItem]
```

## Configuration

### Model Selection

```python
# In .env
MEETING_AGENDA_MODEL=gpt-4o-mini  # Default
# or
MEETING_AGENDA_MODEL=claude-3-5-sonnet-20241022  # For better grouping logic
```

### Feature Flag

Enable/disable meeting generation:

```python
ENABLE_MEETING_AGENT=true  # Default: true
```

## Grouping Strategies

The AI uses several strategies to group confirmations:

### By Kind
- All PRD confirmations together
- All VP confirmations together
- All Feature confirmations together

### By Theme
- "User Authentication" confirmations grouped
- "Payment Flow" confirmations grouped
- "Admin Dashboard" confirmations grouped

### By Priority
- High priority items first
- Medium and low priority later
- Critical blockers at start

### By Complexity
- Simple clarifications early
- Complex decisions mid-meeting
- Strategic discussions after context established

## Export Formats

### Markdown

```markdown
# Client Alignment Meeting - Product Features & UX

**Summary:** Review and confirm key product features, user personas, and UX decisions

**Duration:** 60 minutes | **Items:** 4 | **Confirmations:** 8

---

## 1. User Personas & Target Audience (15 min)

**Discussion Approach:**
Present personas and gather feedback on demographics and goals

**Key Questions:**
- Do these personas align with your understanding of the target users?
- Are there any missing user segments we should consider?

**Related Confirmations:** 2 items

---
```

### Plain Text

```
CLIENT ALIGNMENT MEETING - PRODUCT FEATURES & UX
=================================================

Summary: Review and confirm key product features, user personas, and UX decisions

Duration: 60 minutes | Items: 4 | Confirmations: 8

------------------------------------------------------------

1. User Personas & Target Audience (15 min)

   Discussion Approach:
   Present personas and gather feedback on demographics and
   goals

   Key Questions:
   • Do these personas align with your understanding of the
     target users?
   • Are there any missing user segments we should consider?

   Related Confirmations: 2 items

------------------------------------------------------------
```

## Use Cases

### Client Sync Meetings

**Scenario**: Weekly client sync to review progress and get confirmations

**Process**:
1. Queue confirmations throughout the week as they arise
2. Day before meeting, generate agenda from queued items
3. Share agenda with client via email
4. Use agenda to structure meeting
5. Mark confirmed items as "resolved" after meeting

### Stakeholder Review

**Scenario**: Review session with multiple stakeholders

**Process**:
1. Select all high-priority confirmations
2. Generate agenda with estimated 60-90 min duration
3. Export to Markdown for advance sharing
4. Present topics in suggested order
5. Record decisions and update confirmations

### Sprint Planning

**Scenario**: Clarify requirements before sprint starts

**Process**:
1. Select feature-related confirmations
2. Generate focused agenda on technical details
3. Include engineering team in meeting
4. Confirm acceptance criteria and edge cases
5. Mark features as "confirmed" to move to backlog

## Best Practices

### Selection

1. **Limit Scope**: 5-10 confirmations for 60-minute meeting
2. **Related Items**: Select confirmations for a specific theme/feature
3. **Priority First**: Include high-priority items
4. **Prepare Evidence**: Have evidence sources ready to reference

### Presentation

1. **Share in Advance**: Send agenda 1-2 days before meeting
2. **Follow Sequence**: Stick to suggested topic order
3. **Use Questions**: Ask the key questions to guide discussion
4. **Time Management**: Monitor time allocations
5. **Document Decisions**: Record outcomes for each topic

### Follow-up

1. **Update Confirmations**: Mark items as resolved/dismissed
2. **Share Notes**: Send meeting summary with decisions
3. **Track Actions**: Create tasks for agreed next steps
4. **Schedule Next**: Queue remaining items for follow-up

## Integration Points

### Calendar (Future)

Planned integration:
- Auto-create calendar event with agenda
- Include attendees from confirmation evidence
- Attach agenda as description
- Set duration based on estimate

### Email (Future)

Planned integration:
- Generate email template with agenda
- Include recipient list from confirmations
- Pre-fill subject line from agenda title
- Attach exported agenda file

### Notion/Confluence (Future)

Planned integration:
- Export agenda to Notion page
- Sync to Confluence space
- Link back to confirmations
- Auto-update with meeting notes

## Performance

**Typical Generation Time**: 10-15 seconds for 5-10 confirmations

**Factors Affecting Performance**:
- Number of confirmations (more items = more context to analyze)
- Confirmation complexity (detailed "why" and "ask" fields)
- Model selection (Sonnet provides better grouping but is slower)

## Error Handling

### No Confirmations Provided

```
400 Bad Request: "No confirmations provided"
```

### Confirmations Not Found

```
404 Not Found: "No confirmations found with provided IDs"
```

### LLM Failure

```
500 Internal Server Error: "Meeting agenda generation failed: [error details]"
```

**Recovery**: Previous agenda (if any) remains unchanged. User can retry.

## Future Enhancements

- Agenda templates for recurring meetings
- Auto-schedule with calendar integration
- Video call link generation (Zoom/Google Meet)
- Meeting notes capture during session
- Automatic confirmation status updates post-meeting
- AI-generated follow-up email drafts
- Agenda versioning and comparison
- Meeting analytics (actual time vs estimated)
