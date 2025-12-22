"""Research gap analysis LLM chain with tool calling for web search."""

from openai import OpenAI
from typing import List, Dict, Any
import json
import os

from app.core.schemas_redteam import RedTeamOutput, RedTeamInsight
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.vp_validation import validate_vp_completeness, format_vp_gaps_for_prompt

logger = get_logger(__name__)


def _get_client() -> OpenAI:
    """Get OpenAI client lazily."""
    settings = get_settings()
    return OpenAI(api_key=settings.OPENAI_API_KEY)

# Tool definition for web search
WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web to validate claims, check competitor features, verify market data, or research technical feasibility. Use this to fact-check research assertions or find current information.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to execute"
                },
                "purpose": {
                    "type": "string",
                    "description": "Why you're searching (e.g., 'validate market size claim', 'check competitor X has feature Y')"
                }
            },
            "required": ["query", "purpose"]
        }
    }
}


def web_search(query: str, purpose: str) -> Dict[str, Any]:
    """
    Mock web search function.

    In production, integrate with:
    - Brave Search API
    - Google Custom Search
    - Serper API
    - etc.
    """
    # TODO: Implement actual web search
    logger.info(f"Web search: {query} (purpose: {purpose})")
    return {
        "query": query,
        "purpose": purpose,
        "results": [
            {"title": "Mock Result", "snippet": "This is a mock search result", "url": "https://example.com"}
        ]
    }


def build_research_gap_prompt(
    research_chunks: List[Dict],
    current_features: List[Dict],
    current_prd_sections: List[Dict],
    current_vp_steps: List[Dict],
    context_chunks: List[Dict]
) -> str:
    """
    Build VP-centric research gap analysis prompt with 5-gate validation.

    Gates:
    1. Completeness (data schemas, business logic)
    2. Market Validation (research alignment)
    3. Assumption Testing (validate or challenge)
    4. Scope Protection (prevent gold-plating)
    5. Wow Factor (client experience)
    """

    # Validate VP completeness
    vp_gaps, vp_summary = validate_vp_completeness(current_vp_steps)
    vp_gaps_text = format_vp_gaps_for_prompt(vp_gaps)

    # Organize research by section type
    research_by_type = {}
    for chunk in research_chunks:
        section_type = chunk.get("metadata", {}).get("section_type", "unknown")
        if section_type not in research_by_type:
            research_by_type[section_type] = []
        research_by_type[section_type].append(chunk)

    # Build research summary (organized by section)
    research_summary = "## RESEARCH INTELLIGENCE\n\n"
    for section_type, chunks in research_by_type.items():
        research_summary += f"### {section_type.replace('_', ' ').title()}\n"
        for chunk in chunks:
            research_summary += f"- {chunk['content'][:400]}...\n"
        research_summary += "\n"

    # Build VP-centric state summary (VP is THE product)
    vp_state = "## VALUE PATH (CORE PRODUCT)\n\n"
    vp_state += f"Completeness: {vp_summary['completeness_percent']}% ({vp_summary['complete_steps']}/{vp_summary['total_steps']} steps complete)\n"
    vp_state += f"Prototype Ready: {'YES' if vp_summary['is_prototype_ready'] else 'NO (has critical gaps)'}\n\n"

    for vp in current_vp_steps:
        vp_state += f"**Step {vp['step_index']}: {vp['label']}**\n"
        vp_state += f"  Description: {vp.get('description', 'N/A')[:150]}\n"
        vp_state += f"  User Benefit: {vp.get('user_benefit_pain', 'N/A')[:150]}\n"

        # Show enrichment status
        enrichment = vp.get('enrichment', {})
        has_data = bool(enrichment.get('data_schema'))
        has_logic = bool(enrichment.get('business_logic'))
        has_transition = bool(enrichment.get('transition_logic'))
        vp_state += f"  Enrichment: Data={'✓' if has_data else '✗'}, Logic={'✓' if has_logic else '✗'}, Transition={'✓' if has_transition else '✗'}\n\n"

    # Features mapped to VP
    features_state = "## FEATURES (ENABLE VP STEPS)\n\n"
    for feat in current_features:
        features_state += f"- **{feat['name']}** (MVP: {feat.get('is_mvp', False)}, Category: {feat.get('category', 'N/A')})\n"
    features_state += "\n"

    # PRD sections
    prd_state = "## PRD SECTIONS (INFORM VP DESIGN)\n\n"
    for prd in current_prd_sections:
        prd_state += f"- {prd['slug']}: {prd.get('label', 'N/A')}\n"
    prd_state += "\n"

    # Client context
    context_summary = "## CLIENT SIGNALS\n\n"
    for chunk in context_chunks[:8]:
        context_summary += f"- {chunk['content'][:250]}...\n"

    prompt = f"""You are analyzing a Value Path (VP) that will be prototyped to wow a non-technical client.

**SYSTEM PURPOSE:**
- VP is THE product (not documentation, but the actual user journey to build)
- Features exist to ENABLE VP steps (no VP step = question if feature is needed)
- Research provides market intelligence to OPTIMIZE VP
- Goal: Prototype-ready VP that makes client say "wow, they get me!"

{vp_state}

{vp_gaps_text}

{features_state}

{prd_state}

{research_summary}

{context_summary}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## YOUR ANALYSIS: 5-GATE VALIDATION

**GATE 1: VP COMPLETENESS** (Critical - Can we build a prototype?)

For each VP step, verify:
- Data schema complete? (entities, fields, types, constraints)
- Business logic complete? (validation rules, special sauce)
- Transition logic complete? (what triggers next step?)
- Flag any missing elements that BLOCK prototyping as CRITICAL

**GATE 2: MARKET VALIDATION** (Important - Is this optimal?)

Compare VP against research:
- Are research must-have features included in VP steps?
- Does VP address research pain points?
- Does VP follow market UX best practices?
- Is time-to-value competitive with research benchmarks?
Recommend optimizations based on research.

**GATE 3: ASSUMPTION TESTING** (Important - Are assumptions solid?)

Identify core assumptions embedded in VP:
- Connectivity (online vs offline)
- Device (mobile vs desktop)
- User identity (account vs accountless)
- Data persistence (ephemeral vs stored)

Check each against research:
- Strong (research confirms) → no action
- Weak (no research support) → flag as risk
- Broken (research contradicts) → flag as CRITICAL

Estimate blast radius: if assumption changes, how many VP steps affected?

**GATE 4: SCOPE PROTECTION** (Prevent Distraction)

For research features that don't map to VP steps:
- Determine if MISSING VP STEP or OUT-OF-SCOPE
- Flag "amazing but complex" features (defer to v2)
- Keep VP focused on core first principles
- Common features (login, CRUD, notifications) are LOW PRIORITY unless core differentiator

**GATE 5: WOW FACTOR** (Client Experience)

Evaluate:
- Time to first value (minimize steps before wow moment)
- Cognitive load per step (minimize inputs/decisions)
- "Magic moments" (seamless, instant interactions - e.g., QR code instant join)
- Competitive advantage (is this better/faster/simpler than alternatives?)
Optimize for non-technical client impression.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## FOCUS AREAS

✓ VP steps and their completeness (Gate 1)
✓ Unique/differentiating features that wow (Gate 2, 5)
✓ Core assumptions that could break product (Gate 3)
✓ Feature-to-VP mapping (features without VP steps = scope creep)

✗ Common features (login, payments) UNLESS they're unique differentiators
✗ Edge cases and error handling (refinement phase)
✗ Technical perfection (80% right is the goal)
✗ Trivial differences from research

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## INSTRUCTIONS

For each insight:
1. Assign **gate** category: "completeness", "validation", "assumption", "scope", "wow"
2. Assign **severity**: "minor" (nice-to-have), "important" (should-have), "critical" (blocks prototype)
3. Assign **category**: "logic", "ux", "security", "data", "reporting", "scope", "ops"
4. Write **title** (5-10 words, clear and specific)
5. Write **finding** (what's missing or misaligned)
6. Write **why** (business/user impact, risk if not addressed)
7. Specify **suggested_action**: "apply_internally" or "needs_confirmation"
8. Specify **targets**: which VP step, feature, or PRD section (use labels, not just IDs)
9. Provide **evidence**: cite research chunks or client signals

Use web_search tool to:
- Validate research claims (market size, competitor features)
- Check technical feasibility
- Verify best practices

PRIORITIZE INSIGHTS:
1. Gate 1 (completeness) - blocks prototyping → CRITICAL
2. Gate 3 (broken assumptions) - breaks product → CRITICAL
3. Gate 5 (wow factor) - determines client reaction → IMPORTANT
4. Gate 2 (validation) - optimizes VP → IMPORTANT
5. Gate 4 (scope) - prevents distraction → MINOR

Output valid JSON matching RedTeamOutput schema.
"""
    return prompt


def run_research_gap_analysis(
    research_chunks: List[Dict],
    current_features: List[Dict],
    current_prd_sections: List[Dict],
    current_vp_steps: List[Dict],
    context_chunks: List[Dict],
    run_id: str
) -> RedTeamOutput:
    """
    Execute research gap analysis with LLM + web search tool.
    """
    logger.info(
        f"Starting research gap analysis with {len(research_chunks)} research chunks, "
        f"{len(current_features)} features, {len(current_prd_sections)} PRD sections, "
        f"{len(current_vp_steps)} VP steps, {len(context_chunks)} context chunks"
    )

    prompt = build_research_gap_prompt(
        research_chunks,
        current_features,
        current_prd_sections,
        current_vp_steps,
        context_chunks
    )

    messages = [
        {"role": "system", "content": "You are a senior product analyst performing gap analysis."},
        {"role": "user", "content": prompt}
    ]

    # Get client
    try:
        client = _get_client()
        logger.info("OpenAI client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        raise
    
    try:
        # First call (with tools)
        logger.info(f"Calling OpenAI API with model {get_settings().REDTEAM_MODEL}")
        response = client.chat.completions.create(
            model=get_settings().REDTEAM_MODEL,
            messages=messages,
            tools=[WEB_SEARCH_TOOL],
            tool_choice="auto",
            temperature=0,
            timeout=30  # 30 second timeout
        )
        logger.info("OpenAI API call completed successfully")

        # Handle tool calls
        while response.choices[0].finish_reason == "tool_calls":
            tool_calls = response.choices[0].message.tool_calls
            messages.append(response.choices[0].message)

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)

                if function_name == "web_search":
                    result = web_search(arguments["query"], arguments["purpose"])
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result)
                    })

            # Continue conversation
            response = client.chat.completions.create(
                model=get_settings().REDTEAM_MODEL,
                messages=messages,
                tools=[WEB_SEARCH_TOOL],
                tool_choice="auto",
                temperature=0,
                timeout=30
            )
    except Exception as e:
        logger.error(f"OpenAI API call failed: {e}")
        raise

    # Parse final response
    content = response.choices[0].message.content

    # Strip markdown code blocks if present
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        data = json.loads(content)
        output = RedTeamOutput(
            insights=[RedTeamInsight(**insight) for insight in data["insights"]],
            model=get_settings().REDTEAM_MODEL,
            prompt_version="red_team_vp_centric_v2",
            schema_version="red_team_v1"
        )
        return output
    except Exception as e:
        logger.error(f"Failed to parse red team output: {e}")
        # Retry with fix-to-schema prompt
        fix_prompt = f"""The previous output failed validation. Please output ONLY valid JSON matching this schema:
{{
  "insights": [
    {{
      "severity": "minor|important|critical",
      "category": "logic|ux|security|data|reporting|scope|ops",
      "title": "string",
      "finding": "string",
      "why": "string",
      "suggested_action": "apply_internally|needs_confirmation",
      "targets": [{{"kind": "feature|prd_section|vp_step", "id": null, "label": "string"}}],
      "evidence": [{{"chunk_id": "uuid", "excerpt": "string", "rationale": "string"}}]
    }}
  ]
}}

Previous output:
{content}

Fix and return valid JSON:"""

        messages.append({"role": "assistant", "content": content})
        messages.append({"role": "user", "content": fix_prompt})

        retry_response = client.chat.completions.create(
            model=get_settings().REDTEAM_MODEL,
            messages=messages,
            temperature=0,
            timeout=30
        )

        retry_content = retry_response.choices[0].message.content
        if "```json" in retry_content:
            retry_content = retry_content.split("```json")[1].split("```")[0].strip()

        data = json.loads(retry_content)
        output = RedTeamOutput(
            insights=[RedTeamInsight(**insight) for insight in data["insights"]],
            model=get_settings().REDTEAM_MODEL,
            prompt_version="red_team_vp_centric_v2",
            schema_version="red_team_v1"
        )
        return output
