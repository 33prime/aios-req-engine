"""Research gap analysis LLM chain with tool calling for web search."""

from openai import OpenAI
from typing import List, Dict, Any
import json
import os

from app.core.schemas_redteam import RedTeamOutput, RedTeamInsight
from app.core.config import get_settings
from app.core.logging import get_logger

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
    Build prompt for research gap analysis.
    """

    # Organize research by section type
    research_by_type = {}
    for chunk in research_chunks:
        section_type = chunk.get("metadata", {}).get("section_type", "unknown")
        if section_type not in research_by_type:
            research_by_type[section_type] = []
        research_by_type[section_type].append(chunk)

    # Build research summary
    research_summary = "## RESEARCH INSIGHTS\n\n"
    for section_type, chunks in research_by_type.items():
        research_summary += f"### {section_type.upper()}\n"
        for chunk in chunks:
            research_summary += f"- {chunk['content'][:500]}...\n"
        research_summary += "\n"

    # Build current state summary
    current_state_summary = "## CURRENT PROJECT STATE\n\n"

    current_state_summary += "### FEATURES\n"
    for feat in current_features:
        current_state_summary += f"- {feat['name']} (MVP: {feat.get('is_mvp', False)}, Category: {feat.get('category', 'N/A')})\n"
    current_state_summary += "\n"

    current_state_summary += "### PRD SECTIONS\n"
    for prd in current_prd_sections:
        current_state_summary += f"- {prd['slug']}: {prd.get('label', 'N/A')}\n"
    current_state_summary += "\n"

    current_state_summary += "### VALUE PATH STEPS\n"
    for vp in current_vp_steps:
        current_state_summary += f"{vp['step_index']}. {vp['label']}: {vp.get('description', '')[:200]}\n"
    current_state_summary += "\n"

    # Context chunks
    context_summary = "## CLIENT CONTEXT\n\n"
    for chunk in context_chunks[:10]:
        context_summary += f"- {chunk['content'][:300]}...\n"

    prompt = f"""You are a senior product analyst performing gap analysis.

Your task is to compare the CURRENT PROJECT STATE against RESEARCH INSIGHTS and identify:
1. **Missing must-have features** from research feature matrix
2. **Missing unique/advanced features** that provide differentiation
3. **Unaddressed market pain points** (macro pressures or company frictions)
4. **Overlooked user personas** or underserved persona needs
5. **Unmitigated risks** from research risk analysis
6. **Misaligned goals/KPIs** vs research recommendations
7. **Weak differentiation** (missing USPs)

{research_summary}

{current_state_summary}

{context_summary}

## INSTRUCTIONS

For each gap you identify:
1. Assign severity: "minor" (nice-to-have), "important" (should-have), or "critical" (must-have)
2. Categorize: "logic", "ux", "security", "data", "reporting", "scope", "ops"
3. Write a clear title (5-10 words)
4. Explain the finding (what's missing or misaligned)
5. Explain why it matters (business impact, user impact, risk)
6. Suggest action: "apply_internally" (update state directly) or "needs_confirmation" (ask client/consultant)
7. Specify targets: which feature, PRD section, or VP step should be updated (use IDs if available, otherwise labels)
8. Provide evidence: cite research chunks or client context

Use the web_search tool if you need to:
- Validate research claims (e.g., market size, competitor features)
- Check technical feasibility of suggested features
- Verify current best practices or standards

Focus on HIGH-IMPACT gaps. Don't flag trivial differences.

Output structured JSON matching the RedTeamOutput schema.
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
            prompt_version="red_team_research_v1",
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
            prompt_version="red_team_research_v1",
            schema_version="red_team_v1"
        )
        return output
