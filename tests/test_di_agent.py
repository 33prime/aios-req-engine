"""Unit tests for DI Agent reasoning and tool calling.

Tests the DI Agent's core reasoning engine, response parsing,
tool execution, and orchestration logic.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.agents.di_agent import (
    _extract_reasoning_from_text,
    _parse_agent_response,
    invoke_di_agent,
)
from app.agents.di_agent_tools import execute_di_tool
from app.agents.di_agent_types import (
    ConsultantGuidance,
    DIAgentResponse,
    GateAssessment,
    QuestionToAsk,
    ReadinessPhase,
    ToolCall,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def project_id():
    """Sample project UUID."""
    return uuid4()


@pytest.fixture
def mock_readiness_empty():
    """Mock readiness for empty project."""
    return MagicMock(
        score=5.0,
        phase="insufficient",
        total_readiness=5.0,
        gate_score=0,
        gates={
            "prototype_gates": {
                "core_pain": {
                    "name": "Core Pain",
                    "satisfied": False,
                    "confidence": 0.0,
                    "missing": ["Core pain not yet extracted"],
                },
                "primary_persona": {
                    "name": "Primary Persona",
                    "satisfied": False,
                    "confidence": 0.0,
                    "missing": ["Primary persona not yet identified"],
                },
            },
            "build_gates": {},
        },
        blocking_gates=["core_pain", "primary_persona"],
        client_signals_count=2,
        prototype_ready=False,
        build_ready=False,
        next_milestone="Extract core pain",
    )


@pytest.fixture
def mock_readiness_partial():
    """Mock readiness for project with some gates satisfied."""
    return MagicMock(
        score=35.0,
        phase="prototype_ready",
        total_readiness=35.0,
        gate_score=45,
        gates={
            "prototype_gates": {
                "core_pain": {
                    "name": "Core Pain",
                    "satisfied": True,
                    "confidence": 0.85,
                    "missing": [],
                },
                "primary_persona": {
                    "name": "Primary Persona",
                    "satisfied": False,
                    "confidence": 0.3,
                    "missing": ["Confidence too low - needs validation"],
                },
            },
            "build_gates": {},
        },
        blocking_gates=["primary_persona"],
        client_signals_count=8,
        prototype_ready=False,
        build_ready=False,
        next_milestone="Identify primary persona",
    )


@pytest.fixture
def mock_anthropic_tool_call_response():
    """Mock Anthropic API response with tool call."""
    # Create text block with text attribute (use spec to control attributes)
    text_block = MagicMock(spec=['text'])
    text_block.text = "OBSERVE: Current state shows core pain not yet extracted with 5 unanalyzed signals available.\n\nTHINK: The biggest gap is missing core pain definition. Without this, we cannot define persona or wow moment. This is the highest-priority blocker.\n\nDECIDE: I will extract core pain from available signals to unlock foundation gates and enable downstream work."

    # Create tool block with type, name, input attributes
    tool_block = MagicMock(spec=['type', 'name', 'input'])
    tool_block.type = "tool_use"
    tool_block.name = "extract_core_pain"
    tool_block.input = {"depth": "standard"}

    response = MagicMock()
    response.content = [text_block, tool_block]

    return response


@pytest.fixture
def mock_anthropic_stop_response():
    """Mock Anthropic API response with stop_with_guidance."""
    text_block = MagicMock(spec=['text'])
    text_block.text = "OBSERVE: All foundation gates are satisfied with high confidence. Project is prototype-ready with score of 75/100.\n\nTHINK: No critical gaps remain that block progress. Foundation is solid enough to build prototype and test with real users. Continuing extraction would provide diminishing returns.\n\nDECIDE: Stop and provide guidance to consultant on next steps for building prototype."

    tool_block = MagicMock(spec=['type', 'name', 'input'])
    tool_block.type = "tool_use"
    tool_block.name = "stop_with_guidance"
    tool_block.input = {
        "reason": "Foundation is solid - ready for prototype",
        "what_would_help": [],
        "recommended_next": "Build prototype and test with users",
    }

    response = MagicMock()
    response.content = [text_block, tool_block]

    return response


@pytest.fixture
def mock_anthropic_guidance_response():
    """Mock Anthropic API response with suggest_discovery_questions."""
    text_block = MagicMock(spec=['text'])
    text_block.text = "OBSERVE: Core pain defined with good confidence (0.85) but primary persona confidence is low (0.3). This creates uncertainty about who we're building for.\n\nTHINK: We need more signal about who feels this pain most acutely. Without clear persona, wow moment and features will be too generic. This is the next blocker after core pain.\n\nDECIDE: Suggest targeted discovery questions to identify primary persona with higher confidence."

    tool_block = MagicMock(spec=['type', 'name', 'input'])
    tool_block.type = "tool_use"
    tool_block.name = "suggest_discovery_questions"
    tool_block.input = {"focus_area": "primary_persona"}

    response = MagicMock()
    response.content = [text_block, tool_block]

    return response


@pytest.fixture
def mock_anthropic_no_tools_response():
    """Mock Anthropic API response with no tool calls (fallback to guidance)."""
    text_block = MagicMock(spec=['text'])
    text_block.text = "OBSERVE: Project is in early discovery with only 2 signals collected. Signals are too sparse to extract foundation elements with confidence.\n\nTHINK: Need more conversation with client before we can extract foundation. Premature extraction would result in low-confidence outputs that need rework. Better to wait for richer signal.\n\nDECIDE: Wait for more signals to be collected through discovery conversations. Current data insufficient for confident extraction. Recommend continuing discovery."

    response = MagicMock()
    response.content = [text_block]

    return response


# =============================================================================
# Test: Reasoning Extraction
# =============================================================================


class TestExtractReasoningFromText:
    """Test _extract_reasoning_from_text() parsing."""

    def test_extracts_structured_sections(self):
        """Extracts OBSERVE, THINK, DECIDE when clearly marked."""
        text = """
# OBSERVE
Current state has no core pain defined.

# THINK
Without core pain, we cannot identify persona.

# DECIDE
Extract core pain from signals.
"""

        observation, thinking, decision = _extract_reasoning_from_text(text)

        assert "observe" in observation.lower()
        assert "think" in thinking.lower()
        assert "decide" in decision.lower()

    def test_handles_alternative_headers(self):
        """Handles 'OBSERVATION', 'THINKING', 'DECISION' variants."""
        text = """
OBSERVATION: No foundation gates satisfied.

THINKING: Biggest gap is core pain.

DECISION: Run extract_core_pain tool.
"""

        observation, thinking, decision = _extract_reasoning_from_text(text)

        assert len(observation) > 0
        assert len(thinking) > 0
        assert len(decision) > 0

    def test_fallback_when_no_sections(self):
        """Falls back to splitting by paragraphs when sections not found."""
        text = "This is the observation.\n\nThis is the thinking.\n\nThis is the decision."

        observation, thinking, decision = _extract_reasoning_from_text(text)

        assert "observation" in observation.lower()
        assert "thinking" in thinking.lower()
        assert "decision" in decision.lower()

    def test_handles_empty_text(self):
        """Handles empty text gracefully."""
        observation, thinking, decision = _extract_reasoning_from_text("")

        assert observation == ""
        assert thinking == ""
        assert decision == ""


# =============================================================================
# Test: Response Parsing
# =============================================================================


class TestParseAgentResponse:
    """Test _parse_agent_response() logic."""

    def test_parses_tool_call_response(self, mock_anthropic_tool_call_response):
        """Parses response with tool_use block into tool_call action."""
        response = _parse_agent_response(
            mock_anthropic_tool_call_response,
            readiness_before=5,
            readiness_after=5,
            gates_affected=[],
        )

        assert isinstance(response, DIAgentResponse)
        assert response.action_type == "tool_call"
        assert response.tools_called is not None
        assert len(response.tools_called) == 1
        assert response.tools_called[0].tool_name == "extract_core_pain"
        assert response.tools_called[0].tool_args == {"depth": "standard"}
        assert "core pain not yet" in response.observation.lower() or "core pain" in response.observation.lower()

    def test_parses_stop_response(self, mock_anthropic_stop_response):
        """Parses stop_with_guidance into stop action."""
        response = _parse_agent_response(
            mock_anthropic_stop_response,
            readiness_before=75,
            readiness_after=75,
            gates_affected=[],
        )

        assert response.action_type == "stop"
        assert response.stop_reason is not None
        assert "prototype" in response.stop_reason.lower() or "ready" in response.stop_reason.lower()

    def test_parses_guidance_response(self, mock_anthropic_guidance_response):
        """Parses suggest_discovery_questions into guidance action."""
        response = _parse_agent_response(
            mock_anthropic_guidance_response,
            readiness_before=25,
            readiness_after=25,
            gates_affected=[],
        )

        assert response.action_type == "guidance"
        assert response.guidance is not None
        assert isinstance(response.guidance, ConsultantGuidance)

    def test_fallback_to_guidance_when_no_tools(self, mock_anthropic_no_tools_response):
        """Falls back to guidance action when no tools called."""
        response = _parse_agent_response(
            mock_anthropic_no_tools_response,
            readiness_before=5,
            readiness_after=5,
            gates_affected=[],
        )

        assert response.action_type == "guidance"
        assert response.guidance is not None

    def test_extracts_reasoning_trace(self, mock_anthropic_tool_call_response):
        """Extracts observation, thinking, decision from text."""
        response = _parse_agent_response(
            mock_anthropic_tool_call_response,
            readiness_before=5,
            readiness_after=5,
            gates_affected=[],
        )

        assert len(response.observation) > 0
        assert len(response.thinking) > 0
        assert len(response.decision) > 0


# =============================================================================
# Test: Tool Execution
# =============================================================================


class TestExecuteDITool:
    """Test execute_di_tool() routing and execution."""

    @pytest.mark.anyio
    @patch("app.agents.di_agent_tools.extract_core_pain")
    async def test_executes_extract_core_pain(self, mock_extract, project_id):
        """Routes extract_core_pain to correct extractor."""
        mock_pain = MagicMock(
            statement="Customer success teams spend 10+ hours per week tracking churn",
            trigger="When a customer stops engaging",
            stakes="$50K-200K MRR lost per month",
            who_feels_it="CSMs",
            confidence=0.85,
        )
        mock_extract.return_value = mock_pain

        result = await execute_di_tool(
            tool_name="extract_core_pain",
            tool_args={"depth": "standard"},
            project_id=project_id,
        )

        assert result["success"] is True
        assert "statement" in result["data"]
        assert result["data"]["confidence"] == 0.85
        mock_extract.assert_called_once()

    @pytest.mark.anyio
    @patch("app.agents.di_agent_tools.extract_primary_persona")
    async def test_executes_extract_primary_persona(self, mock_extract, project_id):
        """Routes extract_primary_persona to correct extractor."""
        # Create mock with actual attribute values, not relying on MagicMock auto-creation
        mock_persona = MagicMock()
        mock_persona.name = "Sarah Chen"
        mock_persona.role = "Customer Success Manager"
        mock_persona.confidence = 0.8
        mock_persona.context = "Manages 50+ enterprise accounts"
        mock_persona.pain_experienced = "Manual churn tracking"
        mock_persona.current_behavior = "Uses spreadsheets"
        mock_persona.desired_outcome = "Automated risk detection"
        mock_extract.return_value = mock_persona

        result = await execute_di_tool(
            tool_name="extract_primary_persona",
            tool_args={},
            project_id=project_id,
        )

        assert result["success"] is True
        assert result["data"]["name"] == "Sarah Chen"
        assert result["data"]["role"] == "Customer Success Manager"

    @pytest.mark.anyio
    @patch("app.agents.di_agent_tools.run_strategic_foundation")
    async def test_executes_run_foundation(self, mock_run, project_id):
        """Routes run_foundation to strategic foundation builder."""
        mock_run.return_value = {
            "features_count": 5,
            "personas_count": 2,
            "vp_steps_count": 8,
            "prd_sections_count": 4,
            "stakeholders_count": 3,
        }

        result = await execute_di_tool(
            tool_name="run_foundation",
            tool_args={},
            project_id=project_id,
        )

        assert result["success"] is True
        assert result["data"]["features_count"] == 5
        assert result["data"]["personas_count"] == 2

    @pytest.mark.anyio
    async def test_handles_unknown_tool(self, project_id):
        """Returns error for unknown tool name."""
        result = await execute_di_tool(
            tool_name="nonexistent_tool",
            tool_args={},
            project_id=project_id,
        )

        assert result["success"] is False
        assert "Unknown tool" in result["error"]

    @pytest.mark.anyio
    @patch("app.agents.di_agent_tools.extract_core_pain")
    async def test_handles_tool_execution_error(self, mock_extract, project_id):
        """Handles tool execution errors gracefully."""
        mock_extract.side_effect = Exception("LLM API error")

        result = await execute_di_tool(
            tool_name="extract_core_pain",
            tool_args={},
            project_id=project_id,
        )

        assert result["success"] is False
        assert "LLM API error" in result["error"]


# =============================================================================
# Test: Agent Orchestration
# =============================================================================


class TestInvokeDIAgent:
    """Test invoke_di_agent() full orchestration."""

    @pytest.mark.anyio
    @patch("app.agents.di_agent.Anthropic")
    @patch("app.agents.di_agent.compute_readiness")
    @patch("app.agents.di_agent.get_state_snapshot")
    @patch("app.agents.di_agent.get_di_cache")
    @patch("app.agents.di_agent.is_cache_valid")
    @patch("app.agents.di_agent.get_unanalyzed_signals")
    @patch("app.agents.di_agent.log_agent_invocation")
    async def test_orchestrates_full_agent_flow(
        self,
        mock_log,
        mock_signals,
        mock_cache_valid,
        mock_cache,
        mock_snapshot,
        mock_readiness,
        mock_anthropic_class,
        project_id,
        mock_readiness_empty,
        mock_anthropic_tool_call_response,
    ):
        """Tests complete agent invocation flow."""
        # Setup mocks
        mock_readiness.return_value = mock_readiness_empty
        mock_snapshot.return_value = "Foundation: None\nEntities: []"  # String snapshot
        mock_cache.return_value = None
        mock_cache_valid.return_value = False
        mock_signals.return_value = [MagicMock(id="sig1"), MagicMock(id="sig2")]  # Return list, not int

        # Mock Anthropic client
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_tool_call_response
        mock_anthropic_class.return_value = mock_client

        # Invoke agent
        response = await invoke_di_agent(
            project_id=project_id,
            trigger="new_signal",
            trigger_context="5 new signals added",
        )

        # Verify orchestration
        assert isinstance(response, DIAgentResponse)
        assert response.action_type == "tool_call"
        assert response.readiness_before == 5

        # Verify state loading was called
        mock_readiness.assert_called_once_with(project_id)
        mock_snapshot.assert_called_once()
        mock_signals.assert_called_once()

        # Verify LLM was called
        mock_client.messages.create.assert_called_once()
        call_args = mock_client.messages.create.call_args

        # Verify prompt construction included key elements
        messages = call_args.kwargs["messages"]
        assert len(messages) > 0
        user_message = messages[0]["content"]
        assert "5" in user_message or "score" in user_message.lower()  # Includes readiness

        # Verify logging
        mock_log.assert_called_once()

    @pytest.mark.anyio
    @patch("app.agents.di_agent.Anthropic")
    @patch("app.agents.di_agent.compute_readiness")
    @patch("app.agents.di_agent.get_state_snapshot")
    @patch("app.agents.di_agent.get_di_cache")
    @patch("app.agents.di_agent.is_cache_valid")
    @patch("app.agents.di_agent.get_unanalyzed_signals")
    @patch("app.agents.di_agent.log_agent_invocation")
    async def test_handles_guidance_trigger(
        self,
        mock_log,
        mock_signals,
        mock_cache_valid,
        mock_cache,
        mock_snapshot,
        mock_readiness,
        mock_anthropic_class,
        project_id,
        mock_readiness_partial,
        mock_anthropic_guidance_response,
    ):
        """Tests agent providing guidance when more signal needed."""
        # Setup mocks
        mock_readiness.return_value = mock_readiness_partial
        mock_snapshot.return_value = "Foundation: core_pain defined\nEntities: []"
        mock_cache.return_value = None
        mock_cache_valid.return_value = False
        mock_signals.return_value = [MagicMock(id="sig1")]  # Return list

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_guidance_response
        mock_anthropic_class.return_value = mock_client

        # Invoke agent
        response = await invoke_di_agent(
            project_id=project_id,
            trigger="user_request",
            specific_request="What questions should I ask the client?",
        )

        # Verify guidance response
        assert response.action_type == "guidance"
        assert response.guidance is not None
        assert isinstance(response.guidance, ConsultantGuidance)

    @pytest.mark.anyio
    @patch("app.agents.di_agent.Anthropic")
    @patch("app.agents.di_agent.compute_readiness")
    @patch("app.agents.di_agent.get_state_snapshot")
    @patch("app.agents.di_agent.get_di_cache")
    @patch("app.agents.di_agent.is_cache_valid")
    @patch("app.agents.di_agent.get_unanalyzed_signals")
    @patch("app.agents.di_agent.log_agent_invocation")
    async def test_handles_stop_when_ready(
        self,
        mock_log,
        mock_signals,
        mock_cache_valid,
        mock_cache,
        mock_snapshot,
        mock_readiness,
        mock_anthropic_class,
        project_id,
        mock_anthropic_stop_response,
    ):
        """Tests agent stopping when project is ready."""
        # Setup high readiness
        mock_high_readiness = MagicMock(
            score=75.0,
            phase="build_ready",
            total_readiness=75.0,
            gate_score=75,
            gates={
                "prototype_gates": {
                    "core_pain": {"name": "Core Pain", "satisfied": True, "confidence": 0.9, "missing": []},
                    "primary_persona": {"name": "Primary Persona", "satisfied": True, "confidence": 0.85, "missing": []},
                    "wow_moment": {"name": "Wow Moment", "satisfied": True, "confidence": 0.8, "missing": []},
                },
                "build_gates": {
                    "business_case": {"name": "Business Case", "satisfied": True, "confidence": 0.85, "missing": []},
                },
            },
            blocking_gates=[],
            client_signals_count=15,
            prototype_ready=True,
            build_ready=True,
            next_milestone="Build MVP",
        )
        mock_readiness.return_value = mock_high_readiness
        mock_snapshot.return_value = "Foundation: complete\nEntities: [features, personas]"
        mock_cache.return_value = None
        mock_cache_valid.return_value = True
        mock_signals.return_value = []  # Return empty list

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_stop_response
        mock_anthropic_class.return_value = mock_client

        # Invoke agent
        response = await invoke_di_agent(
            project_id=project_id,
            trigger="scheduled",
        )

        # Verify stop response
        assert response.action_type == "stop"
        assert response.stop_reason is not None


# =============================================================================
# Test: Integration Scenarios
# =============================================================================


class TestDIAgentScenarios:
    """Test realistic DI Agent scenarios."""

    @pytest.mark.anyio
    @patch("app.agents.di_agent.Anthropic")
    @patch("app.agents.di_agent.compute_readiness")
    @patch("app.agents.di_agent.get_state_snapshot")
    @patch("app.agents.di_agent.get_di_cache")
    @patch("app.agents.di_agent.is_cache_valid")
    @patch("app.agents.di_agent.get_unanalyzed_signals")
    @patch("app.agents.di_agent.log_agent_invocation")
    async def test_scenario_empty_project_first_signal(
        self,
        mock_log,
        mock_signals,
        mock_cache_valid,
        mock_cache,
        mock_snapshot,
        mock_readiness,
        mock_anthropic_class,
        project_id,
        mock_readiness_empty,
        mock_anthropic_tool_call_response,
    ):
        """Scenario: Empty project receives first signal, agent extracts core pain."""
        mock_readiness.return_value = mock_readiness_empty
        mock_snapshot.return_value = "Foundation: None\nEntities: []"
        mock_cache.return_value = None
        mock_cache_valid.return_value = False
        mock_signals.return_value = [MagicMock(id="first_signal")]  # First signal as list

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_tool_call_response
        mock_anthropic_class.return_value = mock_client

        response = await invoke_di_agent(
            project_id=project_id,
            trigger="new_signal",
            trigger_context="First discovery call notes added",
        )

        # Should trigger extraction
        assert response.action_type == "tool_call"
        assert any(
            tc.tool_name == "extract_core_pain" for tc in response.tools_called
        )

    @pytest.mark.anyio
    @patch("app.agents.di_agent.Anthropic")
    @patch("app.agents.di_agent.compute_readiness")
    @patch("app.agents.di_agent.get_state_snapshot")
    @patch("app.agents.di_agent.get_di_cache")
    @patch("app.agents.di_agent.is_cache_valid")
    @patch("app.agents.di_agent.get_unanalyzed_signals")
    @patch("app.agents.di_agent.log_agent_invocation")
    async def test_scenario_low_confidence_persona(
        self,
        mock_log,
        mock_signals,
        mock_cache_valid,
        mock_cache,
        mock_snapshot,
        mock_readiness,
        mock_anthropic_class,
        project_id,
        mock_readiness_partial,
        mock_anthropic_guidance_response,
    ):
        """Scenario: Persona defined but low confidence, agent suggests questions."""
        mock_readiness.return_value = mock_readiness_partial  # Has persona with low confidence
        mock_snapshot.return_value = "Foundation: core_pain=high, primary_persona=low\nEntities: []"
        mock_cache.return_value = None
        mock_cache_valid.return_value = False
        mock_signals.return_value = [MagicMock(id=f"sig{i}") for i in range(3)]  # 3 signals as list

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_guidance_response
        mock_anthropic_class.return_value = mock_client

        response = await invoke_di_agent(
            project_id=project_id,
            trigger="pre_call",
            trigger_context="Client call in 30 minutes",
        )

        # Should provide guidance with questions
        assert response.action_type == "guidance"
        assert response.guidance is not None

    def test_tool_call_object_serialization(self):
        """Tests ToolCall Pydantic model serialization."""
        tool_call = ToolCall(
            tool_name="extract_core_pain",
            tool_args={"depth": "standard"},
            result={"statement": "Customer churn is unpredictable", "confidence": 0.8},
            success=True,
            error=None,
        )

        # Serialize to dict
        data = tool_call.model_dump()

        assert data["tool_name"] == "extract_core_pain"
        assert data["success"] is True
        assert data["result"]["confidence"] == 0.8

        # Deserialize from dict
        restored = ToolCall(**data)
        assert restored.tool_name == "extract_core_pain"
        assert restored.result["confidence"] == 0.8

    def test_consultant_guidance_structure(self):
        """Tests ConsultantGuidance Pydantic model structure."""
        guidance = ConsultantGuidance(
            summary="Need more signal about primary persona",
            questions_to_ask=[
                QuestionToAsk(
                    question="Who on your team feels this pain most acutely?",
                    why_ask="To identify THE primary persona",
                    listen_for=["Role titles", "Pain descriptions", "Current workarounds"],
                )
            ],
            signals_to_watch=["Persona roles", "Pain intensity"],
            what_this_unlocks="Primary persona gate, which unlocks wow moment identification",
        )

        assert len(guidance.questions_to_ask) == 1
        assert guidance.questions_to_ask[0].question.startswith("Who on your team")
        assert "primary persona" in guidance.what_this_unlocks.lower()

    def test_di_agent_response_structure(self):
        """Tests DIAgentResponse Pydantic model structure."""
        response = DIAgentResponse(
            observation="Project has core pain but no persona",
            thinking="Cannot define wow moment without persona",
            decision="Extract primary persona from signals",
            action_type="tool_call",
            tools_called=[
                ToolCall(
                    tool_name="extract_primary_persona",
                    tool_args={},
                    success=True,
                )
            ],
            recommended_next="Execute extraction to identify primary persona",
            readiness_before=25,
            readiness_after=25,
            gates_affected=["primary_persona"],
        )

        assert response.action_type == "tool_call"
        assert len(response.tools_called) == 1
        assert response.gates_affected == ["primary_persona"]
        assert response.readiness_before == 25
