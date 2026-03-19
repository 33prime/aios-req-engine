"""Tests for the Intelligence Workbench agent execution chain and API."""

import pytest

from app.core.schemas_agents import (
    AgentExecuteRequest,
    AgentExecuteResponse,
    AgentExampleResponse,
)
from app.chains.execute_agent_demo import EXAMPLE_INPUTS, _TOOLS, _SYSTEM_PROMPTS


# ── Schema validation tests ──────────────────────────────────────


class TestAgentSchemas:
    def test_execute_request_valid(self):
        req = AgentExecuteRequest(
            agent_type="classifier",
            agent_name="Entity Classifier",
            input_text="Some meeting notes here",
        )
        assert req.agent_type == "classifier"
        assert req.step_id is None

    def test_execute_request_with_step_id(self):
        req = AgentExecuteRequest(
            agent_type="processor",
            agent_name="Signal Processor",
            input_text="Email content",
            step_id="abc-123",
        )
        assert req.step_id == "abc-123"

    def test_execute_request_rejects_invalid_type(self):
        with pytest.raises(Exception):
            AgentExecuteRequest(
                agent_type="invalid_type",
                agent_name="Bad Agent",
                input_text="test",
            )

    def test_execute_request_rejects_empty_input(self):
        with pytest.raises(Exception):
            AgentExecuteRequest(
                agent_type="classifier",
                agent_name="Test",
                input_text="",
            )

    def test_execute_response_valid(self):
        resp = AgentExecuteResponse(
            output={"entities": [], "summary": "test"},
            execution_time_ms=150,
            model="claude-haiku-4-5-20251001",
            agent_type="classifier",
        )
        assert resp.execution_time_ms == 150

    def test_example_response_valid(self):
        resp = AgentExampleResponse(
            agent_type="processor",
            example_input="Some example",
            description="Test example",
        )
        assert resp.agent_type == "processor"


# ── Chain configuration tests ────────────────────────────────────


class TestChainConfig:
    def test_all_agent_types_have_tools(self):
        expected = {"classifier", "matcher", "predictor", "watcher", "generator", "processor"}
        assert set(_TOOLS.keys()) == expected

    def test_all_agent_types_have_prompts(self):
        assert set(_SYSTEM_PROMPTS.keys()) == set(_TOOLS.keys())

    def test_all_agent_types_have_examples(self):
        assert set(EXAMPLE_INPUTS.keys()) == set(_TOOLS.keys())

    def test_tool_schemas_have_required_fields(self):
        for agent_type, tool in _TOOLS.items():
            assert "name" in tool, f"{agent_type} tool missing name"
            assert "description" in tool, f"{agent_type} tool missing description"
            assert "input_schema" in tool, f"{agent_type} tool missing input_schema"
            schema = tool["input_schema"]
            assert schema["type"] == "object"
            assert "properties" in schema
            assert "required" in schema

    def test_examples_are_non_empty(self):
        for agent_type, (description, example_text) in EXAMPLE_INPUTS.items():
            assert len(description) > 10, f"{agent_type} example description too short"
            assert len(example_text) > 50, f"{agent_type} example text too short"

    def test_classifier_tool_schema(self):
        tool = _TOOLS["classifier"]
        assert tool["name"] == "classification_output"
        props = tool["input_schema"]["properties"]
        assert "entities" in props
        assert "summary" in props

    def test_watcher_severity_enum(self):
        tool = _TOOLS["watcher"]
        alert_props = tool["input_schema"]["properties"]["alerts"]["items"]["properties"]
        assert alert_props["severity"]["enum"] == ["critical", "warning", "advisory"]

    def test_processor_has_probes(self):
        tool = _TOOLS["processor"]
        props = tool["input_schema"]["properties"]
        assert "probes" in props
        assert "entities" in props


# ── Prompt blocks test ───────────────────────────────────────────


class TestPromptBlocks:
    def test_workbench_page_guidance_exists(self):
        from app.context.prompt_blocks import PAGE_GUIDANCE

        assert "intelligence:workbench" in PAGE_GUIDANCE
        guidance = PAGE_GUIDANCE["intelligence:workbench"]
        assert "Intelligence Workbench" in guidance
        assert "AI architecture" in guidance


# ── Prompt compiler test ─────────────────────────────────────────


class TestPromptCompilerAgent:
    def test_agent_entity_enrichment(self):
        """When focused_entity.type == 'agent' with ai_config, prompt includes agent details."""
        from app.context.prompt_compiler import compile_prompt, CognitiveFrame
        from app.context.prompt_compiler import (
            CognitiveMode,
            ConfidencePosture,
            Scope,
            TemporalEmphasis,
        )
        from app.context.project_awareness import ProjectAwareness

        frame = CognitiveFrame(
            mode=CognitiveMode.SYNTHESIZE,
            temporal=TemporalEmphasis.PRESENT_STATE,
            scope=Scope.CONTEXTUAL,
            posture=ConfidencePosture.EXPLORATORY,
        )

        awareness = ProjectAwareness(
            project_name="Test Project",
            active_phase="solution_flow",
        )

        focused_entity = {
            "type": "agent",
            "data": {
                "id": "step-123",
                "title": "Risk Watcher",
                "goal": "Monitor project risks",
                "ai_config": {
                    "role": "Risk monitoring agent",
                    "agent_type": "watcher",
                    "behaviors": ["monitor", "alert", "detect"],
                    "data_requirements": [
                        {"source": "sprint reviews"},
                        {"source": "jira updates"},
                    ],
                },
            },
        }

        result = compile_prompt(
            frame=frame,
            awareness=awareness,
            page_context="intelligence:workbench",
            focused_entity=focused_entity,
            retrieval_context="",
            solution_flow_ctx=None,
            confidence_state={},
            horizon_state={},
        )

        # Check dynamic block contains agent-specific context
        assert "Risk Watcher" in result.dynamic_block
        assert "Agent Type: watcher" in result.dynamic_block
        assert "Role: Risk monitoring agent" in result.dynamic_block
        assert "Behaviors:" in result.dynamic_block
        assert "Data Sources:" in result.dynamic_block
        # Check page guidance is included
        assert "Intelligence Workbench" in result.dynamic_block
