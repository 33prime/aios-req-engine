# DI Agent API Reference

Complete API reference for Design Intelligence (DI) Agent endpoints.

**Base URL**: `http://localhost:8000` (development) or your production URL

**Authentication**: All endpoints require authentication (Bearer token or session cookie)

---

## Table of Contents

- [Agent Invocation](#agent-invocation)
- [Foundation Management](#foundation-management)
- [Foundation Extraction](#foundation-extraction)
- [Agent Logs](#agent-logs)
- [Cache Management](#cache-management)
- [Error Responses](#error-responses)
- [Rate Limits](#rate-limits)

---

## Agent Invocation

### Invoke DI Agent

**Endpoint**: `POST /projects/{project_id}/di-agent/invoke`

Invoke the Design Intelligence Agent to analyze project foundation and take action following the OBSERVE → THINK → DECIDE → ACT pattern.

#### Request

**Path Parameters:**
- `project_id` (UUID, required) - Project identifier

**Body:**
```json
{
  "trigger": "new_signal",
  "trigger_context": "Just finished discovery call with Sarah",
  "specific_request": null
}
```

**Body Parameters:**
- `trigger` (string, required) - What triggered this invocation
  - `"new_signal"` - After adding client conversation
  - `"user_request"` - Specific consultant question
  - `"scheduled"` - Periodic health check
  - `"pre_call"` - Prepare for upcoming meeting
- `trigger_context` (string, optional) - Additional context about the trigger
- `specific_request` (string, optional) - Specific consultant request (used with `user_request` trigger)

#### Response

**Status**: `200 OK`

```json
{
  "observation": "Project has core pain (confidence: 0.85) but primary persona is unclear. 5 unanalyzed signals available.",
  "thinking": "The biggest gap is understanding WHO feels this pain most acutely. Without primary persona, we cannot define wow moment.",
  "decision": "I will suggest discovery questions to identify THE primary persona with higher confidence.",
  "action_type": "guidance",
  "tools_called": null,
  "tool_results": null,
  "guidance": {
    "summary": "Need to identify THE primary persona",
    "questions_to_ask": [
      {
        "question": "Who on your team gets fired if this problem isn't solved?",
        "why_ask": "Identifies ownership and urgency",
        "listen_for": ["Job titles", "Pain intensity", "Current workarounds"]
      },
      {
        "question": "Walk me through a day in the life of the person who feels this pain most.",
        "why_ask": "Provides context and validates persona details",
        "listen_for": ["Daily workflows", "Frustration points", "Workarounds"]
      }
    ],
    "signals_to_watch": ["Persona roles", "Pain intensity", "Current behavior"],
    "what_this_unlocks": "Primary persona gate → wow moment identification"
  },
  "readiness_before": 25,
  "readiness_after": 25,
  "gates_affected": ["primary_persona"]
}
```

**Response Fields:**
- `observation` (string) - What the agent observed about current state
- `thinking` (string) - The agent's analysis of the biggest gap
- `decision` (string) - What the agent decided to do and why
- `action_type` (string) - Type of action taken:
  - `"tool_call"` - Agent executed extraction/analysis tools
  - `"guidance"` - Agent needs more signal, provides questions
  - `"stop"` - Agent completed work or needs consultant involvement
  - `"confirmation"` - Agent needs validation
- `tools_called` (array|null) - Tools that were called (if `action_type` = `"tool_call"`)
- `tool_results` (array|null) - Results from tool execution
- `guidance` (object|null) - Guidance for consultant (if `action_type` = `"guidance"`)
  - `summary` (string) - Summary of the situation
  - `questions_to_ask` (array) - Discovery questions to ask client
  - `signals_to_watch` (array) - What to listen for in responses
  - `what_this_unlocks` (string) - What getting this information will enable
- `readiness_before` (integer|null) - Readiness score before action (0-100)
- `readiness_after` (integer|null) - Readiness score after action (if changed)
- `gates_affected` (array) - Which gates were affected by this action

#### cURL Example

```bash
curl -X POST "http://localhost:8000/projects/123e4567-e89b-12d3-a456-426614174000/di-agent/invoke" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "trigger": "new_signal",
    "trigger_context": "Added discovery call transcript with Sarah (CSM lead)"
  }'
```

#### TypeScript Example

```typescript
interface InvokeDIAgentRequest {
  trigger: 'new_signal' | 'user_request' | 'scheduled' | 'pre_call';
  trigger_context?: string;
  specific_request?: string;
}

interface InvokeDIAgentResponse {
  observation: string;
  thinking: string;
  decision: string;
  action_type: 'tool_call' | 'guidance' | 'stop' | 'confirmation';
  tools_called?: Array<{
    tool_name: string;
    tool_args: Record<string, any>;
    result?: any;
    success: boolean;
  }>;
  guidance?: {
    summary: string;
    questions_to_ask: Array<{
      question: string;
      why_ask: string;
      listen_for: string[];
    }>;
    signals_to_watch: string[];
    what_this_unlocks: string;
  };
  readiness_before?: number;
  readiness_after?: number;
  gates_affected?: string[];
}

async function invokeDIAgent(
  projectId: string,
  request: InvokeDIAgentRequest
): Promise<InvokeDIAgentResponse> {
  const response = await fetch(
    `http://localhost:8000/projects/${projectId}/di-agent/invoke`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${YOUR_TOKEN}`
      },
      body: JSON.stringify(request)
    }
  );

  if (!response.ok) {
    throw new Error(`DI Agent invocation failed: ${response.statusText}`);
  }

  return response.json();
}

// Example usage
const result = await invokeDIAgent(
  '123e4567-e89b-12d3-a456-426614174000',
  {
    trigger: 'new_signal',
    trigger_context: 'Added discovery call transcript'
  }
);

if (result.action_type === 'guidance') {
  console.log('Questions to ask client:');
  result.guidance?.questions_to_ask.forEach(q => {
    console.log(`- ${q.question}`);
  });
}
```

---

## Foundation Management

### Get Complete Foundation

**Endpoint**: `GET /projects/{project_id}/foundation`

Retrieve all foundation gate elements for a project.

#### Request

**Path Parameters:**
- `project_id` (UUID, required) - Project identifier

#### Response

**Status**: `200 OK`

```json
{
  "project_id": "123e4567-e89b-12d3-a456-426614174000",
  "core_pain": {
    "statement": "Customer success teams spend 10+ hours per week manually tracking churn risk",
    "trigger": "When a customer stops engaging",
    "stakes": "We lose $50K-200K MRR per month from preventable churn",
    "who_feels_it": "Customer Success Managers",
    "confidence": 0.85,
    "confirmed_by": "client"
  },
  "primary_persona": {
    "name": "Sarah Chen",
    "role": "Customer Success Manager",
    "goal": "Prevent customer churn proactively",
    "pain_connection": "Manually tracks 50+ accounts, misses early warning signs",
    "context": "Manages enterprise accounts worth $2M+ ARR",
    "confidence": 0.8,
    "confirmed_by": "consultant"
  },
  "wow_moment": {
    "description": "Sarah opens dashboard Monday morning and instantly sees which 3 accounts need attention",
    "core_pain_inversion": "From 'manual spreadsheet panic' to 'confident prioritization in 30 seconds'",
    "emotional_impact": "Relief, control, confidence",
    "visual_concept": "Clean dashboard with 3 red-flagged accounts",
    "level_1_core": "See churn risk instantly",
    "level_2_adjacent": "Know WHY they're at risk",
    "level_3_unstated": "Get AI-suggested rescue actions",
    "confidence": 0.75,
    "confirmed_by": null
  },
  "design_preferences": {
    "style": "Clean, data-dense like Stripe",
    "references": ["Stripe Dashboard", "Linear"],
    "confidence": 0.6
  },
  "business_case": null,
  "budget_constraints": null,
  "confirmed_scope": null,
  "created_at": "2025-01-20T10:00:00Z",
  "updated_at": "2025-01-24T15:30:00Z"
}
```

**Status**: `404 Not Found` - Foundation not yet created for this project

```json
{
  "detail": "Foundation not found for this project"
}
```

#### cURL Example

```bash
curl -X GET "http://localhost:8000/projects/123e4567-e89b-12d3-a456-426614174000/foundation" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### TypeScript Example

```typescript
interface ProjectFoundation {
  project_id: string;
  core_pain?: CorePain;
  primary_persona?: PrimaryPersona;
  wow_moment?: WowMoment;
  design_preferences?: DesignPreferences;
  business_case?: BusinessCase;
  budget_constraints?: BudgetConstraints;
  confirmed_scope?: ConfirmedScope;
  created_at: string;
  updated_at: string;
}

async function getFoundation(projectId: string): Promise<ProjectFoundation> {
  const response = await fetch(
    `http://localhost:8000/projects/${projectId}/foundation`,
    {
      headers: {
        'Authorization': `Bearer ${YOUR_TOKEN}`
      }
    }
  );

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('Foundation not yet created for this project');
    }
    throw new Error(`Failed to get foundation: ${response.statusText}`);
  }

  return response.json();
}
```

---

## Foundation Extraction

Individual extraction endpoints for targeted foundation element extraction.

### Extract Core Pain

**Endpoint**: `POST /projects/{project_id}/foundation/extract-core-pain`

Extract THE singular core pain from project signals.

#### Request

**Path Parameters:**
- `project_id` (UUID, required) - Project identifier

**Body**: Empty (no request body required)

#### Response

**Status**: `200 OK`

```json
{
  "statement": "Customer success teams spend 10+ hours per week manually tracking churn risk indicators across disconnected tools",
  "confidence": 0.85,
  "trigger": "When a customer stops engaging but no alert fires",
  "stakes": "We lose $50K-200K MRR per month from preventable churn",
  "who_feels_it": "Customer Success Managers",
  "confirmed_by": "client"
}
```

**Response Fields:**
- `statement` (string, min 20 chars) - Clear problem description (root cause, not symptom)
- `confidence` (number, 0.0-1.0) - Extraction confidence score
  - `< 0.5` - Very uncertain, needs validation
  - `0.5-0.7` - Moderate, get more signal
  - `0.7-0.85` - High confidence
  - `> 0.85` - Very high, client-confirmed
- `trigger` (string|null) - What causes this pain? Why now?
- `stakes` (string|null) - What happens if unsolved?
- `who_feels_it` (string|null) - Specific role experiencing pain
- `confirmed_by` (string|null) - Authority: `"client"`, `"consultant"`, or null

#### cURL Example

```bash
curl -X POST "http://localhost:8000/projects/123e4567-e89b-12d3-a456-426614174000/foundation/extract-core-pain" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### Extract Primary Persona

**Endpoint**: `POST /projects/{project_id}/foundation/extract-primary-persona`

Identify THE primary persona who feels the core pain most.

#### Request

**Path Parameters:**
- `project_id` (UUID, required) - Project identifier

**Body**: Empty

#### Response

**Status**: `200 OK`

```json
{
  "name": "Sarah Chen",
  "role": "Customer Success Manager",
  "confidence": 0.8,
  "context": "Manages 50+ enterprise accounts worth $2M+ ARR, under pressure to reduce churn",
  "pain_experienced": "Manually tracks churn risk in spreadsheets, misses early warning signs",
  "current_behavior": "Checks Salesforce, Intercom, and Google Sheets daily to track engagement",
  "desired_outcome": "Proactively identify at-risk accounts before churn happens",
  "confirmed_by": "consultant"
}
```

**Response Fields:**
- `name` (string) - Specific person name (can be role if name unknown)
- `role` (string) - Job title
- `confidence` (number, 0.0-1.0) - Extraction confidence
- `context` (string|null) - Daily work context
- `pain_experienced` (string|null) - How they experience the core pain
- `current_behavior` (string|null) - How they handle it today
- `desired_outcome` (string|null) - What success looks like
- `confirmed_by` (string|null) - Authority: `"client"`, `"consultant"`, or null

#### cURL Example

```bash
curl -X POST "http://localhost:8000/projects/123e4567-e89b-12d3-a456-426614174000/foundation/extract-primary-persona" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### Identify Wow Moment

**Endpoint**: `POST /projects/{project_id}/foundation/identify-wow-moment`

Identify THE wow moment where pain inverts to delight.

#### Request

**Path Parameters:**
- `project_id` (UUID, required) - Project identifier

**Body**: Empty

#### Response

**Status**: `200 OK`

```json
{
  "description": "Sarah opens the dashboard Monday morning and instantly sees which 3 accounts need attention this week, ranked by churn risk with AI-suggested actions",
  "confidence": 0.75,
  "trigger_event": "Opening dashboard on Monday morning",
  "emotional_response": "Relief, control, confidence instead of panic",
  "level_1_core": "See churn risk instantly (solves core pain)",
  "level_2_adjacent": "Know WHY they're at risk (context)",
  "level_3_unstated": "Get AI-suggested rescue actions (intelligence)",
  "confirmed_by": null
}
```

**Response Fields:**
- `description` (string) - The moment itself
- `confidence` (number, 0.0-1.0) - Identification confidence
- `trigger_event` (string|null) - What causes the wow moment
- `emotional_response` (string|null) - What the persona feels
- `level_1_core` (string|null) - Core pain solved
- `level_2_adjacent` (string|null) - Adjacent pains addressed
- `level_3_unstated` (string|null) - Unstated needs met
- `confirmed_by` (string|null) - Authority: `"client"`, `"consultant"`, or null

**Confidence Threshold**: Wow moment requires ≥ 0.5 confidence (hypothesis-level, validated with prototype)

#### cURL Example

```bash
curl -X POST "http://localhost:8000/projects/123e4567-e89b-12d3-a456-426614174000/foundation/identify-wow-moment" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### Extract Business Case

**Endpoint**: `POST /projects/{project_id}/foundation/extract-business-case`

Extract business value, ROI, KPIs, and priority from signals.

#### Request

**Path Parameters:**
- `project_id` (UUID, required) - Project identifier

**Body**: Empty

#### Response

**Status**: `200 OK`

```json
{
  "value_to_business": "Reduce customer churn by 15% through proactive intervention",
  "roi_framing": "$2.4M ARR saved annually vs $200K implementation cost = 12x ROI in year 1",
  "why_priority": "Churn is #1 threat to growth targets. Q2 board presentation requires solution",
  "confidence": 0.85,
  "success_kpis": [
    {
      "metric": "Customer retention rate",
      "target": "↑ 15%",
      "timeframe": "6 months",
      "measurement": "90-day retention cohorts"
    },
    {
      "metric": "Time to identify at-risk accounts",
      "target": "< 1 day",
      "timeframe": "immediate",
      "measurement": "Days from disengagement to alert"
    }
  ],
  "confirmed_by": "client"
}
```

**Response Fields:**
- `value_to_business` (string) - Quantified business impact
- `roi_framing` (string) - How they'll measure ROI
- `why_priority` (string) - Why now vs other initiatives
- `confidence` (number, 0.0-1.0) - Extraction confidence
- `success_kpis` (array) - ≥1 KPI required for satisfaction
  - `metric` (string) - What to measure
  - `target` (string) - Success target
  - `timeframe` (string) - When to measure
  - `measurement` (string) - How to measure
- `confirmed_by` (string|null) - Authority: `"client"`, `"consultant"`, or null

**Note**: Business case often unlocks AFTER prototype when client can articulate value concretely.

#### cURL Example

```bash
curl -X POST "http://localhost:8000/projects/123e4567-e89b-12d3-a456-426614174000/foundation/extract-business-case" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### Extract Budget & Constraints

**Endpoint**: `POST /projects/{project_id}/foundation/extract-budget-constraints`

Extract budget range, timeline, and technical/organizational constraints.

#### Request

**Path Parameters:**
- `project_id` (UUID, required) - Project identifier

**Body**: Empty

#### Response

**Status**: `200 OK`

```json
{
  "budget_range": "$100K-150K",
  "budget_flexibility": "Can flex to $175K if ROI justifies",
  "timeline": "Must launch MVP by end of Q2 (June 30)",
  "confidence": 0.8,
  "hard_deadline": "2025-06-30",
  "deadline_driver": "Q2 board presentation needs progress demo",
  "technical_constraints": [
    "Must integrate with Salesforce",
    "Use existing AWS infrastructure",
    "Cannot access customer PII directly"
  ],
  "organizational_constraints": [
    "Only 1 backend dev available until April",
    "Must get security review before launch",
    "CSM team has limited time for testing"
  ],
  "confirmed_by": "client"
}
```

**Response Fields:**
- `budget_range` (string) - Budget ballpark (not exact)
- `budget_flexibility` (string) - How firm is the number
- `timeline` (string) - Timeline expectations
- `confidence` (number, 0.0-1.0) - Extraction confidence
- `hard_deadline` (string|null) - External deadline (ISO 8601 date)
- `deadline_driver` (string|null) - Why the deadline exists
- `technical_constraints` (array) - Technology limitations
- `organizational_constraints` (array) - People/process limitations
- `confirmed_by` (string|null) - Authority: `"client"`, `"consultant"`, or null

**Note**: Budget/constraints often unlock AFTER prototype. Don't push for this on discovery call #1.

#### cURL Example

```bash
curl -X POST "http://localhost:8000/projects/123e4567-e89b-12d3-a456-426614174000/foundation/extract-budget-constraints" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Agent Logs

### Get DI Agent Logs

**Endpoint**: `GET /projects/{project_id}/di-agent/logs`

Retrieve paginated DI Agent reasoning logs with full OBSERVE → THINK → DECIDE → ACT traces.

#### Request

**Path Parameters:**
- `project_id` (UUID, required) - Project identifier

**Query Parameters:**
- `limit` (integer, optional, 1-100, default: 50) - Maximum logs to return
- `offset` (integer, optional, ≥0, default: 0) - Number of logs to skip
- `trigger` (string, optional) - Filter by trigger type (`"new_signal"`, `"user_request"`, etc.)
- `action_type` (string, optional) - Filter by action type (`"tool_call"`, `"guidance"`, etc.)
- `success_only` (boolean, optional, default: false) - Only return successful invocations

#### Response

**Status**: `200 OK`

```json
{
  "logs": [
    {
      "id": "log-uuid",
      "project_id": "123e4567-e89b-12d3-a456-426614174000",
      "trigger": "new_signal",
      "trigger_context": "Added discovery call transcript",
      "observation": "Project has core pain (0.85) but primary persona unclear...",
      "thinking": "Biggest gap is identifying WHO feels pain most...",
      "decision": "Suggest discovery questions to identify primary persona",
      "action_type": "guidance",
      "tools_called": null,
      "guidance_provided": {
        "summary": "Need to identify THE primary persona",
        "questions_to_ask": [...]
      },
      "readiness_before": 25,
      "readiness_after": 25,
      "gates_affected": ["primary_persona"],
      "execution_time_ms": 2340,
      "created_at": "2025-01-24T15:30:00Z"
    }
  ],
  "total": 1
}
```

**Response Fields:**
- `logs` (array) - Array of log entries
  - `id` (string) - Log entry UUID
  - `project_id` (string) - Project UUID
  - `trigger` (string) - What triggered invocation
  - `trigger_context` (string|null) - Additional context
  - `observation` (string) - Agent's observation
  - `thinking` (string) - Agent's analysis
  - `decision` (string) - Agent's decision
  - `action_type` (string) - Action taken
  - `tools_called` (array|null) - Tools executed
  - `guidance_provided` (object|null) - Guidance given
  - `readiness_before` (integer|null) - Score before action
  - `readiness_after` (integer|null) - Score after action
  - `gates_affected` (array) - Affected gates
  - `execution_time_ms` (integer) - Execution time in milliseconds
  - `created_at` (string) - Timestamp
- `total` (integer) - Total number of logs returned

#### cURL Example

```bash
# Get latest 10 logs
curl -X GET "http://localhost:8000/projects/123e4567-e89b-12d3-a456-426614174000/di-agent/logs?limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get logs filtered by trigger type
curl -X GET "http://localhost:8000/projects/123e4567-e89b-12d3-a456-426614174000/di-agent/logs?trigger=new_signal&limit=20" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get only successful guidance actions
curl -X GET "http://localhost:8000/projects/123e4567-e89b-12d3-a456-426614174000/di-agent/logs?action_type=guidance&success_only=true" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### TypeScript Example

```typescript
interface DIAgentLog {
  id: string;
  project_id: string;
  trigger: string;
  observation: string;
  thinking: string;
  decision: string;
  action_type: string;
  readiness_before?: number;
  readiness_after?: number;
  execution_time_ms: number;
  created_at: string;
}

interface DIAgentLogsResponse {
  logs: DIAgentLog[];
  total: number;
}

async function getAgentLogs(
  projectId: string,
  options: {
    limit?: number;
    offset?: number;
    trigger?: string;
    actionType?: string;
    successOnly?: boolean;
  } = {}
): Promise<DIAgentLogsResponse> {
  const params = new URLSearchParams();
  if (options.limit) params.set('limit', options.limit.toString());
  if (options.offset) params.set('offset', options.offset.toString());
  if (options.trigger) params.set('trigger', options.trigger);
  if (options.actionType) params.set('action_type', options.actionType);
  if (options.successOnly) params.set('success_only', 'true');

  const response = await fetch(
    `http://localhost:8000/projects/${projectId}/di-agent/logs?${params}`,
    {
      headers: {
        'Authorization': `Bearer ${YOUR_TOKEN}`
      }
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to get agent logs: ${response.statusText}`);
  }

  return response.json();
}
```

---

## Cache Management

### Invalidate DI Cache

**Endpoint**: `POST /projects/{project_id}/di-cache/invalidate`

Force the DI Agent to re-analyze the project on next invocation by invalidating the analysis cache.

#### Request

**Path Parameters:**
- `project_id` (UUID, required) - Project identifier

**Query Parameters:**
- `reason` (string, required) - Reason for cache invalidation

#### Response

**Status**: `200 OK`

```json
{
  "success": true,
  "message": "DI cache invalidated: Major signal update - re-run full analysis"
}
```

**Response Fields:**
- `success` (boolean) - Whether invalidation succeeded
- `message` (string) - Confirmation message with reason

#### cURL Example

```bash
curl -X POST "http://localhost:8000/projects/123e4567-e89b-12d3-a456-426614174000/di-cache/invalidate?reason=Major%20signal%20update" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### TypeScript Example

```typescript
interface InvalidateCacheResponse {
  success: boolean;
  message: string;
}

async function invalidateDICache(
  projectId: string,
  reason: string
): Promise<InvalidateCacheResponse> {
  const response = await fetch(
    `http://localhost:8000/projects/${projectId}/di-cache/invalidate?reason=${encodeURIComponent(reason)}`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${YOUR_TOKEN}`
      }
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to invalidate cache: ${response.statusText}`);
  }

  return response.json();
}

// Example usage
await invalidateDICache(
  '123e4567-e89b-12d3-a456-426614174000',
  'Re-extracted core pain with higher confidence'
);
```

**Common Invalidation Reasons:**
- `"Major signal update"` - Added significant new information
- `"Core pain re-extracted"` - Foundation element changed
- `"Manual refresh requested"` - Consultant wants fresh analysis
- `"Phase transition"` - Moved from prototype to build phase

---

## Error Responses

All endpoints return consistent error responses.

### 400 Bad Request

Invalid request parameters or malformed request body.

```json
{
  "detail": "Invalid trigger type. Must be one of: new_signal, user_request, scheduled, pre_call"
}
```

**Common Causes:**
- Invalid UUID format for `project_id`
- Invalid enum value (e.g., unknown trigger type)
- Missing required fields
- Invalid data types

### 404 Not Found

Resource not found.

```json
{
  "detail": "Foundation not found for this project"
}
```

**Common Causes:**
- Project doesn't exist
- Foundation not yet created for project
- Agent logs not found

### 500 Internal Server Error

Server-side error during processing.

```json
{
  "detail": "Failed to invoke DI Agent: LLM API timeout"
}
```

**Common Causes:**
- LLM API error (OpenAI/Anthropic timeout or rate limit)
- Extraction failed (insufficient signal)
- Database connection error
- Unexpected exception during processing

**Error Handling Best Practices:**

```typescript
async function invokeDIAgentWithRetry(
  projectId: string,
  request: InvokeDIAgentRequest,
  maxRetries: number = 3
): Promise<InvokeDIAgentResponse> {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await invokeDIAgent(projectId, request);
    } catch (error) {
      if (error.status === 400 || error.status === 404) {
        // Don't retry client errors
        throw error;
      }

      if (attempt === maxRetries) {
        throw error;
      }

      // Exponential backoff
      await new Promise(resolve =>
        setTimeout(resolve, Math.pow(2, attempt) * 1000)
      );
    }
  }
}
```

---

## Rate Limits

### Current Limits

**DI Agent Invocation**:
- **Limit**: No hard limit currently enforced
- **Recommendation**: Limit to 1 invocation per project per minute
- **Reason**: LLM calls are expensive; allow time for signal accumulation

**Foundation Extraction**:
- **Limit**: No hard limit currently enforced
- **Recommendation**: Avoid rapid re-extraction (< 5 minutes apart)
- **Reason**: Extraction results are cached; rapid calls won't yield new insights

**Agent Logs**:
- **Limit**: No hard limit
- **Max Results**: 100 logs per request (use pagination for more)

### Rate Limit Headers

Rate limit information is not currently included in response headers. Future versions may include:

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1643040000
```

### Best Practices

1. **Batch Signal Addition**: Add multiple signals, then invoke agent once
2. **Cache Awareness**: Check if foundation exists before extracting
3. **Trigger Appropriately**: Use `"new_signal"` trigger only after meaningful signal addition
4. **Respect Extraction Timing**: Don't re-extract within 5 minutes unless foundation changed
5. **Log Pagination**: Use `limit` and `offset` for large log collections

---

## Workflow Examples

### Complete Discovery Workflow

```typescript
// 1. Add discovery call signals
await addSignal(projectId, {
  signal_type: 'transcript',
  content: discoveryCallTranscript
});

// 2. Invoke DI Agent to analyze
const agentResponse = await invokeDIAgent(projectId, {
  trigger: 'new_signal',
  trigger_context: 'Added discovery call transcript with CSM lead'
});

// 3. If agent provides guidance, prepare for next call
if (agentResponse.action_type === 'guidance') {
  const questions = agentResponse.guidance.questions_to_ask;
  console.log('Ask client these questions:');
  questions.forEach(q => console.log(`- ${q.question}`));
}

// 4. After next call, add more signals and re-invoke
await addSignal(projectId, {
  signal_type: 'email',
  content: clientFollowUpEmail
});

const secondResponse = await invokeDIAgent(projectId, {
  trigger: 'new_signal',
  trigger_context: 'Client follow-up email with persona details'
});

// 5. Check if persona extracted
if (secondResponse.action_type === 'tool_call') {
  const foundation = await getFoundation(projectId);
  if (foundation.primary_persona) {
    console.log(`Primary Persona: ${foundation.primary_persona.name}`);
  }
}

// 6. Review agent reasoning history
const logs = await getAgentLogs(projectId, { limit: 10 });
logs.logs.forEach(log => {
  console.log(`${log.created_at}: ${log.action_type} - ${log.decision}`);
});
```

### Pre-Call Preparation Workflow

```typescript
// Before client call, invoke agent for guidance
const prepResponse = await invokeDIAgent(projectId, {
  trigger: 'pre_call',
  trigger_context: 'Client call in 30 minutes - Sarah (CSM lead)'
});

// Agent analyzes gaps and suggests questions
if (prepResponse.action_type === 'guidance') {
  const prep = prepResponse.guidance;

  console.log('Call Preparation:');
  console.log(`\nSituation: ${prep.summary}`);
  console.log('\nQuestions to ask:');
  prep.questions_to_ask.forEach((q, i) => {
    console.log(`\n${i + 1}. ${q.question}`);
    console.log(`   Why: ${q.why_ask}`);
    console.log(`   Listen for: ${q.listen_for.join(', ')}`);
  });
  console.log(`\nThis unlocks: ${prep.what_this_unlocks}`);
}
```

### Foundation Review Workflow

```typescript
// Get complete foundation
const foundation = await getFoundation(projectId);

// Check gate satisfaction
const gates = [
  { name: 'Core Pain', data: foundation.core_pain, threshold: 0.6 },
  { name: 'Primary Persona', data: foundation.primary_persona, threshold: 0.6 },
  { name: 'Wow Moment', data: foundation.wow_moment, threshold: 0.5 }
];

gates.forEach(gate => {
  if (!gate.data) {
    console.log(`❌ ${gate.name}: Not extracted`);
  } else if (gate.data.confidence < gate.threshold) {
    console.log(`⚠️  ${gate.name}: Low confidence (${gate.data.confidence})`);
  } else {
    console.log(`✅ ${gate.name}: Satisfied (${gate.data.confidence})`);
  }
});

// If gates unsatisfied, invoke agent for next steps
if (!foundation.core_pain || foundation.core_pain.confidence < 0.6) {
  const response = await invokeDIAgent(projectId, {
    trigger: 'user_request',
    specific_request: 'What do I need to satisfy core pain gate?'
  });

  console.log('\nAgent recommendation:');
  console.log(response.decision);
}
```

---

## Additional Resources

- **[DI Agent Guide](DI_AGENT_GUIDE.md)** - Complete conceptual guide
- **[OpenAPI Schema](http://localhost:8000/docs)** - Interactive API documentation (Swagger UI)
- **[OpenAPI JSON](http://localhost:8000/openapi.json)** - Machine-readable API specification

---

## Support

For issues or questions:
- **GitHub Issues**: [Report bugs or feature requests](https://github.com/your-org/aios-req-engine/issues)
- **API Docs**: Visit `/docs` endpoint on your running server for interactive testing

---

**Last Updated**: January 2025
**API Version**: 1.0
**Service**: aios-req-engine
