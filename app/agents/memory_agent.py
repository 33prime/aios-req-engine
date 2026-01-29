"""Memory Agent - Autonomous memory management for DI Agent.

Three components:
1. MemoryWatcher (Haiku): Fast processing after every event - extracts facts
2. MemorySynthesizer (Sonnet): Deep integration - builds beliefs from facts
3. MemoryReflector (Sonnet): Periodic insight generation - finds patterns

The memory agent maintains a knowledge graph where:
- Facts are immutable observations (confidence always 1.0)
- Beliefs are evolving interpretations (confidence 0.0-1.0)
- Insights are generated patterns across beliefs

Usage:
    # After signal processing
    watcher = MemoryWatcher()
    result = await watcher.process_event(project_id, "signal_processed", {...})

    if result["triggers_synthesis"]:
        synthesizer = MemorySynthesizer()
        await synthesizer.synthesize(project_id, "high_importance", result["facts"])

    # Periodically (e.g., after 10 decisions)
    reflector = MemoryReflector()
    await reflector.reflect(project_id)
"""

import json
import re
from datetime import datetime
from typing import Any
from uuid import UUID

from anthropic import Anthropic

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.memory_graph import (
    create_node,
    create_edge,
    get_active_beliefs,
    get_recent_facts,
    get_insights,
    get_all_edges,
    get_edges_to_node,
    get_nodes,
    update_belief_confidence,
    update_belief_content,
    supersede_belief,
    start_synthesis_log,
    complete_synthesis_log,
    fail_synthesis_log,
    archive_old_insights,
    archive_low_confidence_beliefs,
)

logger = get_logger(__name__)

# Model configuration
HAIKU_MODEL = "claude-3-5-haiku-20241022"
SONNET_MODEL = "claude-sonnet-4-20250514"

# Thresholds
IMPORTANCE_THRESHOLD_FOR_SYNTHESIS = 0.7
MIN_FACTS_FOR_REFLECTION = 5
INSIGHT_ARCHIVE_DAYS = 60


class MemoryWatcher:
    """
    Fast, cheap event processing using Haiku.

    Runs after every significant event (signal processed, entity changed, etc.)
    to extract facts and determine if deeper synthesis is needed.

    Cost: ~$0.001 per invocation
    """

    def __init__(self):
        self.settings = get_settings()
        self.client = Anthropic(api_key=self.settings.ANTHROPIC_API_KEY)

    async def process_event(
        self,
        project_id: UUID,
        event_type: str,
        event_data: dict,
    ) -> dict:
        """
        Process an event and extract facts.

        Args:
            project_id: Project UUID
            event_type: Type of event ('signal_processed', 'entity_changed', etc.)
            event_data: Event details

        Returns:
            {
                "facts": [{"id": uuid, "summary": str}, ...],
                "importance": float (0.0-1.0),
                "triggers_synthesis": bool,
                "triggers_reflection": bool,
                "contradicted_beliefs": [str, ...],
                "supported_beliefs": [str, ...],
            }
        """
        started_at = datetime.utcnow()

        # Start synthesis log
        log_id = start_synthesis_log(
            project_id=project_id,
            synthesis_type="watcher",
            trigger_type=event_type,
            trigger_details={"event_data_keys": list(event_data.keys())},
        )

        try:
            # Get minimal recent context
            recent_beliefs = get_active_beliefs(project_id, limit=5)
            recent_facts = get_recent_facts(project_id, limit=3)

            # Build prompt
            prompt = self._build_watcher_prompt(event_type, event_data, recent_beliefs, recent_facts)

            # Call Haiku
            response = self.client.messages.create(
                model=HAIKU_MODEL,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse response
            content = response.content[0].text if response.content else "{}"
            result = self._parse_watcher_response(content)

            # Store extracted facts
            stored_facts = []
            for fact in result.get("facts", []):
                node = create_node(
                    project_id=project_id,
                    node_type="fact",
                    content=fact["content"],
                    summary=fact["summary"],
                    source_type="signal" if "signal" in event_type else "agent",
                    source_id=UUID(event_data.get("signal_id")) if event_data.get("signal_id") else None,
                )
                if node:
                    stored_facts.append({"id": node["id"], "summary": fact["summary"]})

            # Complete synthesis log
            complete_synthesis_log(
                log_id=log_id,
                facts_created=len(stored_facts),
                tokens_input=response.usage.input_tokens if response.usage else 0,
                tokens_output=response.usage.output_tokens if response.usage else 0,
                model_used=HAIKU_MODEL,
                started_at=started_at,
            )

            importance = result.get("importance", 0.5)

            return {
                "facts": stored_facts,
                "importance": importance,
                "triggers_synthesis": importance >= IMPORTANCE_THRESHOLD_FOR_SYNTHESIS or len(result.get("contradicts_beliefs", [])) > 0,
                "triggers_reflection": result.get("is_milestone", False),
                "contradicted_beliefs": result.get("contradicts_beliefs", []),
                "supported_beliefs": result.get("confirms_beliefs", []),
                "rationale": result.get("rationale", ""),
            }

        except Exception as e:
            logger.error(f"MemoryWatcher failed: {e}")
            fail_synthesis_log(log_id, str(e))
            return {
                "facts": [],
                "importance": 0.0,
                "triggers_synthesis": False,
                "triggers_reflection": False,
                "contradicted_beliefs": [],
                "supported_beliefs": [],
                "error": str(e),
            }

    def _build_watcher_prompt(
        self,
        event_type: str,
        event_data: dict,
        recent_beliefs: list[dict],
        recent_facts: list[dict],
    ) -> str:
        """Build the prompt for fact extraction."""
        beliefs_text = "\n".join([
            f"- [{b['confidence']:.0%}] {b['summary']}"
            for b in recent_beliefs
        ]) if recent_beliefs else "No beliefs yet."

        facts_text = "\n".join([
            f"- {f['summary']}"
            for f in recent_facts
        ]) if recent_facts else "No recent facts."

        # Format event data, handling common fields
        event_details = []
        if event_data.get("signal_type"):
            event_details.append(f"Signal type: {event_data['signal_type']}")
        if event_data.get("source_label"):
            event_details.append(f"Source: {event_data['source_label']}")
        if event_data.get("entities_extracted"):
            event_details.append(f"Entities: {event_data['entities_extracted']}")
        if event_data.get("raw_text_snippet"):
            event_details.append(f"Content snippet: {event_data['raw_text_snippet'][:500]}")
        if event_data.get("entity_type"):
            event_details.append(f"Entity: {event_data['entity_type']} - {event_data.get('entity_name', 'unknown')}")
        if event_data.get("action"):
            event_details.append(f"Action: {event_data['action']}")

        event_text = "\n".join(event_details) if event_details else str(event_data)[:500]

        return f"""You are extracting knowledge from an event for a project memory system.

## Event
Type: {event_type}
{event_text}

## Current Beliefs (for contradiction detection)
{beliefs_text}

## Recent Facts (for context)
{facts_text}

## Your Task

1. **Extract FACTS** (immutable observations) from this event:
   - What was literally said, done, or observed?
   - Who was involved?
   - Be specific and granular (one fact per distinct piece of information)

2. **Score IMPORTANCE** (0.0-1.0):
   - 0.0-0.3: Routine, no new information
   - 0.4-0.6: Useful context, minor update
   - 0.7-0.9: Significant new information or contradiction
   - 1.0: Major revelation, pivot, or contradiction

3. **Check for CONTRADICTIONS**: Does this contradict any existing beliefs?

4. **Check for CONFIRMATIONS**: Does this support any existing beliefs?

5. **Is this a MILESTONE?** (triggers deeper reflection)
   - Major decision made
   - Significant change in direction
   - Key stakeholder input

Output valid JSON only:
{{
    "facts": [
        {{"content": "Full fact text with context", "summary": "One-line summary"}}
    ],
    "importance": 0.X,
    "contradicts_beliefs": ["belief summary if contradicted"],
    "confirms_beliefs": ["belief summary if confirmed"],
    "is_milestone": false,
    "rationale": "Brief explanation of importance score"
}}"""

    def _parse_watcher_response(self, content: str) -> dict:
        """Parse the watcher's JSON response."""
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
            return {}
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse watcher response: {e}")
            return {}


class MemorySynthesizer:
    """
    Deep integration of facts into beliefs using Sonnet.

    Triggered by MemoryWatcher when importance is high or contradictions detected.
    Builds and updates beliefs, creates edges, resolves contradictions.

    Cost: ~$0.02 per invocation
    """

    def __init__(self):
        self.settings = get_settings()
        self.client = Anthropic(api_key=self.settings.ANTHROPIC_API_KEY)

    async def synthesize(
        self,
        project_id: UUID,
        trigger_reason: str,
        pending_facts: list[dict] | None = None,
    ) -> dict:
        """
        Integrate facts into the belief system.

        Args:
            project_id: Project UUID
            trigger_reason: What triggered this synthesis
            pending_facts: New facts to integrate (if None, uses recent unprocessed)

        Returns:
            {
                "beliefs_created": int,
                "beliefs_updated": int,
                "edges_created": int,
            }
        """
        started_at = datetime.utcnow()

        # Get current state
        active_beliefs = get_active_beliefs(project_id, limit=20)
        recent_facts = get_recent_facts(project_id, limit=15)
        existing_edges = get_all_edges(project_id, limit=100)

        # Start synthesis log
        log_id = start_synthesis_log(
            project_id=project_id,
            synthesis_type="synthesizer",
            trigger_type=trigger_reason,
            input_facts_count=len(recent_facts),
            input_beliefs_count=len(active_beliefs),
        )

        try:
            # Build prompt
            prompt = self._build_synthesizer_prompt(
                pending_facts or [],
                recent_facts,
                active_beliefs,
                existing_edges,
            )

            # Call Sonnet
            response = self.client.messages.create(
                model=SONNET_MODEL,
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse and execute actions
            content = response.content[0].text if response.content else "[]"
            actions = self._parse_synthesizer_response(content)

            results = await self._execute_actions(project_id, actions, log_id)

            # Complete synthesis log
            complete_synthesis_log(
                log_id=log_id,
                beliefs_created=results["beliefs_created"],
                beliefs_updated=results["beliefs_updated"],
                edges_created=results["edges_created"],
                tokens_input=response.usage.input_tokens if response.usage else 0,
                tokens_output=response.usage.output_tokens if response.usage else 0,
                model_used=SONNET_MODEL,
                started_at=started_at,
            )

            logger.info(
                f"Synthesis complete: {results['beliefs_created']} created, "
                f"{results['beliefs_updated']} updated, {results['edges_created']} edges"
            )

            return results

        except Exception as e:
            logger.error(f"MemorySynthesizer failed: {e}")
            fail_synthesis_log(log_id, str(e))
            return {
                "beliefs_created": 0,
                "beliefs_updated": 0,
                "edges_created": 0,
                "error": str(e),
            }

    def _build_synthesizer_prompt(
        self,
        pending_facts: list[dict],
        recent_facts: list[dict],
        active_beliefs: list[dict],
        existing_edges: list[dict],
    ) -> str:
        """Build the prompt for belief synthesis."""
        # Format facts
        facts_text = ""
        if pending_facts:
            facts_text += "### New Facts (just extracted)\n"
            for i, f in enumerate(pending_facts):
                facts_text += f"{i+1}. [{f.get('id', 'new')}] {f.get('summary', f.get('content', ''))}\n"

        facts_text += "\n### Recent Facts (for context)\n"
        for f in recent_facts[:10]:
            facts_text += f"- [{f['id'][:8]}] {f['summary']}\n"

        # Format beliefs
        beliefs_text = ""
        for b in active_beliefs:
            support_count = len(get_edges_to_node(UUID(b["id"]), "supports"))
            contradict_count = len(get_edges_to_node(UUID(b["id"]), "contradicts"))
            beliefs_text += f"- [{b['id'][:8]}] ({b['confidence']:.0%}) {b['summary']}\n"
            beliefs_text += f"  Support: {support_count} facts, Contradict: {contradict_count} facts\n"

        if not beliefs_text:
            beliefs_text = "No beliefs yet - this is initial synthesis.\n"

        # Format edges (summarized)
        edge_summary = {}
        for e in existing_edges:
            t = e["edge_type"]
            edge_summary[t] = edge_summary.get(t, 0) + 1
        edges_text = ", ".join([f"{k}: {v}" for k, v in edge_summary.items()]) if edge_summary else "No edges yet."

        return f"""You are synthesizing project memory by integrating facts into beliefs.

## Facts
{facts_text}

## Current Beliefs
{beliefs_text}

## Existing Edges
{edges_text}

## Your Task

For each fact (especially new ones), determine what actions to take:

### Action Types

1. **add_edge** - Connect a fact to a belief
   ```json
   {{"action": "add_edge", "from_id": "fact_id", "to_id": "belief_id", "edge_type": "supports|contradicts", "rationale": "why"}}
   ```

2. **update_belief_confidence** - Adjust confidence based on evidence
   ```json
   {{"action": "update_belief_confidence", "belief_id": "id", "new_confidence": 0.X, "reason": "why"}}
   ```

3. **create_belief** - Create a new belief from accumulated evidence
   ```json
   {{"action": "create_belief", "content": "Full belief text", "summary": "One-line", "confidence": 0.X, "domain": "client_priority|technical|market|user_need|constraint", "supported_by": ["fact_id1", "fact_id2"]}}
   ```

4. **update_belief_content** - Refine a belief's meaning
   ```json
   {{"action": "update_belief_content", "belief_id": "id", "new_content": "...", "new_summary": "...", "new_confidence": 0.X, "reason": "why"}}
   ```

5. **supersede_belief** - Replace a belief with a better one
   ```json
   {{"action": "supersede_belief", "old_belief_id": "id", "new_content": "...", "new_summary": "...", "new_confidence": 0.X, "reason": "why"}}
   ```

### Confidence Guidelines

- 1 supporting fact, no contradictions: 0.5-0.6
- 2-3 supporting facts: 0.7-0.8
- 4+ supporting facts: 0.85-0.95
- Each contradicting fact: subtract 0.1-0.15
- Never go above 0.95 or below 0.1

### Rules

- Be GRANULAR with beliefs (specific, not vague)
- Always explain WHY in rationale/reason fields
- Create edges to connect facts to beliefs
- If facts conflict, don't delete - lower confidence and explain
- Beliefs should capture the WHY, not just the WHAT

Output a JSON array of actions:
```json
[
    {{"action": "...", ...}},
    {{"action": "...", ...}}
]
```"""

    def _parse_synthesizer_response(self, content: str) -> list[dict]:
        """Parse the synthesizer's JSON response."""
        try:
            # Try to extract JSON array from the response
            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                return json.loads(json_match.group())
            return []
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse synthesizer response: {e}")
            return []

    async def _execute_actions(
        self,
        project_id: UUID,
        actions: list[dict],
        synthesis_log_id: UUID,
    ) -> dict:
        """Execute the synthesis actions."""
        results = {
            "beliefs_created": 0,
            "beliefs_updated": 0,
            "edges_created": 0,
        }

        for action in actions:
            try:
                action_type = action.get("action")

                if action_type == "add_edge":
                    create_edge(
                        project_id=project_id,
                        from_node_id=UUID(action["from_id"]),
                        to_node_id=UUID(action["to_id"]),
                        edge_type=action["edge_type"],
                        rationale=action.get("rationale"),
                    )
                    results["edges_created"] += 1

                elif action_type == "update_belief_confidence":
                    update_belief_confidence(
                        node_id=UUID(action["belief_id"]),
                        new_confidence=action["new_confidence"],
                        change_reason=action["reason"],
                        triggered_by_synthesis_id=synthesis_log_id,
                    )
                    results["beliefs_updated"] += 1

                elif action_type == "create_belief":
                    node = create_node(
                        project_id=project_id,
                        node_type="belief",
                        content=action["content"],
                        summary=action["summary"],
                        confidence=action["confidence"],
                        source_type="synthesis",
                        source_id=synthesis_log_id,
                        belief_domain=action.get("domain"),
                    )
                    results["beliefs_created"] += 1

                    # Create supporting edges
                    if node and action.get("supported_by"):
                        for fact_id in action["supported_by"]:
                            try:
                                create_edge(
                                    project_id=project_id,
                                    from_node_id=UUID(fact_id),
                                    to_node_id=UUID(node["id"]),
                                    edge_type="supports",
                                )
                                results["edges_created"] += 1
                            except Exception:
                                pass  # Skip invalid fact IDs

                elif action_type == "update_belief_content":
                    update_belief_content(
                        node_id=UUID(action["belief_id"]),
                        new_content=action["new_content"],
                        new_summary=action["new_summary"],
                        new_confidence=action.get("new_confidence"),
                        change_reason=action["reason"],
                        triggered_by_synthesis_id=synthesis_log_id,
                    )
                    results["beliefs_updated"] += 1

                elif action_type == "supersede_belief":
                    # Create new belief first
                    new_node = create_node(
                        project_id=project_id,
                        node_type="belief",
                        content=action["new_content"],
                        summary=action["new_summary"],
                        confidence=action["new_confidence"],
                        source_type="synthesis",
                        source_id=synthesis_log_id,
                    )
                    if new_node:
                        supersede_belief(
                            old_node_id=UUID(action["old_belief_id"]),
                            new_node_id=UUID(new_node["id"]),
                            reason=action["reason"],
                        )
                        results["beliefs_created"] += 1
                        results["beliefs_updated"] += 1
                        results["edges_created"] += 1  # supersedes edge

            except Exception as e:
                logger.warning(f"Failed to execute action {action}: {e}")

        return results


class MemoryReflector:
    """
    Periodic insight generation using Sonnet.

    Runs periodically to find patterns across accumulated beliefs and facts.
    Generates strategic insights that help guide the DI Agent.

    Cost: ~$0.03 per invocation
    """

    def __init__(self):
        self.settings = get_settings()
        self.client = Anthropic(api_key=self.settings.ANTHROPIC_API_KEY)

    async def reflect(self, project_id: UUID) -> dict:
        """
        Generate strategic insights from the knowledge graph.

        Args:
            project_id: Project UUID

        Returns:
            {
                "insights_created": int,
                "insights": [{"summary": str, "type": str}, ...],
            }
        """
        started_at = datetime.utcnow()

        # Get comprehensive graph state
        all_beliefs = get_active_beliefs(project_id, limit=30)
        all_facts = get_recent_facts(project_id, limit=20)
        existing_insights = get_insights(project_id, limit=10)
        all_edges = get_all_edges(project_id, limit=150)

        # Start synthesis log
        log_id = start_synthesis_log(
            project_id=project_id,
            synthesis_type="reflector",
            trigger_type="periodic",
            input_facts_count=len(all_facts),
            input_beliefs_count=len(all_beliefs),
        )

        try:
            # Build prompt
            prompt = self._build_reflector_prompt(
                all_beliefs,
                all_facts,
                existing_insights,
                all_edges,
            )

            # Call Sonnet
            response = self.client.messages.create(
                model=SONNET_MODEL,
                max_tokens=2500,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse and store insights
            content = response.content[0].text if response.content else "{}"
            result = self._parse_reflector_response(content)

            stored_insights = []
            for insight in result.get("insights", []):
                node = create_node(
                    project_id=project_id,
                    node_type="insight",
                    content=insight["content"],
                    summary=insight["summary"],
                    confidence=insight.get("confidence", 0.7),
                    source_type="reflection",
                    source_id=log_id,
                    insight_type=insight.get("type"),
                )
                if node:
                    stored_insights.append({
                        "id": node["id"],
                        "summary": insight["summary"],
                        "type": insight.get("type"),
                    })

                    # Create supporting edges
                    for supported_by_id in insight.get("supported_by", []):
                        try:
                            create_edge(
                                project_id=project_id,
                                from_node_id=UUID(supported_by_id),
                                to_node_id=UUID(node["id"]),
                                edge_type="leads_to",
                                rationale="Evidence for insight",
                            )
                        except Exception:
                            pass

            # Archive old insights
            archived = archive_old_insights(project_id, days_old=INSIGHT_ARCHIVE_DAYS)

            # Complete synthesis log
            complete_synthesis_log(
                log_id=log_id,
                insights_created=len(stored_insights),
                edges_created=len(stored_insights) * 2,  # Approximate
                tokens_input=response.usage.input_tokens if response.usage else 0,
                tokens_output=response.usage.output_tokens if response.usage else 0,
                model_used=SONNET_MODEL,
                started_at=started_at,
            )

            logger.info(f"Reflection complete: {len(stored_insights)} insights created, {archived} old insights archived")

            return {
                "insights_created": len(stored_insights),
                "insights": stored_insights,
                "insights_archived": archived,
            }

        except Exception as e:
            logger.error(f"MemoryReflector failed: {e}")
            fail_synthesis_log(log_id, str(e))
            return {
                "insights_created": 0,
                "insights": [],
                "error": str(e),
            }

    def _build_reflector_prompt(
        self,
        all_beliefs: list[dict],
        all_facts: list[dict],
        existing_insights: list[dict],
        all_edges: list[dict],
    ) -> str:
        """Build the prompt for insight generation."""
        # Format beliefs with confidence
        beliefs_text = ""
        for b in all_beliefs:
            beliefs_text += f"- [{b['id'][:8]}] ({b['confidence']:.0%}) {b['summary']}\n"
            if b.get("belief_domain"):
                beliefs_text += f"  Domain: {b['belief_domain']}\n"

        if not beliefs_text:
            beliefs_text = "No beliefs yet.\n"

        # Format facts
        facts_text = "\n".join([f"- [{f['id'][:8]}] {f['summary']}" for f in all_facts[:15]])
        if not facts_text:
            facts_text = "No facts yet.\n"

        # Format existing insights (to avoid duplicates)
        existing_text = "\n".join([f"- {i['summary']}" for i in existing_insights])
        if not existing_text:
            existing_text = "No existing insights.\n"

        # Summarize edges
        edge_summary = {}
        for e in all_edges:
            t = e["edge_type"]
            edge_summary[t] = edge_summary.get(t, 0) + 1
        edges_text = ", ".join([f"{k}: {v}" for k, v in edge_summary.items()]) if edge_summary else "No edges."

        return f"""You are generating strategic insights from a project knowledge graph.

## Current Beliefs ({len(all_beliefs)})
{beliefs_text}

## Recent Facts ({len(all_facts)})
{facts_text}

## Edge Summary
{edges_text}

## Existing Insights (DO NOT duplicate these)
{existing_text}

## Your Task

Look for PATTERNS across the beliefs and facts that reveal deeper understanding:

### Insight Types

1. **behavioral** - Client's actions vs stated intentions
   - Do they say one thing but do another?
   - What do they consistently prioritize?

2. **contradiction** - Unresolved tensions in the data
   - Where do beliefs conflict?
   - What can't both be true?

3. **evolution** - How understanding has changed
   - What did we think before that we now know differently?
   - How have priorities shifted?

4. **risk** - Potential problems or weak assumptions
   - What beliefs have low confidence?
   - Where might we be wrong?

5. **opportunity** - Possibilities not yet explored
   - What adjacent ideas emerge?
   - What questions should we be asking?

### Rules

- Generate 2-4 NEW insights (not duplicating existing ones)
- Each insight should be non-obvious (not just restating beliefs)
- Support each insight with specific belief/fact IDs
- Confidence should reflect how well-supported the pattern is

Output valid JSON:
```json
{{
    "insights": [
        {{
            "content": "Full insight with evidence and reasoning",
            "summary": "One-line summary",
            "confidence": 0.X,
            "type": "behavioral|contradiction|evolution|risk|opportunity",
            "supported_by": ["belief_id1", "fact_id2"]
        }}
    ]
}}
```"""

    def _parse_reflector_response(self, content: str) -> dict:
        """Parse the reflector's JSON response."""
        try:
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                return json.loads(json_match.group())
            return {}
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse reflector response: {e}")
            return {}


# =============================================================================
# Convenience Functions
# =============================================================================


async def process_signal_for_memory(
    project_id: UUID,
    signal_id: UUID,
    signal_type: str,
    raw_text: str,
    entities_extracted: dict,
) -> dict:
    """
    Convenience function to process a signal through the memory system.

    Called after signal processing completes.

    Args:
        project_id: Project UUID
        signal_id: Signal UUID
        signal_type: Type of signal
        raw_text: Raw text content
        entities_extracted: Dict of entity counts

    Returns:
        Processing result including whether synthesis was triggered
    """
    watcher = MemoryWatcher()

    result = await watcher.process_event(
        project_id=project_id,
        event_type="signal_processed",
        event_data={
            "signal_id": str(signal_id),
            "signal_type": signal_type,
            "raw_text_snippet": raw_text[:500] if raw_text else "",
            "entities_extracted": entities_extracted,
        },
    )

    # Trigger synthesis if needed
    if result.get("triggers_synthesis"):
        synthesizer = MemorySynthesizer()
        synthesis_result = await synthesizer.synthesize(
            project_id=project_id,
            trigger_reason="high_importance_signal",
            pending_facts=result.get("facts", []),
        )
        result["synthesis_result"] = synthesis_result

    return result


async def run_periodic_reflection(project_id: UUID) -> dict:
    """
    Run periodic reflection for a project.

    Should be called after significant activity (e.g., every 10 decisions).

    Args:
        project_id: Project UUID

    Returns:
        Reflection result
    """
    # First, clean up low-confidence beliefs
    archived_beliefs = archive_low_confidence_beliefs(
        project_id=project_id,
        confidence_threshold=0.3,
        min_age_days=7,
    )

    # Then run reflection
    reflector = MemoryReflector()
    result = await reflector.reflect(project_id)

    result["beliefs_archived"] = archived_beliefs

    return result
