# Memory Agent Design: Knowledge Graph with Markdown View

## Design Philosophy

**Extend, don't replace.** Your existing memory tables are solid. We add a knowledge graph layer underneath that powers better reasoning, while markdown remains the human-readable view.

**Accuracy over speed.** Memory updates batch naturally (after signals, after DI actions). No real-time streaming needed.

**Facts vs Beliefs.** Inspired by Hindsight architecture - facts are immutable observations, beliefs are evolving interpretations that the system can update as it learns more.

---

## Architecture Overview

```
                    ┌─────────────────────────────────────┐
                    │         MARKDOWN VIEW               │
                    │   (Human-readable, what exists)     │
                    │                                     │
                    │   Rendered from graph on-demand     │
                    └──────────────────┬──────────────────┘
                                       │
                                       │ render()
                                       │
┌──────────────────────────────────────┴──────────────────────────────────────┐
│                          KNOWLEDGE GRAPH CORE                                │
│                                                                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │     FACTS       │    │    BELIEFS      │    │    INSIGHTS     │         │
│  │   (Immutable)   │    │   (Evolving)    │    │   (Generated)   │         │
│  │                 │    │                 │    │                 │         │
│  │ - Signal said X │    │ - We think Y    │    │ - Pattern: Z    │         │
│  │ - Client is ABC │    │ - Priority is P │    │ - Prediction: W │         │
│  │ - Feature named │    │ - Pain point Q  │    │ - Risk: R       │         │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘         │
│           │                      │                      │                   │
│           └──────────────────────┴──────────────────────┘                   │
│                                  │                                          │
│                          ┌───────┴───────┐                                  │
│                          │    EDGES      │                                  │
│                          │ (Connections) │                                  │
│                          │               │                                  │
│                          │ supports      │                                  │
│                          │ contradicts   │                                  │
│                          │ caused_by     │                                  │
│                          │ leads_to      │                                  │
│                          │ supersedes    │                                  │
│                          └───────────────┘                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ process()
                                       │
                    ┌──────────────────┴──────────────────┐
                    │          MEMORY AGENT               │
                    │                                     │
                    │  Watcher (Haiku) → Synthesizer     │
                    │  (Sonnet) → Reflector (Sonnet)     │
                    └─────────────────────────────────────┘
```

---

## Database Schema (Migration 0088)

```sql
-- =============================================================================
-- Knowledge Graph: Nodes
-- =============================================================================
-- The fundamental unit of memory - a discrete piece of knowledge

CREATE TABLE IF NOT EXISTS memory_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Node classification
    node_type TEXT NOT NULL,  -- 'fact', 'belief', 'insight', 'decision', 'learning'

    -- Content
    content TEXT NOT NULL,           -- The knowledge itself
    summary TEXT,                    -- One-line summary for graph views

    -- For beliefs: confidence and evolution
    confidence FLOAT DEFAULT 1.0,    -- 1.0 for facts, 0.0-1.0 for beliefs
    is_active BOOLEAN DEFAULT TRUE,  -- Beliefs can be superseded

    -- Source attribution
    source_type TEXT,                -- 'signal', 'agent', 'user', 'synthesis'
    source_id UUID,                  -- Link to signal, di_agent_log, etc.

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_memory_nodes_project ON memory_nodes(project_id);
CREATE INDEX idx_memory_nodes_type ON memory_nodes(project_id, node_type);
CREATE INDEX idx_memory_nodes_active ON memory_nodes(project_id, is_active);

-- =============================================================================
-- Knowledge Graph: Edges
-- =============================================================================
-- Relationships between nodes - this is where the graph magic happens

CREATE TABLE IF NOT EXISTS memory_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Edge endpoints
    from_node_id UUID NOT NULL REFERENCES memory_nodes(id) ON DELETE CASCADE,
    to_node_id UUID NOT NULL REFERENCES memory_nodes(id) ON DELETE CASCADE,

    -- Relationship type
    edge_type TEXT NOT NULL,  -- 'supports', 'contradicts', 'caused_by', 'leads_to', 'supersedes', 'related_to'

    -- Strength (for weighted graph operations)
    strength FLOAT DEFAULT 1.0,  -- How strong is this connection?

    -- Optional explanation
    rationale TEXT,  -- Why does this connection exist?

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Prevent duplicate edges
    UNIQUE(from_node_id, to_node_id, edge_type)
);

CREATE INDEX idx_memory_edges_project ON memory_edges(project_id);
CREATE INDEX idx_memory_edges_from ON memory_edges(from_node_id);
CREATE INDEX idx_memory_edges_to ON memory_edges(to_node_id);
CREATE INDEX idx_memory_edges_type ON memory_edges(edge_type);

-- =============================================================================
-- Belief Evolution History
-- =============================================================================
-- Track how beliefs change over time (the "why" of evolution)

CREATE TABLE IF NOT EXISTS belief_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id UUID NOT NULL REFERENCES memory_nodes(id) ON DELETE CASCADE,

    -- What changed
    previous_content TEXT,
    previous_confidence FLOAT,
    new_content TEXT,
    new_confidence FLOAT,

    -- Why it changed
    change_reason TEXT NOT NULL,
    triggered_by_node_id UUID REFERENCES memory_nodes(id),  -- What fact/signal caused this change?

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_belief_history_node ON belief_history(node_id);

-- =============================================================================
-- Memory Synthesis Log
-- =============================================================================
-- Track when synthesis runs and what it produced

CREATE TABLE IF NOT EXISTS memory_synthesis_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- What triggered synthesis
    trigger_type TEXT NOT NULL,  -- 'watcher_threshold', 'scheduled', 'manual'
    trigger_details JSONB DEFAULT '{}',

    -- What was processed
    nodes_processed INTEGER DEFAULT 0,
    edges_created INTEGER DEFAULT 0,
    beliefs_updated INTEGER DEFAULT 0,
    insights_generated INTEGER DEFAULT 0,

    -- Token usage (for cost tracking)
    tokens_used INTEGER DEFAULT 0,
    model_used TEXT,

    -- Timing
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_ms INTEGER
);

CREATE INDEX idx_synthesis_log_project ON memory_synthesis_log(project_id);

-- =============================================================================
-- Comments
-- =============================================================================

COMMENT ON TABLE memory_nodes IS 'Knowledge graph nodes - facts, beliefs, insights, decisions';
COMMENT ON TABLE memory_edges IS 'Relationships between nodes - supports, contradicts, caused_by, etc.';
COMMENT ON TABLE belief_history IS 'Audit trail of how beliefs evolve over time';
COMMENT ON COLUMN memory_nodes.node_type IS 'fact=immutable observation, belief=evolving interpretation, insight=generated pattern';
COMMENT ON COLUMN memory_edges.edge_type IS 'supports=evidence for, contradicts=evidence against, caused_by=causal chain, leads_to=consequence, supersedes=replaces';
```

---

## Token Budget Strategy

### Context Budget: 4000 tokens for memory

| Component | Tokens | Notes |
|-----------|--------|-------|
| Active beliefs | 1200 | Current understanding (~15 beliefs at 80 tokens each) |
| Recent facts | 800 | Last 10 facts with context |
| Key insights | 600 | Top 5 strategic insights |
| Active decisions | 400 | Last 5 decisions (summaries) |
| Mistakes to avoid | 400 | Top 3 mistakes |
| Connection summary | 600 | Key relationships between above |

### Compaction Strategy

**Unchanged trigger**: Still compact when markdown view > 2000 tokens

**New compaction behavior**:
1. Facts are NEVER deleted (but can be marked as "absorbed" into beliefs)
2. Beliefs with low confidence AND no recent edges get archived
3. Insights older than 30 days with no application get archived
4. Edges to archived nodes get removed
5. Markdown is regenerated from active nodes

**Landmark protection** (same as before):
- Decisions with `is_landmark=true` are never compacted
- Facts that support landmarks are protected
- Beliefs with confidence > 0.9 are protected

---

## Node Types Explained

### Facts (Immutable)
```python
{
    "node_type": "fact",
    "content": "Client CTO Sarah mentioned 'compliance deadline in Q2' in email on 2025-01-15",
    "summary": "Q2 compliance deadline mentioned",
    "confidence": 1.0,  # Facts are always 1.0
    "source_type": "signal",
    "source_id": "<signal_uuid>"
}
```

Facts are direct observations - what was said, what happened. Never modified, only archived.

### Beliefs (Evolving)
```python
{
    "node_type": "belief",
    "content": "The primary business driver is regulatory compliance, not user experience. Evidence: 3 signals mention compliance deadlines, 0 signals mention UX goals.",
    "summary": "Primary driver: compliance",
    "confidence": 0.85,  # Can change as evidence accumulates
    "source_type": "synthesis",
    "source_id": "<synthesis_log_uuid>"
}
```

Beliefs are interpretations. They have confidence levels and can be updated when new facts contradict or support them.

### Insights (Generated)
```python
{
    "node_type": "insight",
    "content": "Pattern detected: Client's stated priorities (mobile-first) differ from revealed priorities (compliance). In 5 decisions, compliance was prioritized over mobile 4 times.",
    "summary": "Stated vs revealed priority mismatch",
    "confidence": 0.75,
    "source_type": "reflection"
}
```

Insights are higher-order patterns generated by the Reflector. They connect multiple beliefs and facts.

---

## Edge Types Explained

| Edge Type | Meaning | Example |
|-----------|---------|---------|
| `supports` | Evidence for | Fact "Sarah mentioned compliance" → supports → Belief "compliance is primary driver" |
| `contradicts` | Evidence against | Fact "CEO said mobile-first is #1" → contradicts → Belief "compliance is primary driver" |
| `caused_by` | Causal chain | Decision "added audit logging" → caused_by → Fact "compliance deadline" |
| `leads_to` | Consequence | Belief "compliance is primary" → leads_to → Insight "may need pivot from consumer" |
| `supersedes` | Replaces | Belief v2 "compliance AND mobile" → supersedes → Belief v1 "compliance only" |
| `related_to` | General connection | Feature "audit trail" → related_to → Persona "compliance officer" |

---

## Memory Agent Implementation

### File: `app/agents/memory_agent.py`

```python
"""Memory Agent - Autonomous memory management for DI Agent.

Three components:
1. Watcher (Haiku): Fast processing after every event
2. Synthesizer (Sonnet): Deep integration when triggered
3. Reflector (Sonnet): Periodic insight generation
"""

from uuid import UUID
from anthropic import Anthropic
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

HAIKU_MODEL = "claude-3-5-haiku-20241022"
SONNET_MODEL = "claude-sonnet-4-20250514"


class MemoryWatcher:
    """Fast, cheap event processing. Runs after every significant event."""

    async def process_event(
        self,
        project_id: UUID,
        event_type: str,
        event_data: dict,
    ) -> dict:
        """
        Process an event and decide if deep synthesis is needed.

        Returns:
            {
                "facts_extracted": [...],
                "importance_score": 0.0-1.0,
                "triggers_synthesis": bool,
                "triggers_reflection": bool,
            }
        """
        # Get minimal recent context (last 5 nodes)
        recent_nodes = await get_recent_nodes(project_id, limit=5)

        prompt = f"""You are extracting knowledge from an event for a project memory system.

## Event
Type: {event_type}
Data: {event_data}

## Recent Memory (for context)
{self._format_nodes(recent_nodes)}

## Your Task

1. Extract FACTS (immutable observations) from this event:
   - What was literally said or done?
   - Who said/did it?
   - When?

2. Score IMPORTANCE (0.0-1.0):
   - 0.0-0.3: Routine, no new information
   - 0.4-0.6: Useful context, minor update
   - 0.7-0.9: Significant new information or contradiction
   - 1.0: Major revelation or pivot

3. Flag if this:
   - CONTRADICTS existing beliefs (triggers synthesis)
   - CONFIRMS a hypothesis (strengthens edges)
   - REVEALS something new about client priorities

Output JSON:
{{
    "facts": [
        {{"content": "...", "summary": "..."}}
    ],
    "importance": 0.X,
    "contradicts_beliefs": ["belief_summary_1", ...],
    "confirms_beliefs": ["belief_summary_1", ...],
    "triggers_synthesis": true/false,
    "rationale": "Why this importance score"
}}"""

        client = Anthropic(api_key=get_settings().ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse and store facts
        result = self._parse_response(response)
        await self._store_facts(project_id, result["facts"], event_type, event_data)

        return result


class MemorySynthesizer:
    """Deep integration of new information. Triggered by Watcher."""

    async def synthesize(
        self,
        project_id: UUID,
        trigger_reason: str,
        pending_facts: list[dict],
    ) -> dict:
        """
        Integrate new facts into the belief system.

        - Updates belief confidences
        - Creates new beliefs from accumulated evidence
        - Resolves contradictions
        - Builds causal chains (edges)
        """
        # Get current graph state
        active_beliefs = await get_active_beliefs(project_id)
        recent_facts = await get_recent_facts(project_id, limit=20)
        existing_edges = await get_edges_for_nodes(project_id, [n["id"] for n in active_beliefs])

        prompt = f"""You are synthesizing project memory by integrating new facts into beliefs.

## New Facts to Integrate
{self._format_facts(pending_facts)}

## Current Beliefs
{self._format_beliefs(active_beliefs)}

## Existing Connections
{self._format_edges(existing_edges)}

## Your Task

For each new fact, determine:

1. **Does it SUPPORT an existing belief?**
   - If yes: strengthen that connection
   - Output: {{"action": "add_edge", "from": "fact_id", "to": "belief_id", "type": "supports"}}

2. **Does it CONTRADICT an existing belief?**
   - If yes: either lower belief confidence OR update belief content
   - Output: {{"action": "update_belief", "belief_id": "...", "new_confidence": 0.X, "reason": "..."}}
   - OR: {{"action": "add_edge", "from": "fact_id", "to": "belief_id", "type": "contradicts"}}

3. **Does it reveal something NEW not captured in any belief?**
   - If yes: create a new belief
   - Output: {{"action": "create_belief", "content": "...", "summary": "...", "confidence": 0.X, "supported_by_facts": ["fact_id", ...]}}

4. **Does it create a CAUSAL connection?**
   - If A caused B, record that chain
   - Output: {{"action": "add_edge", "from": "node_id", "to": "node_id", "type": "caused_by", "rationale": "..."}}

## Critical Rules

- NEVER delete facts
- When beliefs conflict, don't delete - lower confidence or create superseding belief
- Always explain WHY in rationale fields
- Confidence should reflect evidence strength:
  - 1 supporting fact: 0.5-0.6
  - 2-3 supporting facts: 0.7-0.8
  - 4+ supporting facts: 0.9+
  - Contradicting evidence: subtract 0.1-0.2

Output a JSON array of actions to take."""

        client = Anthropic(api_key=get_settings().ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        actions = self._parse_actions(response)
        results = await self._execute_actions(project_id, actions)

        return {
            "beliefs_updated": results["beliefs_updated"],
            "beliefs_created": results["beliefs_created"],
            "edges_created": results["edges_created"],
        }


class MemoryReflector:
    """Periodic insight generation from accumulated knowledge."""

    async def reflect(self, project_id: UUID) -> dict:
        """
        Generate higher-order insights from the knowledge graph.

        Runs periodically (e.g., after every 10 decisions or weekly).
        """
        # Get comprehensive graph state
        all_beliefs = await get_all_active_beliefs(project_id)
        all_edges = await get_all_edges(project_id)
        existing_insights = await get_insights(project_id)

        prompt = f"""You are generating strategic insights from a project knowledge graph.

## Current Beliefs ({len(all_beliefs)})
{self._format_beliefs(all_beliefs)}

## Connections ({len(all_edges)})
{self._format_edges(all_edges)}

## Existing Insights (don't duplicate)
{self._format_insights(existing_insights)}

## Your Task

Look for PATTERNS across the graph:

1. **Behavioral Patterns**
   - Do the client's actions match their stated priorities?
   - What do they consistently prioritize in decisions?

2. **Contradiction Patterns**
   - Where do beliefs conflict?
   - What unresolved tensions exist?

3. **Evolution Patterns**
   - How has understanding shifted over time?
   - Which beliefs have been updated most?

4. **Risk Patterns**
   - What assumptions are weakly supported?
   - Where might we be wrong?

5. **Opportunity Patterns**
   - What adjacent possibilities emerge from the data?
   - What questions should we ask next?

Generate 2-4 NEW insights (not duplicating existing ones).

Output JSON:
{{
    "insights": [
        {{
            "content": "Full insight explanation with evidence",
            "summary": "One-line summary",
            "confidence": 0.X,
            "supported_by": ["belief_id_1", "fact_id_2", ...],
            "type": "behavioral|contradiction|evolution|risk|opportunity"
        }}
    ]
}}"""

        client = Anthropic(api_key=get_settings().ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=SONNET_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        insights = self._parse_insights(response)
        await self._store_insights(project_id, insights)

        return {"insights_generated": len(insights)}
```

---

## Markdown Rendering

The markdown document is generated FROM the graph, not stored separately.

### File: `app/core/memory_renderer.py`

```python
"""Render knowledge graph to human-readable markdown."""

async def render_memory_markdown(project_id: UUID) -> str:
    """
    Generate markdown view from knowledge graph.

    This replaces the stored markdown document - it's always
    generated fresh from the graph state.
    """
    # Fetch graph state
    beliefs = await get_active_beliefs(project_id, order_by="confidence")
    facts = await get_recent_facts(project_id, limit=10)
    insights = await get_insights(project_id, limit=5)
    decisions = await get_recent_decisions(project_id, limit=5)
    mistakes = await get_mistakes_to_avoid(project_id, limit=3)

    sections = []

    # Header
    project = await get_project(project_id)
    sections.append(f"# Project Memory: {project.name}")
    sections.append(f"*Generated from knowledge graph at {datetime.utcnow().isoformat()}Z*\n")

    # Current Understanding (from high-confidence beliefs)
    sections.append("## Current Understanding")
    high_conf_beliefs = [b for b in beliefs if b["confidence"] >= 0.7]
    if high_conf_beliefs:
        for b in high_conf_beliefs[:5]:
            conf_bar = "█" * int(b["confidence"] * 5) + "░" * (5 - int(b["confidence"] * 5))
            sections.append(f"- [{conf_bar}] {b['summary']}")
            # Show supporting evidence count
            support_count = await count_supporting_edges(b["id"])
            if support_count > 0:
                sections.append(f"  *({support_count} supporting facts)*")
    else:
        sections.append("*Building understanding from signals...*")
    sections.append("")

    # Open Questions / Low Confidence Beliefs
    sections.append("## Open Questions")
    low_conf_beliefs = [b for b in beliefs if b["confidence"] < 0.7]
    if low_conf_beliefs:
        for b in low_conf_beliefs[:3]:
            sections.append(f"- ❓ {b['summary']} (confidence: {b['confidence']:.0%})")
    else:
        sections.append("*No major uncertainties currently.*")
    sections.append("")

    # Strategic Insights
    if insights:
        sections.append("## Strategic Insights")
        for i in insights:
            emoji = {"behavioral": "👤", "contradiction": "⚡", "evolution": "📈",
                    "risk": "⚠️", "opportunity": "💡"}.get(i.get("type", ""), "📌")
            sections.append(f"### {emoji} {i['summary']}")
            sections.append(i['content'])
            sections.append("")

    # Recent Decisions
    sections.append("## Key Decisions")
    for d in decisions:
        sections.append(f"- **{d['title']}**: {d['decision'][:100]}")
        sections.append(f"  *Why*: {d['rationale'][:100]}")
    sections.append("")

    # Mistakes to Avoid
    if mistakes:
        sections.append("## Mistakes to Avoid")
        for m in mistakes:
            sections.append(f"- ⚠️ {m['title']}: {m['learning']}")
        sections.append("")

    # Recent Facts (for transparency)
    sections.append("## Recent Observations")
    for f in facts[:5]:
        sections.append(f"- {f['summary']}")

    return "\n".join(sections)
```

---

## Integration Points

### 1. After Signal Processing
```python
# In signal_pipeline.py
async def process_signal(...):
    # ... existing processing ...

    # NEW: Feed to memory agent
    from app.agents.memory_agent import MemoryWatcher
    watcher = MemoryWatcher()
    result = await watcher.process_event(
        project_id=project_id,
        event_type="signal_processed",
        event_data={
            "signal_id": str(signal_id),
            "signal_type": signal_type,
            "entities_extracted": entity_counts,
            "raw_text_snippet": raw_text[:500],
        }
    )

    # Trigger synthesis if important enough
    if result["triggers_synthesis"]:
        from app.agents.memory_agent import MemorySynthesizer
        synthesizer = MemorySynthesizer()
        await synthesizer.synthesize(
            project_id=project_id,
            trigger_reason="high_importance_signal",
            pending_facts=result["facts_extracted"],
        )
```

### 2. DI Agent Context Building
```python
# In di_agent.py
async def invoke_di_agent(...):
    # ... existing code ...

    # NEW: Get memory from graph (not stored markdown)
    from app.core.memory_renderer import render_memory_markdown
    memory_markdown = await render_memory_markdown(project_id)

    # Also get structured data for reasoning
    beliefs = await get_active_beliefs(project_id, limit=10)
    insights = await get_insights(project_id, limit=3)

    # Build prompt with both narrative and structured
    memory_context = f"""
## Project Memory

{memory_markdown}

## Beliefs (Structured)
{format_beliefs_for_prompt(beliefs)}

## Strategic Insights
{format_insights_for_prompt(insights)}
"""
```

### 3. Scheduled Reflection
```python
# New scheduled task
async def run_memory_reflection():
    """Run reflector for all active projects periodically."""
    from app.agents.memory_agent import MemoryReflector

    active_projects = await get_active_projects()
    reflector = MemoryReflector()

    for project in active_projects:
        # Only reflect if enough new data
        new_facts_count = await count_facts_since_last_reflection(project.id)
        if new_facts_count >= 5:  # Minimum threshold
            await reflector.reflect(project.id)
```

---

## Migration Path

### Phase 1: Add Tables (No Behavior Change)
1. Create migration 0088 with new tables
2. Keep existing memory system working as-is
3. Start writing to graph in parallel (dual-write)

### Phase 2: Enable Watcher
1. Deploy MemoryWatcher to process events
2. Build up graph data alongside existing system
3. Monitor token usage and latency

### Phase 3: Enable Synthesizer
1. Start triggering synthesis on high-importance events
2. Graph becomes source of truth for beliefs
3. Existing `project_memory.content` becomes cached render

### Phase 4: Enable Reflector
1. Run periodic reflection
2. Insights flow into DI Agent context
3. Full system operational

### Phase 5: Deprecate Old Memory
1. Remove direct markdown storage
2. All reads go through renderer
3. Old tables become optional backup

---

## Cost Estimates

| Operation | Model | Est. Tokens | Est. Cost | Frequency |
|-----------|-------|-------------|-----------|-----------|
| Watcher | Haiku | ~1500 | ~$0.001 | Every signal/event |
| Synthesizer | Sonnet | ~3000 | ~$0.02 | Every 3-5 events |
| Reflector | Sonnet | ~4000 | ~$0.03 | Weekly or every 10 decisions |
| Render | None | 0 | $0 | On-demand |

**Monthly estimate per active project** (assuming 20 signals/month):
- Watcher: 20 × $0.001 = $0.02
- Synthesizer: 6 × $0.02 = $0.12
- Reflector: 4 × $0.03 = $0.12
- **Total: ~$0.26/project/month**

---

## What This Enables

1. **True WHY tracking**: Beliefs have supporting facts, contradicting facts, and evolution history

2. **Confidence-based reasoning**: DI Agent can weight information by how well-supported it is

3. **Contradiction detection**: When facts conflict, the system surfaces this rather than hiding it

4. **Pattern discovery**: Reflector finds insights humans might miss

5. **Audit trail**: Every belief change is logged with reason

6. **Human-readable output**: Markdown is always available, always consistent with graph state

---

## Questions to Resolve Before Implementation

1. **Belief granularity**: How specific should beliefs be? "Client cares about compliance" vs "Client's Q2 compliance deadline drives feature prioritization"?

2. **Edge strength decay**: Should edges weaken over time if not reinforced? Or stay constant?

3. **Insight expiration**: Should old insights be archived? After how long?

4. **Cross-entity connections**: Should we link memory nodes to entities (features, personas)? Or keep them separate?
