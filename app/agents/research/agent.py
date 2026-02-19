"""Deep Research Agent - Multi-phase competitive intelligence gathering.

This agent uses Claude to autonomously:
1. DISCOVERY: Find competitors and alternatives in the market
2. DEEP DIVES: Analyze each competitor in detail
3. USER VOICE: Gather user reviews and sentiment
4. FEATURE ANALYSIS: Map features across competitors
5. SYNTHESIS: Generate insights and recommendations

The agent runs in an agentic loop, making tool calls until each phase is complete.
"""

import asyncio
import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from anthropic import Anthropic

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.state_snapshot import get_state_snapshot
from app.db.supabase_client import get_supabase
from app.agents.research.tools import TOOL_DEFINITIONS, ToolContext, execute_tool
from app.agents.research.schemas import (
    DeepResearchRequest,
    DeepResearchResponse,
)

logger = get_logger(__name__)


# === SYSTEM PROMPT ===

SYSTEM_PROMPT = """You are a world-class competitive intelligence analyst helping a product team understand their market.

## Your Mission
Conduct deep research to uncover actionable competitive intelligence. You have access to tools for web search, page fetching, review analysis, and data storage.

## Research Phases

You will work through 5 phases. Complete each phase before moving to the next:

### Phase 1: DISCOVERY
- Search for competitors and alternatives in this market
- Identify 5-8 relevant competitors (direct, adjacent, and emerging)
- Focus on products that solve similar problems or target similar users
- Use web_search with search_type="competitors"

### Phase 2: DEEP DIVES
- For each identified competitor, gather detailed information:
  - Visit their website (use fetch_page)
  - Understand their positioning, target market, key features
  - Note their pricing model and target customer size
- Save each competitor using save_competitor tool
- Research at least 3-5 competitors in depth

### Phase 3: USER VOICE
- Search for user reviews on G2, Capterra, and other sources
- Use search_g2 to find products in the category
- Use fetch_reviews to get actual user quotes
- Save valuable quotes using save_user_voice
- Look for patterns in complaints and praise
- Focus on reviews from users similar to our target personas

### Phase 4: FEATURE ANALYSIS
- Compare features across competitors
- Identify what's table stakes vs. differentiators
- Note features competitors have that we should consider
- Use generate_feature_matrix to create comparison

### Phase 5: SYNTHESIS
- Identify market gaps and opportunities
- Save key gaps using save_market_gap
- Generate executive summary and recommendations
- Identify our key differentiation opportunities

## Important Guidelines

1. **Be Thorough**: Don't rush. Each competitor deserves proper research.
2. **Use Evidence**: Every insight should have supporting data.
3. **Save As You Go**: Use save_* tools to persist findings.
4. **Stay Focused**: Keep research relevant to the project context.
5. **Complete Phases**: Call complete_phase when done with each phase.
6. **Be Specific**: Names, numbers, quotes - specificity matters.

## Project Context
{state_snapshot}

## Our Features
{features}

## Our Personas
{personas}

## Focus Areas
{focus_areas}

Start with Phase 1: DISCOVERY. Search for competitors in this market."""


# === AGENT IMPLEMENTATION ===

async def run_deep_research_agent(
    request: DeepResearchRequest,
) -> DeepResearchResponse:
    """
    Run the deep research agent.

    This executes an agentic loop where Claude makes tool calls
    to gather competitive intelligence across 5 phases.
    """
    settings = get_settings()
    run_id = uuid4()
    started_at = datetime.utcnow()

    logger.info(
        f"Starting deep research agent for project {request.project_id}",
        extra={"run_id": str(run_id)}
    )

    # Initialize Anthropic client
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Get project context
    state_snapshot = get_state_snapshot(request.project_id)
    supabase = get_supabase()

    # Get project features
    features_data = supabase.table("features").select(
        "id, name, overview, is_mvp"
    ).eq("project_id", str(request.project_id)).execute().data or []

    # Get project personas
    personas_data = supabase.table("personas").select(
        "id, name, role, pain_points"
    ).eq("project_id", str(request.project_id)).execute().data or []

    # Format for prompt
    features_str = "\n".join([
        f"- {f['name']}{' (MVP)' if f.get('is_mvp') else ''}: {(f.get('overview') or '')[:100]}"
        for f in features_data[:15]
    ])

    personas_str = "\n".join([
        f"- {p['name']} ({p.get('role', 'User')})"
        for p in personas_data[:5]
    ])

    focus_areas_str = ", ".join(request.focus_areas) if request.focus_areas else "General competitive analysis"

    # Build system prompt
    system_prompt = SYSTEM_PROMPT.format(
        state_snapshot=state_snapshot,
        features=features_str or "No features defined yet",
        personas=personas_str or "No personas defined yet",
        focus_areas=focus_areas_str,
    )

    # Initialize tool context
    tool_context = ToolContext(
        project_id=request.project_id,
        run_id=run_id,
        state_snapshot=state_snapshot,
        project_features=features_data,
    )

    # Initialize conversation
    messages = [
        {"role": "user", "content": "Begin the research. Start with Phase 1: DISCOVERY."}
    ]

    phases_completed = []
    max_iterations = 50  # Safety limit
    iteration = 0

    # Agentic loop
    while iteration < max_iterations:
        iteration += 1
        logger.info(f"Research agent iteration {iteration}")

        try:
            # Call Claude
            response = client.messages.create(
                model=settings.DEEP_RESEARCH_MODEL or "claude-sonnet-4-6",
                max_tokens=4096,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                tools=TOOL_DEFINITIONS,
                messages=messages,
                output_config={"effort": "medium"},
                thinking={"type": "adaptive"},
            )

            # Check stop reason
            if response.stop_reason == "end_turn":
                # Claude is done (no more tool calls)
                logger.info("Agent completed - no more tool calls")

                # Extract final text
                final_text = ""
                for block in response.content:
                    if block.type == "thinking":
                        continue
                    if hasattr(block, "text"):
                        final_text = block.text

                break

            # Process tool calls
            assistant_content = response.content
            tool_results = []
            phase_just_completed = None

            for block in assistant_content:
                if block.type == "thinking":
                    continue
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input

                    # Execute the tool
                    result = await execute_tool(tool_name, tool_input, tool_context)

                    # Track phase completion
                    if tool_name == "complete_phase":
                        phase = tool_input.get("phase")
                        phases_completed.append(phase)
                        phase_just_completed = phase

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })

            # Add assistant response and tool results to messages
            messages.append({"role": "assistant", "content": assistant_content})

            # If a phase was just completed, prompt for next phase
            if phase_just_completed:
                phase_order = ["discovery", "deep_dives", "user_voice", "feature_analysis", "synthesis"]
                current_idx = phase_order.index(phase_just_completed)
                if current_idx < len(phase_order) - 1:
                    next_phase = phase_order[current_idx + 1]
                    tool_results.append({
                        "type": "text",
                        "text": f"Phase {phase_just_completed} complete. Now proceed to Phase {current_idx + 2}: {next_phase.upper().replace('_', ' ')}."
                    })

            messages.append({"role": "user", "content": tool_results})

            # Check if all phases complete
            if len(phases_completed) >= 5 or "synthesis" in phases_completed:
                logger.info("All phases completed")
                break

        except Exception as e:
            logger.error(f"Agent iteration failed: {e}")
            break

    # Generate final response
    completed_at = datetime.utcnow()

    # Get final counts from database
    competitors_count = len(supabase.table("competitor_references").select("id").eq(
        "project_id", str(request.project_id)
    ).execute().data or [])

    # Build executive summary from last messages
    executive_summary = "Research completed. "
    key_insights = []
    recommended_actions = []

    # Try to extract insights from final response
    for msg in reversed(messages):
        if isinstance(msg.get("content"), list):
            for block in msg["content"]:
                if hasattr(block, "type") and block.type == "thinking":
                    continue
                if hasattr(block, "text"):
                    text = block.text
                    if "insight" in text.lower() or "recommend" in text.lower():
                        # Extract key points
                        lines = text.split("\n")
                        for line in lines:
                            if line.strip().startswith("-") or line.strip().startswith("•"):
                                clean = line.strip().lstrip("-•").strip()
                                if "recommend" in line.lower():
                                    recommended_actions.append(clean)
                                else:
                                    key_insights.append(clean)
                    executive_summary = text[:500]
                    break

    return DeepResearchResponse(
        run_id=run_id,
        project_id=request.project_id,
        status="completed" if len(phases_completed) >= 4 else "partial",
        competitors_found=len(tool_context.competitors_saved),
        competitors_analyzed=min(len(tool_context.competitors_saved), request.max_competitors),
        features_mapped=len(features_data),
        reviews_analyzed=tool_context.user_voices_saved,
        market_gaps_identified=tool_context.market_gaps_saved,
        executive_summary=executive_summary,
        key_insights=key_insights[:10],
        recommended_actions=recommended_actions[:5],
        started_at=started_at,
        completed_at=completed_at,
        phases_completed=phases_completed,
    )


# === STREAMING VERSION ===

async def run_deep_research_agent_streaming(
    request: DeepResearchRequest,
    on_event: callable = None,
):
    """
    Run deep research agent with streaming progress updates.

    Args:
        request: Research request
        on_event: Callback for progress events

    Yields:
        Progress events as dicts
    """
    settings = get_settings()
    run_id = uuid4()
    started_at = datetime.utcnow()

    if on_event:
        await on_event({
            "type": "started",
            "run_id": str(run_id),
            "project_id": str(request.project_id),
        })

    try:
        # Run the agent
        result = await run_deep_research_agent(request)

        if on_event:
            await on_event({
                "type": "completed",
                "run_id": str(run_id),
                "result": result.model_dump(),
            })

        return result

    except Exception as e:
        if on_event:
            await on_event({
                "type": "error",
                "run_id": str(run_id),
                "error": str(e),
            })
        raise
