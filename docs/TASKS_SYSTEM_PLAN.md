# Tasks System Implementation Plan

> Detailed implementation plan for the Tasks system with proper dependencies.

## Overview

This plan introduces a **Tasks** system that serves as the central work management layer for pushing projects toward gate completion. Tasks are distinct from Next Actions (info_requests) but both appear in Overview and Collaboration tabs with different filters.

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TASK SOURCES                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. DI Agent (gap detection)     → gap tasks                                 │
│  2. Signal Processing            → proposal tasks                            │
│  3. Manual (user/AI assistant)   → manual tasks                              │
│  4. Enrichment triggers          → enrichment tasks                          │
│  5. Validation needs             → validation tasks (client-relevant)        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TASKS TABLE                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Unified storage for all task types                                        │
│  • Priority calculated via hybrid approach                                   │
│  • Status: pending → in_progress → completed | dismissed                     │
│  • Anchored to entities (business drivers, features, personas, etc.)         │
│  • Client-relevant flag for Collaboration tab filtering                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
┌───────────────────────────────┐   ┌───────────────────────────────┐
│         OVERVIEW TAB          │   │      COLLABORATION TAB        │
│  (renamed from current)       │   │  (renamed from Next Steps)    │
├───────────────────────────────┤   ├───────────────────────────────┤
│  • All tasks                  │   │  • Client-relevant tasks      │
│  • Next actions preview       │   │  • Full next actions view     │
│  • Project health summary     │   │  • Discovery questions        │
│  • Recent activity            │   │  • Pending client input       │
└───────────────────────────────┘   └───────────────────────────────┘
```

---

## Database Schema

### New Table: `tasks`

```sql
CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

  -- Content
  title TEXT NOT NULL,
  description TEXT,

  -- Type & Classification
  task_type TEXT NOT NULL DEFAULT 'manual',
    -- 'proposal' | 'gap' | 'manual' | 'enrichment' | 'validation' | 'research' | 'collaboration'

  -- Anchoring (what this task relates to)
  anchored_entity_type TEXT,
    -- 'business_driver' | 'feature' | 'persona' | 'vp_step' | 'stakeholder' | 'competitor_ref' | 'gate' | NULL (project-level)
  anchored_entity_id UUID,
  gate_stage TEXT,
    -- Which gate this helps satisfy (for priority calculation)

  -- Priority
  priority_score NUMERIC DEFAULT 50,
    -- Calculated: entity_value × gate_modifier

  -- Status & Lifecycle
  status TEXT NOT NULL DEFAULT 'pending',
    -- 'pending' | 'in_progress' | 'completed' | 'dismissed'

  -- Client Relevance (for Collaboration tab filtering)
  requires_client_input BOOLEAN DEFAULT false,

  -- Source Tracking
  source_type TEXT NOT NULL DEFAULT 'manual',
    -- 'di_agent' | 'signal_processing' | 'manual' | 'enrichment_trigger' | 'ai_assistant'
  source_id UUID,
    -- Reference to proposal_id, signal_id, etc.
  source_context JSONB,
    -- Additional context from source (e.g., proposal details, gap analysis)

  -- Resolution
  completed_at TIMESTAMPTZ,
  completed_by UUID REFERENCES users(id),
  completion_method TEXT,
    -- 'chat_approval' | 'task_board' | 'auto' | 'dismissed'
  completion_notes TEXT,

  -- If this creates a collaboration item
  info_request_id UUID REFERENCES info_requests(id),

  -- Metadata
  metadata JSONB DEFAULT '{}',

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX idx_tasks_project_id ON tasks(project_id);
CREATE INDEX idx_tasks_project_status ON tasks(project_id, status);
CREATE INDEX idx_tasks_project_type ON tasks(project_id, task_type);
CREATE INDEX idx_tasks_anchored ON tasks(anchored_entity_type, anchored_entity_id);
CREATE INDEX idx_tasks_requires_client ON tasks(project_id, requires_client_input) WHERE requires_client_input = true;
CREATE INDEX idx_tasks_priority ON tasks(project_id, priority_score DESC) WHERE status = 'pending';

-- Trigger for updated_at
CREATE TRIGGER tasks_updated_at
  BEFORE UPDATE ON tasks
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();
```

### New Table: `task_activity_log`

```sql
CREATE TABLE task_activity_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

  -- Activity
  action TEXT NOT NULL,
    -- 'created' | 'started' | 'completed' | 'dismissed' | 'reopened' | 'updated'
  actor_type TEXT NOT NULL,
    -- 'user' | 'system' | 'ai_assistant'
  actor_id UUID,
    -- user_id if actor_type = 'user'

  -- Snapshot
  previous_status TEXT,
  new_status TEXT,
  details JSONB,

  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_task_activity_project ON task_activity_log(project_id, created_at DESC);
CREATE INDEX idx_task_activity_task ON task_activity_log(task_id, created_at DESC);
```

---

## Implementation Phases

### Phase 1: Database & Core Backend (Foundation)

| Task ID | Task | Depends On | Description |
|---------|------|------------|-------------|
| 1.1 | Create tasks migration | - | SQL migration for tasks + task_activity_log tables |
| 1.2 | Create tasks DB module | 1.1 | `app/db/tasks.py` with CRUD operations |
| 1.3 | Create tasks schemas | 1.1 | `app/core/schemas_tasks.py` with Pydantic models |
| 1.4 | Create tasks API routes | 1.2, 1.3 | `app/api/tasks.py` with REST endpoints |
| 1.5 | Add priority calculation | 1.2 | Helper function for hybrid priority scoring |

**API Endpoints (Phase 1):**
```
GET    /projects/{project_id}/tasks              # List tasks (with filters)
GET    /projects/{project_id}/tasks/{task_id}    # Get single task
POST   /projects/{project_id}/tasks              # Create task (manual)
PATCH  /projects/{project_id}/tasks/{task_id}    # Update task
DELETE /projects/{project_id}/tasks/{task_id}    # Delete/dismiss task
POST   /projects/{project_id}/tasks/{task_id}/complete   # Complete task
POST   /projects/{project_id}/tasks/{task_id}/dismiss    # Dismiss task
GET    /projects/{project_id}/tasks/activity     # Get activity log
```

---

### Phase 2: Task Source Integrations

| Task ID | Task | Depends On | Description |
|---------|------|------------|-------------|
| 2.1 | DI Agent → Tasks bridge | 1.4 | Create tasks from gap analysis |
| 2.2 | Signal processing → Tasks | 1.4 | Create tasks from proposals |
| 2.3 | Proposal approval → Task completion | 2.2 | Link proposal state to task state |
| 2.4 | Enrichment trigger → Tasks | 1.4 | Create tasks for enrichment needs |

**2.1 DI Agent Integration:**
```python
# In di_agent_tools.py or new bridge module
async def create_tasks_from_gaps(project_id: UUID, gaps: list[dict]) -> list[UUID]:
    """Create tasks for each unsatisfied gate gap."""
    task_ids = []
    for gap in gaps:
        if not gap["is_satisfied"]:
            task = await create_task(
                project_id=project_id,
                title=f"Fill {gap['gate']} gap",
                description=gap.get("reason", ""),
                task_type="gap",
                gate_stage=gap["gate"],
                source_type="di_agent",
                source_context=gap,
                requires_client_input=_gate_requires_client(gap["gate"]),
            )
            task_ids.append(task["id"])
    return task_ids
```

**2.2 Signal Processing Integration:**
```python
# In signal_pipeline.py or proposals module
async def create_tasks_from_proposals(project_id: UUID, proposals: list[dict]) -> list[UUID]:
    """Create tasks for each proposal."""
    task_ids = []
    for proposal in proposals:
        task = await create_task(
            project_id=project_id,
            title=proposal["title"],
            description=proposal.get("description", ""),
            task_type="proposal",
            anchored_entity_type=proposal["entity_type"],
            anchored_entity_id=proposal.get("entity_id"),
            source_type="signal_processing",
            source_id=proposal["id"],
            source_context={"proposal": proposal},
        )
        task_ids.append(task["id"])
    return task_ids
```

---

### Phase 3: AI Assistant Integration

| Task ID | Task | Depends On | Description |
|---------|------|------------|-------------|
| 3.1 | Add task tools to assistant | 1.4 | create_task, list_tasks, complete_task tools |
| 3.2 | Post-signal task surfacing | 2.2 | Show proposals as tasks in chat after processing |
| 3.3 | "Approve All" chat action | 3.2 | Batch approve proposals via chat |
| 3.4 | Manual task creation via chat | 3.1 | User can ask assistant to create tasks |

**3.1 Assistant Tools:**
```typescript
// In apps/workbench/lib/assistant/commands.ts
const taskCommands = {
  create_task: {
    description: "Create a new task",
    parameters: { title, description, task_type, anchored_to },
    execute: async (params) => { /* call API */ }
  },
  list_tasks: {
    description: "List pending tasks",
    parameters: { status, task_type },
    execute: async (params) => { /* call API */ }
  },
  complete_task: {
    description: "Mark task as complete",
    parameters: { task_id, notes },
    execute: async (params) => { /* call API */ }
  },
  approve_proposals: {
    description: "Approve all pending proposal tasks",
    parameters: { task_ids },
    execute: async (params) => { /* batch complete */ }
  }
};
```

**3.2-3.3 Post-Signal Flow:**
```typescript
// After signal processing completes
const proposals = result.proposals;
if (proposals.length > 0) {
  // Create tasks for proposals
  const taskIds = await createTasksFromProposals(projectId, proposals);

  // Show in chat
  return {
    message: `Found ${proposals.length} changes to review:`,
    proposals: proposals,
    actions: [
      { label: "Approve All", action: "approve_proposals", taskIds },
      { label: "Review as Tasks", action: "navigate", to: "overview" }
    ]
  };
}
```

---

### Phase 4: Frontend - Overview Tab

| Task ID | Task | Depends On | Description |
|---------|------|------------|-------------|
| 4.1 | Create TaskCard component | 1.4 | Reusable task display component |
| 4.2 | Create TaskList component | 4.1 | List of tasks with filters |
| 4.3 | Add tasks section to Overview | 4.2 | Integrate into OverviewTab |
| 4.4 | Add next actions preview to Overview | - | Summary of pending info_requests |
| 4.5 | Task quick actions | 4.1 | Complete/dismiss inline |

**4.1 TaskCard Component:**
```tsx
// apps/workbench/components/tasks/TaskCard.tsx
interface TaskCardProps {
  task: Task;
  onComplete: (taskId: string) => void;
  onDismiss: (taskId: string) => void;
  onNavigate?: (entityType: string, entityId: string) => void;
}

export function TaskCard({ task, onComplete, onDismiss, onNavigate }: TaskCardProps) {
  return (
    <div className="border rounded-lg p-4">
      <div className="flex items-start justify-between">
        <div>
          <span className="text-xs text-muted-foreground">{task.task_type}</span>
          <h4 className="font-medium">{task.title}</h4>
          {task.description && (
            <p className="text-sm text-muted-foreground">{task.description}</p>
          )}
          {task.anchored_entity_type && (
            <button onClick={() => onNavigate?.(task.anchored_entity_type, task.anchored_entity_id)}>
              View {task.anchored_entity_type}
            </button>
          )}
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="ghost" onClick={() => onDismiss(task.id)}>
            Dismiss
          </Button>
          <Button size="sm" onClick={() => onComplete(task.id)}>
            Complete
          </Button>
        </div>
      </div>
      <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
        <span>Priority: {task.priority_score}</span>
        {task.requires_client_input && <Badge>Client Input</Badge>}
      </div>
    </div>
  );
}
```

---

### Phase 5: Frontend - Collaboration Tab

| Task ID | Task | Depends On | Description |
|---------|------|------------|-------------|
| 5.1 | Rename NextStepsTab → CollaborationTab | - | File rename + tab label |
| 5.2 | Add client-relevant tasks section | 4.2 | Filtered task list in Collaboration |
| 5.3 | Reorganize info_requests display | - | Full next actions view |
| 5.4 | Add task → info_request conversion | 1.4 | Convert validation task to client question |

**5.1 Tab Rename:**
```
apps/workbench/app/projects/[projectId]/components/tabs/NextStepsTab.tsx
  → CollaborationTab.tsx

Update imports in page.tsx:
  - import { NextStepsTab } from './components/tabs/NextStepsTab'
  + import { CollaborationTab } from './components/tabs/CollaborationTab'

Update tab config:
  - { id: 'next-steps', label: 'Next Steps', ... }
  + { id: 'collaboration', label: 'Collaboration', ... }
```

**5.2 Client-Relevant Tasks:**
```tsx
// In CollaborationTab.tsx
const { data: clientTasks } = useQuery({
  queryKey: ['tasks', projectId, 'client-relevant'],
  queryFn: () => fetchTasks(projectId, { requires_client_input: true })
});

return (
  <div>
    {/* Client-Relevant Tasks */}
    <section>
      <h3>Pending Validation</h3>
      <TaskList
        tasks={clientTasks}
        onComplete={handleComplete}
        onConvertToQuestion={handleConvertToInfoRequest}
      />
    </section>

    {/* Info Requests (existing) */}
    <section>
      <h3>Discovery Questions</h3>
      <InfoRequestsList requests={infoRequests} />
    </section>
  </div>
);
```

---

### Phase 6: Polish & Integration

| Task ID | Task | Depends On | Description |
|---------|------|------------|-------------|
| 6.1 | Activity log UI | 1.4, 4.3 | Show task history in Overview |
| 6.2 | Task notifications | 4.3 | Toast/badge for new tasks |
| 6.3 | Bulk task operations | 4.2 | Select multiple, bulk complete/dismiss |
| 6.4 | Task search/filter | 4.2 | Filter by type, status, entity |
| 6.5 | Priority auto-recalculation | 1.5 | Update priorities when entities change |

---

## API Reference

### List Tasks
```
GET /projects/{project_id}/tasks
Query params:
  - status: pending|in_progress|completed|dismissed
  - task_type: proposal|gap|manual|enrichment|validation|research|collaboration
  - requires_client_input: true|false
  - anchored_entity_type: feature|persona|...
  - limit: number
  - offset: number
  - sort: priority_score|created_at|updated_at
  - order: asc|desc
```

### Create Task
```
POST /projects/{project_id}/tasks
Body:
{
  "title": "Review persona update",
  "description": "New pain point identified from client call",
  "task_type": "validation",
  "anchored_entity_type": "persona",
  "anchored_entity_id": "uuid",
  "requires_client_input": true,
  "metadata": {}
}
```

### Update Task
```
PATCH /projects/{project_id}/tasks/{task_id}
Body:
{
  "status": "in_progress",
  "description": "Updated description"
}
```

### Complete Task
```
POST /projects/{project_id}/tasks/{task_id}/complete
Body:
{
  "completion_method": "task_board",
  "completion_notes": "Verified with client"
}
```

### Dismiss Task
```
POST /projects/{project_id}/tasks/{task_id}/dismiss
Body:
{
  "reason": "Duplicate of another task"
}
```

---

## Priority Calculation

```python
GATE_MODIFIERS = {
    # Phase 1 - Prototype (higher priority)
    "core_pain": 1.5,
    "primary_persona": 1.4,
    "wow_moment": 1.3,
    "design_preferences": 1.1,
    # Phase 2 - Build (standard priority)
    "business_case": 1.0,
    "budget_constraints": 0.9,
    "full_requirements": 0.8,
    "confirmed_scope": 0.7,
}

def calculate_priority(task: Task, entity: Entity | None) -> float:
    # Base priority from entity or default
    if entity and hasattr(entity, 'priority_score'):
        base = entity.priority_score
    else:
        base = 50  # Default for project-level tasks

    # Apply gate modifier if applicable
    modifier = GATE_MODIFIERS.get(task.gate_stage, 1.0)

    # Boost for client-relevant tasks (they often block progress)
    if task.requires_client_input:
        modifier *= 1.1

    return round(base * modifier, 2)
```

---

## Migration Path

1. **No breaking changes** - Tasks is additive
2. **Existing proposals** - Continue working, tasks layer is optional at first
3. **Gradual adoption** - Can enable task creation from proposals incrementally
4. **Tab rename** - Simple rename, no functional change to info_requests

---

## Success Criteria

- [ ] Tasks can be created from DI Agent gaps
- [ ] Tasks can be created from signal processing proposals
- [ ] Tasks can be created manually (UI + AI assistant)
- [ ] Tasks appear in Overview tab (all tasks)
- [ ] Client-relevant tasks appear in Collaboration tab
- [ ] Next Actions (info_requests) preview in Overview
- [ ] Next Actions full view in Collaboration (renamed from Next Steps)
- [ ] "Approve All" works in AI assistant chat
- [ ] Priority correctly calculated using hybrid approach
- [ ] Activity log captures task lifecycle
