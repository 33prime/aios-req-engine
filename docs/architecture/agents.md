# LangGraph Agents

**Last Updated:** 2026-01-30

## Overview

AIOS uses LangGraph agents for complex AI reasoning tasks that require:
- Multi-step decision making
- Tool orchestration
- State management
- Conditional logic

## Core Agents

### 1. DI Agent (Design Intelligence Agent)
**Purpose:** Autonomous foundation building and gap analysis

**Location:** `app/agents/di_agent.py`

**Pattern:** OBSERVE → THINK → DECIDE → ACT

**Capabilities:**
- Gate status assessment
- Foundation gap identification
- Automatic data extraction (core pain, persona, wow moment)
- Research orchestration
- Consultant guidance generation

**Tools:**
- `extract_core_pain` - Extract core pain from signals
- `extract_primary_persona` - Identify primary persona
- `identify_wow_moment` - Find wow moment
- `extract_business_case` - Extract ROI and KPIs
- `extract_budget_constraints` - Extract budget/timeline
- `run_research` - Trigger research agent
- `analyze_gaps` - Identify requirements gaps

**State Machine:**
```
Start → Assess Gates → Identify Gaps → 
Choose Tool → Execute Tool → 
Update State → Provide Guidance → End
```

**Invocation:**
```python
from app.agents.di_agent import invoke_di_agent

response = await invoke_di_agent(
    project_id=project_id,
    trigger="manual_refresh",
    specific_request="Check foundation completeness"
)
```

**Logs:** Stored in `di_logs` table with full reasoning trace

**Cache:** Analysis cached in `di_cache` table, invalidated on data changes

### 2. Memory Agent
**Purpose:** Project memory synthesis and retrieval

**Location:** `app/agents/memory_agent.py`

**Capabilities:**
- Synthesize project decisions and learnings
- Build knowledge graph (facts → beliefs → insights)
- Detect contradictions
- Compact memory when > 2000 tokens

**Tools:**
- `get_project_memory` - Retrieve memory document
- `add_decision` - Add decision to memory
- `add_learning` - Add learning/insight
- `synthesize_memory` - Regenerate with LLM
- `compact_memory` - Compress via Haiku

**Memory Structure:**
```markdown
# Project Memory: [Project Name]

## Strategic Foundation
- Core pain, persona, wow moment

## Key Decisions
1. Decision with rationale
2. Another decision

## Learnings
- Insight from signals
- Pattern identified

## Open Questions
- Unresolved question
```

### 3. Research Agent
**Purpose:** Multi-source research and synthesis

**Location:** `app/agents/research/agent.py`

**Capabilities:**
- Query generation
- Source search (web, documents, internal signals)
- Content retrieval
- Chunk-level analysis
- Report synthesis

**Tools:**
- `web_search` - Search web via API
- `web_fetch` - Retrieve full pages
- `search_signals` - Search internal signals
- `extract_insights` - Analyze chunks

**Pipeline:**
```
Research Request → Generate Queries → 
Search Sources → Retrieve Content → 
Chunk Analysis → Synthesize Report
```

**Output:** Research report with citations

### 4. Stakeholder Suggester
**Purpose:** Identify stakeholders from signals

**Location:** `app/agents/stakeholder_suggester.py`

**Capabilities:**
- Parse signals for stakeholder mentions
- Extract role, influence level
- Suggest new stakeholder records

**Tools:**
- `extract_stakeholder_mentions` - NER for people
- `classify_stakeholder_role` - Determine role
- `assess_influence` - Estimate influence level

### 5. Discovery Prep Agents
**Purpose:** Prepare for discovery sessions

**Location:** `app/agents/discovery_prep/`

**Sub-Agents:**
- **Document Agent** - Analyzes uploaded documents
- **Question Agent** - Generates discovery questions
- **Agenda Agent** - Creates meeting agendas

**Tools:**
- `analyze_document` - Extract key topics
- `generate_questions` - Create targeted questions
- `build_agenda` - Structure meeting flow

## Agent Design Patterns

### 1. Tool Selection Pattern
```python
# Agent observes state
state = get_project_state(project_id)

# Agent decides which tool to use
if state.has_gap("core_pain"):
    tool = "extract_core_pain"
elif state.has_gap("persona"):
    tool = "extract_primary_persona"
    
# Agent executes tool
result = await execute_tool(tool, project_id)

# Agent updates state
update_foundation(project_id, result)
```

### 2. Multi-Step Reasoning Pattern
```python
# Step 1: Analyze
gaps = analyze_gaps(project_id)

# Step 2: Decide
if gaps["critical"] > 0:
    priority = "critical"
else:
    priority = "normal"

# Step 3: Act
if priority == "critical":
    result = await extract_foundation_data(project_id)
else:
    result = provide_guidance(gaps)
```

### 3. Conditional Branching Pattern
```python
def decide_next_step(state):
    if state.foundation_complete:
        return "analyze_solution"
    elif state.has_signals:
        return "extract_data"
    else:
        return "request_input"
        
next_step = decide_next_step(state)
result = await execute_step(next_step)
```

## Agent Configuration

**LLM Models:**
- **DI Agent:** Claude Sonnet 4 (reasoning + tool use)
- **Memory Agent:** Claude Sonnet 4 (synthesis), Haiku 3.5 (compaction)
- **Research Agent:** Claude Sonnet 4 (analysis + synthesis)

**Context Windows:**
- DI Agent: 200k tokens
- Memory Agent: 200k tokens (Sonnet), 100k (Haiku)
- Research Agent: 200k tokens

**Rate Limits:**
- Anthropic API: Tier-based (see core/llm.py)
- Caching enabled for repeated prompts

## Agent Monitoring

**Logs:**
- Full reasoning traces in `di_logs`
- Agent runs tracked in `agent_runs`
- Tool calls logged with inputs/outputs

**Metrics:**
- Invocation count
- Success rate
- Average execution time
- Tools called per run

**Observability:**
- LangSmith integration (optional)
- Structured logging in production

## Agent Extension

To add a new agent:

1. **Create agent file** in `app/agents/`
2. **Define tools** the agent can call
3. **Build state machine** for multi-step logic
4. **Add API endpoint** to invoke agent
5. **Create database tables** for logs/cache
6. **Write tests** for agent behavior

**Example Agent Structure:**
```python
from langchain.agents import AgentExecutor
from app.core.llm import get_llm

async def invoke_my_agent(project_id: UUID):
    # 1. Observe
    state = get_project_state(project_id)
    
    # 2. Think
    llm = get_llm("sonnet")
    analysis = await llm.ainvoke(
        f"Analyze this state: {state}"
    )
    
    # 3. Decide
    decision = parse_decision(analysis)
    
    # 4. Act
    if decision.action == "extract_data":
        result = await extract_data_tool(project_id)
    else:
        result = provide_guidance(decision)
    
    return result
```

---

**Agent Count:** 5 core agents  
**Tool Count:** 20+ tools across all agents  
**Average Execution:** 5-30 seconds per agent run
