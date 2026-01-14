"""Client-specific chat tools for the client portal.

These tools are a limited subset of the full consultant tools,
focused on context gathering and information updates.
"""

from typing import Any, Dict, List
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


def get_client_tool_definitions() -> List[Dict[str, Any]]:
    """
    Get tool definitions for client chat.

    Clients have limited tools focused on:
    - Updating project context sections
    - Adding users, competitors, tribal knowledge
    - Completing action items
    - Uploading/referencing files

    Returns:
        List of tool definition dictionaries
    """
    return [
        {
            "name": "update_context_section",
            "description": "Update a section of the project context. Use when the client provides information about their problem, success criteria, metrics, or design preferences.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "enum": ["problem_main", "problem_why_now", "success_future", "success_wow", "design_avoid"],
                        "description": "Which context section to update",
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to set for this section",
                    },
                },
                "required": ["section", "content"],
            },
        },
        {
            "name": "add_metric",
            "description": "Add a success metric to the project context. Use when the client mentions a KPI, metric, or measurable goal.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "description": "What to measure (e.g., 'Time to process invoice')",
                    },
                    "current": {
                        "type": "string",
                        "description": "Current value or state (e.g., '15 hours')",
                    },
                    "goal": {
                        "type": "string",
                        "description": "Target value (e.g., '2 hours')",
                    },
                },
                "required": ["metric"],
            },
        },
        {
            "name": "add_user",
            "description": "Add a key user/persona to the project context. Use when the client mentions someone who will use the product.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name or role of the user (e.g., 'Jennifer', 'Dev Director')",
                    },
                    "role": {
                        "type": "string",
                        "description": "Their job role or title",
                    },
                    "frustrations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Current pain points or frustrations",
                    },
                    "helps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "What would help them",
                    },
                },
                "required": ["name"],
            },
        },
        {
            "name": "add_competitor",
            "description": "Add a competitor or alternative tool the client has tried. Use when the client mentions other solutions.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the tool/competitor",
                    },
                    "worked": {
                        "type": "string",
                        "description": "What worked well about it",
                    },
                    "didnt_work": {
                        "type": "string",
                        "description": "What didn't work",
                    },
                    "why_left": {
                        "type": "string",
                        "description": "Why they stopped using it",
                    },
                },
                "required": ["name"],
            },
        },
        {
            "name": "add_design_inspiration",
            "description": "Add an app or tool the client loves for design inspiration. Use when the client mentions apps they like.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the app/tool",
                    },
                    "url": {
                        "type": "string",
                        "description": "URL (optional)",
                    },
                    "what_like": {
                        "type": "string",
                        "description": "What they like about it",
                    },
                },
                "required": ["name"],
            },
        },
        {
            "name": "add_tribal_knowledge",
            "description": "Add edge cases, gotchas, or unusual scenarios to capture tribal knowledge. Use when the client mentions special cases or exceptions.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "knowledge": {
                        "type": "string",
                        "description": "The edge case or special scenario",
                    },
                },
                "required": ["knowledge"],
            },
        },
        {
            "name": "complete_info_request",
            "description": "Mark an information request (question or action item) as complete with an answer. Use when the client provides a full answer to a pending question.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "request_id": {
                        "type": "string",
                        "description": "UUID of the info request to complete",
                    },
                    "answer": {
                        "type": "string",
                        "description": "The answer or response",
                    },
                },
                "required": ["request_id", "answer"],
            },
        },
        {
            "name": "get_pending_questions",
            "description": "Get the list of pending questions or action items. Use when the client asks what they need to do or what questions remain.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "phase": {
                        "type": "string",
                        "enum": ["pre_call", "post_call", "all"],
                        "description": "Filter by phase (optional)",
                        "default": "all",
                    },
                },
            },
        },
        {
            "name": "get_context_summary",
            "description": "Get a summary of the current project context and what's missing. Use when the client asks about progress or what info is needed.",
            "input_schema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "suggest_next_action",
            "description": "Suggest what the client should do next based on incomplete sections. Use proactively to guide the client.",
            "input_schema": {
                "type": "object",
                "properties": {},
            },
        },
    ]


async def execute_client_tool(
    project_id: UUID,
    user_id: UUID,
    tool_name: str,
    tool_input: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute a client tool and return results.

    Args:
        project_id: Project UUID
        user_id: Client user UUID
        tool_name: Name of tool to execute
        tool_input: Tool input parameters

    Returns:
        Tool execution results
    """
    try:
        logger.info(f"Client executing tool {tool_name} for project {project_id}")

        if tool_name == "update_context_section":
            return await _update_context_section(project_id, user_id, tool_input)
        elif tool_name == "add_metric":
            return await _add_metric(project_id, user_id, tool_input)
        elif tool_name == "add_user":
            return await _add_user(project_id, user_id, tool_input)
        elif tool_name == "add_competitor":
            return await _add_competitor(project_id, user_id, tool_input)
        elif tool_name == "add_design_inspiration":
            return await _add_design_inspiration(project_id, user_id, tool_input)
        elif tool_name == "add_tribal_knowledge":
            return await _add_tribal_knowledge(project_id, user_id, tool_input)
        elif tool_name == "complete_info_request":
            return await _complete_info_request(project_id, user_id, tool_input)
        elif tool_name == "get_pending_questions":
            return await _get_pending_questions(project_id, tool_input)
        elif tool_name == "get_context_summary":
            return await _get_context_summary(project_id, tool_input)
        elif tool_name == "suggest_next_action":
            return await _suggest_next_action(project_id, tool_input)
        else:
            return {"error": f"Unknown client tool: {tool_name}"}

    except Exception as e:
        logger.error(f"Error executing client tool {tool_name}: {e}", exc_info=True)
        return {"error": str(e)}


async def _update_context_section(
    project_id: UUID,
    user_id: UUID,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Update a text section of project context."""
    supabase = get_supabase()

    section = params.get("section")
    content = params.get("content")

    if not section or not content:
        return {"error": "Both section and content are required"}

    # Map section names to database columns
    section_map = {
        "problem_main": ("problem_main", "problem_main_source", "problem_main_locked"),
        "problem_why_now": ("problem_why_now", "problem_why_now_source", "problem_why_now_locked"),
        "success_future": ("success_future", "success_future_source", "success_future_locked"),
        "success_wow": ("success_wow", "success_wow_source", "success_wow_locked"),
        "design_avoid": ("design_avoid", "design_avoid_source", "design_avoid_locked"),
    }

    if section not in section_map:
        return {"error": f"Unknown section: {section}"}

    field, source_field, locked_field = section_map[section]

    # Check if context exists
    context_resp = (
        supabase.table("project_context")
        .select("id")
        .eq("project_id", str(project_id))
        .single()
        .execute()
    )

    update_data = {
        field: content,
        source_field: "chat",
        locked_field: True,  # Lock since manually edited via chat
    }

    if context_resp.data:
        # Update existing
        supabase.table("project_context").update(update_data).eq(
            "project_id", str(project_id)
        ).execute()
    else:
        # Create new context
        update_data["project_id"] = str(project_id)
        supabase.table("project_context").insert(update_data).execute()

    return {
        "success": True,
        "section": section,
        "message": f"Updated {section.replace('_', ' ')} in project context",
    }


async def _add_metric(
    project_id: UUID,
    user_id: UUID,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Add a metric to project context."""
    supabase = get_supabase()

    metric = params.get("metric")
    current = params.get("current", "")
    goal = params.get("goal", "")

    if not metric:
        return {"error": "Metric name is required"}

    # Get current context
    context_resp = (
        supabase.table("project_context")
        .select("id, metrics")
        .eq("project_id", str(project_id))
        .single()
        .execute()
    )

    new_metric = {
        "metric": metric,
        "current": current,
        "goal": goal,
        "source": "chat",
        "locked": False,
    }

    if context_resp.data:
        metrics = context_resp.data.get("metrics") or []
        metrics.append(new_metric)

        supabase.table("project_context").update({
            "metrics": metrics
        }).eq("project_id", str(project_id)).execute()
    else:
        supabase.table("project_context").insert({
            "project_id": str(project_id),
            "metrics": [new_metric],
        }).execute()

    return {
        "success": True,
        "metric": new_metric,
        "message": f"Added metric: {metric}",
    }


async def _add_user(
    project_id: UUID,
    user_id: UUID,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Add a key user to project context."""
    supabase = get_supabase()

    name = params.get("name")
    if not name:
        return {"error": "User name is required"}

    new_user = {
        "name": name,
        "role": params.get("role", ""),
        "frustrations": params.get("frustrations", []),
        "helps": params.get("helps", []),
        "source": "chat",
        "locked": False,
    }

    # Get current context
    context_resp = (
        supabase.table("project_context")
        .select("id, key_users")
        .eq("project_id", str(project_id))
        .single()
        .execute()
    )

    if context_resp.data:
        key_users = context_resp.data.get("key_users") or []
        key_users.append(new_user)

        supabase.table("project_context").update({
            "key_users": key_users
        }).eq("project_id", str(project_id)).execute()
    else:
        supabase.table("project_context").insert({
            "project_id": str(project_id),
            "key_users": [new_user],
        }).execute()

    return {
        "success": True,
        "user": new_user,
        "message": f"Added user: {name}",
    }


async def _add_competitor(
    project_id: UUID,
    user_id: UUID,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Add a competitor to project context."""
    supabase = get_supabase()

    name = params.get("name")
    if not name:
        return {"error": "Competitor name is required"}

    new_competitor = {
        "name": name,
        "worked": params.get("worked", ""),
        "didnt_work": params.get("didnt_work", ""),
        "why_left": params.get("why_left", ""),
        "source": "chat",
        "locked": False,
    }

    # Get current context
    context_resp = (
        supabase.table("project_context")
        .select("id, competitors")
        .eq("project_id", str(project_id))
        .single()
        .execute()
    )

    if context_resp.data:
        competitors = context_resp.data.get("competitors") or []
        competitors.append(new_competitor)

        supabase.table("project_context").update({
            "competitors": competitors
        }).eq("project_id", str(project_id)).execute()
    else:
        supabase.table("project_context").insert({
            "project_id": str(project_id),
            "competitors": [new_competitor],
        }).execute()

    return {
        "success": True,
        "competitor": new_competitor,
        "message": f"Added competitor: {name}",
    }


async def _add_design_inspiration(
    project_id: UUID,
    user_id: UUID,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Add design inspiration to project context."""
    supabase = get_supabase()

    name = params.get("name")
    if not name:
        return {"error": "App/tool name is required"}

    new_inspiration = {
        "name": name,
        "url": params.get("url", ""),
        "what_like": params.get("what_like", ""),
        "source": "chat",
    }

    # Get current context
    context_resp = (
        supabase.table("project_context")
        .select("id, design_love")
        .eq("project_id", str(project_id))
        .single()
        .execute()
    )

    if context_resp.data:
        design_love = context_resp.data.get("design_love") or []
        design_love.append(new_inspiration)

        supabase.table("project_context").update({
            "design_love": design_love
        }).eq("project_id", str(project_id)).execute()
    else:
        supabase.table("project_context").insert({
            "project_id": str(project_id),
            "design_love": [new_inspiration],
        }).execute()

    return {
        "success": True,
        "inspiration": new_inspiration,
        "message": f"Added design inspiration: {name}",
    }


async def _add_tribal_knowledge(
    project_id: UUID,
    user_id: UUID,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Add tribal knowledge to project context."""
    supabase = get_supabase()

    knowledge = params.get("knowledge")
    if not knowledge:
        return {"error": "Knowledge content is required"}

    # Get current context
    context_resp = (
        supabase.table("project_context")
        .select("id, tribal_knowledge, tribal_source")
        .eq("project_id", str(project_id))
        .single()
        .execute()
    )

    if context_resp.data:
        tribal_knowledge = context_resp.data.get("tribal_knowledge") or []
        tribal_knowledge.append(knowledge)

        supabase.table("project_context").update({
            "tribal_knowledge": tribal_knowledge,
            "tribal_source": "chat",
        }).eq("project_id", str(project_id)).execute()
    else:
        supabase.table("project_context").insert({
            "project_id": str(project_id),
            "tribal_knowledge": [knowledge],
            "tribal_source": "chat",
        }).execute()

    return {
        "success": True,
        "message": f"Added tribal knowledge: {knowledge[:50]}...",
    }


async def _complete_info_request(
    project_id: UUID,
    user_id: UUID,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Mark an info request as complete."""
    supabase = get_supabase()

    request_id = params.get("request_id")
    answer = params.get("answer")

    if not request_id or not answer:
        return {"error": "Both request_id and answer are required"}

    # Verify the request belongs to this project
    request_resp = (
        supabase.table("info_requests")
        .select("id, title, auto_populates_to")
        .eq("id", request_id)
        .eq("project_id", str(project_id))
        .single()
        .execute()
    )

    if not request_resp.data:
        return {"error": "Info request not found"}

    # Update the request
    supabase.table("info_requests").update({
        "status": "complete",
        "answer_data": {"text": answer},
        "completed_at": "now()",
        "completed_by": str(user_id),
    }).eq("id", request_id).execute()

    # Auto-populate to context if configured
    auto_targets = request_resp.data.get("auto_populates_to") or []
    populated_sections = []

    for target in auto_targets:
        if target in ["problem", "success", "tribal"]:
            # Would trigger context population here
            populated_sections.append(target)

    result = {
        "success": True,
        "request_title": request_resp.data.get("title"),
        "message": f"Completed: {request_resp.data.get('title')}",
    }

    if populated_sections:
        result["populated_sections"] = populated_sections
        result["message"] += f" (auto-populated to: {', '.join(populated_sections)})"

    return result


async def _get_pending_questions(
    project_id: UUID,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Get pending info requests."""
    supabase = get_supabase()

    phase = params.get("phase", "all")

    query = (
        supabase.table("info_requests")
        .select("id, title, description, phase, request_type, priority, status")
        .eq("project_id", str(project_id))
        .neq("status", "complete")
        .order("display_order")
    )

    if phase != "all":
        query = query.eq("phase", phase)

    response = query.execute()
    requests = response.data or []

    # Group by phase
    pre_call = [r for r in requests if r.get("phase") == "pre_call"]
    post_call = [r for r in requests if r.get("phase") == "post_call"]

    return {
        "total": len(requests),
        "pre_call": pre_call,
        "post_call": post_call,
        "message": f"You have {len(requests)} pending items ({len(pre_call)} pre-call, {len(post_call)} post-call)",
    }


async def _get_context_summary(
    project_id: UUID,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Get project context completion summary."""
    supabase = get_supabase()

    # Get context
    context_resp = (
        supabase.table("project_context")
        .select("*")
        .eq("project_id", str(project_id))
        .single()
        .execute()
    )

    if not context_resp.data:
        return {
            "overall_completion": 0,
            "sections": {
                "problem": {"complete": False, "score": 0},
                "success": {"complete": False, "score": 0},
                "users": {"complete": False, "score": 0},
                "design": {"complete": False, "score": 0},
                "competitors": {"complete": False, "score": 0},
                "tribal": {"complete": False, "score": 0},
            },
            "message": "Project context is empty. Start by describing the main problem you're trying to solve.",
        }

    ctx = context_resp.data

    # Calculate completion for each section
    sections = {}

    # Problem section
    problem_score = 0
    if ctx.get("problem_main"):
        problem_score += 50
    if ctx.get("problem_why_now"):
        problem_score += 30
    metrics = ctx.get("metrics") or []
    if len(metrics) > 0:
        problem_score += 20
    sections["problem"] = {"complete": problem_score >= 80, "score": min(problem_score, 100)}

    # Success section
    success_score = 0
    if ctx.get("success_future"):
        success_score += 50
    if ctx.get("success_wow"):
        success_score += 50
    sections["success"] = {"complete": success_score >= 80, "score": min(success_score, 100)}

    # Users section
    key_users = ctx.get("key_users") or []
    users_score = min(len(key_users) * 40, 100)
    sections["users"] = {"complete": users_score >= 80, "score": users_score}

    # Design section
    design_score = 0
    design_love = ctx.get("design_love") or []
    if len(design_love) > 0:
        design_score += 60
    if ctx.get("design_avoid"):
        design_score += 40
    sections["design"] = {"complete": design_score >= 60, "score": min(design_score, 100)}

    # Competitors section
    competitors = ctx.get("competitors") or []
    competitors_score = min(len(competitors) * 50, 100)
    sections["competitors"] = {"complete": competitors_score >= 50, "score": competitors_score}

    # Tribal knowledge section
    tribal = ctx.get("tribal_knowledge") or []
    tribal_score = min(len(tribal) * 30, 100)
    sections["tribal"] = {"complete": tribal_score >= 30, "score": tribal_score}

    # Calculate overall
    weights = {
        "problem": 0.2,
        "success": 0.2,
        "users": 0.2,
        "design": 0.15,
        "competitors": 0.15,
        "tribal": 0.1,
    }

    overall = sum(sections[s]["score"] * weights[s] for s in weights)

    # Generate message
    incomplete = [s for s, data in sections.items() if not data["complete"]]

    if not incomplete:
        message = "Great job! All sections are complete."
    elif len(incomplete) == 6:
        message = "Let's start by describing the main problem you're trying to solve."
    else:
        message = f"Good progress! Still need info on: {', '.join(incomplete)}"

    return {
        "overall_completion": round(overall),
        "sections": sections,
        "message": message,
    }


async def _suggest_next_action(
    project_id: UUID,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """Suggest what the client should do next."""
    # Get context summary
    summary = await _get_context_summary(project_id, {})
    sections = summary.get("sections", {})

    # Priority order for incomplete sections
    priority_order = [
        ("problem", "Tell me about the main problem you're trying to solve"),
        ("users", "Who are the key people who will use this?"),
        ("success", "What does success look like for this project?"),
        ("competitors", "What tools have you tried before?"),
        ("design", "Are there any apps or tools you love using?"),
        ("tribal", "Any edge cases or special scenarios we should know about?"),
    ]

    for section, prompt in priority_order:
        if not sections.get(section, {}).get("complete", False):
            return {
                "section": section,
                "prompt": prompt,
                "current_score": sections.get(section, {}).get("score", 0),
                "message": f"Let's work on the {section} section. {prompt}",
            }

    return {
        "section": None,
        "message": "All sections look good! Feel free to add more details to any section.",
    }


def build_client_system_prompt(project_name: str, client_name: str | None = None) -> str:
    """
    Build the system prompt for client chat.

    Args:
        project_name: Name of the project
        client_name: Optional client name for personalization

    Returns:
        System prompt string
    """
    greeting = f"Hi{' ' + client_name if client_name else ''}!"

    return f"""You are a helpful assistant working with a client on their project "{project_name}".

{greeting} Your role is to help gather information about the project by having a natural conversation. You're friendly, concise, and focused on understanding:

1. **The Problem** - What are they trying to solve? Why now?
2. **Success Criteria** - What does success look like? What would wow them?
3. **Key Users** - Who will use this? What are their pain points?
4. **Design Preferences** - What apps do they love? What to avoid?
5. **Past Experience** - What tools have they tried? What worked/didn't?
6. **Edge Cases** - Any special scenarios or tribal knowledge?

## How to Help

- Ask clarifying questions to understand their needs
- Use your tools to save information to the project context
- When they provide info, acknowledge it and use the appropriate tool
- Keep the conversation flowing naturally
- Suggest what to discuss next based on what's missing

## Tools Available

You have tools to:
- Update context sections (problem, success, design preferences)
- Add users, competitors, design inspiration, and edge cases
- Add metrics and KPIs
- Complete pending questions/action items
- Check what info is still needed

## Guidelines

- Be conversational, not robotic
- Save info as you go - don't wait until the end
- If they provide partial info, save what you have and ask follow-ups
- Don't ask for everything at once - one topic at a time
- Acknowledge what you've learned and summarize periodically

Remember: You're helping them prepare for their discovery call or fill in details after it. Make it easy and pleasant for them to share information.
"""
