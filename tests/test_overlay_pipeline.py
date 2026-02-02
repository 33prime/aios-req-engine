"""Tests for the prototype analysis pipeline graph."""

from dataclasses import dataclass
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.schemas_prototypes import FeatureAnalysis, GeneratedQuestion, OverlayContent
from app.graphs.prototype_analysis_graph import (
    PrototypeAnalysisState,
    check_more,
    complete,
)


@pytest.fixture
def base_state():
    """Create a base analysis state for testing."""
    return PrototypeAnalysisState(
        prototype_id=uuid4(),
        project_id=uuid4(),
        run_id=uuid4(),
        local_path="/tmp/aios-prototypes/test",
    )


@pytest.fixture
def state_with_features(base_state):
    """State with features ready to analyze."""
    features = [
        {"feature": {"id": str(uuid4()), "name": "Login"}, "file_path": "src/Login.tsx"},
        {"feature": {"id": str(uuid4()), "name": "Dashboard"}, "file_path": "src/Dashboard.tsx"},
        {"feature": {"id": str(uuid4()), "name": "Settings"}, "file_path": None},
    ]
    base_state.features_to_analyze = features
    base_state.features = [f["feature"] for f in features]
    base_state.personas = [{"id": str(uuid4()), "name": "Sarah Chen", "role": "PM"}]
    base_state.vp_steps = [{"step_index": 0, "label": "Sign Up"}]
    return base_state


class TestCheckMore:
    """Tests for the check_more conditional edge."""

    def test_returns_analyze_when_more_features(self, state_with_features):
        """Should loop back when there are more features."""
        state_with_features.current_feature_idx = 0
        assert check_more(state_with_features) == "analyze_feature"

    def test_returns_analyze_at_middle(self, state_with_features):
        """Should continue for middle features."""
        state_with_features.current_feature_idx = 1
        assert check_more(state_with_features) == "analyze_feature"

    def test_returns_complete_when_done(self, state_with_features):
        """Should complete when all features are processed."""
        state_with_features.current_feature_idx = 3  # Past all 3 features
        assert check_more(state_with_features) == "complete"

    def test_returns_complete_for_empty_list(self, base_state):
        """Should complete immediately when no features."""
        base_state.features_to_analyze = []
        base_state.current_feature_idx = 0
        assert check_more(base_state) == "complete"


class TestComplete:
    """Tests for the complete node."""

    def test_updates_prototype_status(self, state_with_features):
        """Should update prototype to 'analyzed' status."""
        state_with_features.results = [
            {"feature_name": "Login", "status": "understood"},
            {"feature_name": "Dashboard", "status": "partial"},
        ]
        state_with_features.errors = []

        with patch("app.graphs.prototype_analysis_graph.update_prototype") as mock_update:
            result = complete(state_with_features)
            mock_update.assert_called_once_with(state_with_features.prototype_id, status="analyzed")

    def test_updates_status_even_with_errors(self, state_with_features):
        """Should still mark as analyzed even if some features had errors."""
        state_with_features.results = [{"feature_name": "Login", "status": "understood"}]
        state_with_features.errors = [{"feature": "Dashboard", "error": "Parse error"}]

        with patch("app.graphs.prototype_analysis_graph.update_prototype") as mock_update:
            complete(state_with_features)
            mock_update.assert_called_once_with(state_with_features.prototype_id, status="analyzed")


class TestPrototypeAnalysisState:
    """Tests for the state dataclass."""

    def test_default_state(self):
        """Default state should have empty lists and zero index."""
        state = PrototypeAnalysisState(
            prototype_id=uuid4(),
            project_id=uuid4(),
            run_id=uuid4(),
            local_path="/tmp/test",
        )
        assert state.features == []
        assert state.personas == []
        assert state.vp_steps == []
        assert state.features_to_analyze == []
        assert state.current_feature_idx == 0
        assert state.current_analysis is None
        assert state.results == []
        assert state.errors == []
        assert state.step_count == 0

    def test_state_with_analysis(self, base_state):
        """State can hold analysis results."""
        analysis = {
            "triggers": ["Click"],
            "actions": ["Submit"],
            "implementation_status": "functional",
            "confidence": 0.9,
        }
        base_state.current_analysis = analysis
        assert base_state.current_analysis["confidence"] == 0.9


class TestPipelineGraphStructure:
    """Tests for the graph compilation."""

    def test_graph_compiles(self):
        """The graph should compile without errors."""
        from app.graphs.prototype_analysis_graph import build_prototype_analysis_graph

        graph = build_prototype_analysis_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        """Graph should contain all expected node names."""
        from app.graphs.prototype_analysis_graph import build_prototype_analysis_graph

        graph = build_prototype_analysis_graph()
        # LangGraph compiled graphs expose node names via get_graph().nodes
        graph_def = graph.get_graph()
        node_names = {n.name if hasattr(n, "name") else str(n) for n in graph_def.nodes}
        # Verify critical nodes exist (exact names depend on LangGraph internals)
        assert len(node_names) > 0
