"""
End-to-end tests for research-enhanced red team pipeline.

Tests the complete flow:
1. VP completeness validation
2. Research chunk deduplication and priority boosting
3. 5-gate red team analysis
4. Insight generation with gate categories
5. Confirmation generation with email/meeting recommendations
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from app.core.vp_validation import validate_vp_completeness, VPGap
from app.core.chunk_deduplication import deduplicate_chunks, rerank_for_diversity
from app.chains.red_team_research import build_research_gap_prompt
from app.api.insights import determine_confirmation_channel, format_client_friendly_confirmation


class TestVPCompletenessValidation:
    """Tests for VP completeness validation (Gate 1)"""

    def test_identifies_missing_data_schema(self):
        """Should flag VP steps missing data schema as critical"""
        vp_steps = [
            {
                "step_index": 1,
                "label": "Create route",
                "enrichment": {
                    # Missing data_schema
                    "business_logic": "Validate inputs",
                    "transition_logic": "On save, move to step 2"
                }
            }
        ]

        gaps, summary = validate_vp_completeness(vp_steps)

        critical_gaps = [g for g in gaps if g.severity == "critical"]
        assert len(critical_gaps) == 1
        assert critical_gaps[0].gap_type == "data_schema"
        assert not summary["is_prototype_ready"]

    def test_identifies_missing_business_logic(self):
        """Should flag VP steps missing business logic as critical"""
        vp_steps = [
            {
                "step_index": 1,
                "label": "Create route",
                "enrichment": {
                    "data_schema": {"entities": [{"name": "Route", "fields": [{"name": "name", "type": "string"}]}]},
                    # Missing business_logic
                    "transition_logic": "On save, move to step 2"
                }
            }
        ]

        gaps, summary = validate_vp_completeness(vp_steps)

        critical_gaps = [g for g in gaps if g.severity == "critical"]
        assert len(critical_gaps) == 1
        assert critical_gaps[0].gap_type == "business_logic"

    def test_complete_vp_step_has_no_gaps(self):
        """Should not flag complete VP steps"""
        vp_steps = [
            {
                "step_index": 1,
                "label": "Create route",
                "user_benefit_pain": "Save time planning routes efficiently",
                "enrichment": {
                    "data_schema": {"entities": [{"name": "Route", "fields": [{"name": "name", "type": "string"}]}]},
                    "business_logic": "Validate route name is unique and not empty",
                    "transition_logic": "On successful save, redirect to route details view"
                }
            }
        ]

        gaps, summary = validate_vp_completeness(vp_steps)

        assert len(gaps) == 0
        assert summary["is_prototype_ready"]
        assert summary["completeness_percent"] == 100


class TestChunkDeduplication:
    """Tests for chunk deduplication and priority boosting"""

    def test_removes_duplicate_chunks(self):
        """Should remove semantically similar chunks"""
        chunks = [
            {
                "id": "1",
                "content": "Users need real-time updates",
                "embedding": [0.1, 0.2, 0.3],
                "similarity": 0.9
            },
            {
                "id": "2",
                "content": "Real-time updates are essential for users",
                "embedding": [0.11, 0.21, 0.31],  # Very similar
                "similarity": 0.85
            },
            {
                "id": "3",
                "content": "Payment processing must be PCI compliant",
                "embedding": [0.9, 0.8, 0.7],  # Different
                "similarity": 0.8
            }
        ]

        deduplicated = deduplicate_chunks(chunks, similarity_threshold=0.85)

        # Should keep only 2 chunks (removes the duplicate)
        assert len(deduplicated) <= 2
        # Should keep highest similarity chunks
        assert any(c["id"] in ["1", "2"] for c in deduplicated)
        assert any(c["id"] == "3" for c in deduplicated)

    def test_respects_section_limits(self):
        """Should limit chunks per section type"""
        chunks = [
            {
                "id": f"feature_{i}",
                "content": f"Feature {i}",
                "embedding": [0.1 * i, 0.2 * i, 0.3 * i],
                "similarity": 0.9 - (i * 0.01),
                "metadata": {"section_type": "features_must_have"}
            }
            for i in range(10)
        ]

        deduplicated = deduplicate_chunks(chunks, max_per_section=3)

        # Should keep max 3 per section
        feature_chunks = [c for c in deduplicated if c.get("metadata", {}).get("section_type") == "features_must_have"]
        assert len(feature_chunks) <= 3

    def test_mmr_reranking_balances_relevance_and_diversity(self):
        """Should rerank for diversity using MMR algorithm"""
        chunks = [
            {
                "id": "1",
                "content": "Authentication feature",
                "embedding": [0.1, 0.2, 0.3],
                "similarity": 0.95
            },
            {
                "id": "2",
                "content": "Login feature",  # Similar to 1
                "embedding": [0.11, 0.21, 0.31],
                "similarity": 0.9
            },
            {
                "id": "3",
                "content": "Payment processing",  # Different
                "embedding": [0.9, 0.8, 0.7],
                "similarity": 0.7
            }
        ]

        reranked = rerank_for_diversity(chunks, alpha=0.7)

        # Should prefer diversity - chunk 3 should rank higher than chunk 2
        # even though chunk 2 has higher similarity
        assert len(reranked) == 3


class TestRedTeamPromptBuilding:
    """Tests for VP-centric red team prompt construction"""

    def test_includes_vp_completeness_gaps(self):
        """Should include VP gaps in prompt"""
        research_chunks = []
        current_features = []
        current_prd_sections = []
        current_vp_steps = [
            {
                "step_index": 1,
                "label": "Create route",
                "description": "Allow users to create a new route",
                "user_benefit_pain": "Save time planning",
                "enrichment": {}  # Empty - should trigger gaps
            }
        ]
        context_chunks = []

        prompt = build_research_gap_prompt(
            research_chunks,
            current_features,
            current_prd_sections,
            current_vp_steps,
            context_chunks
        )

        assert "VP COMPLETENESS GAPS" in prompt
        assert "CRITICAL" in prompt
        assert "data_schema" in prompt.lower()

    def test_includes_5_gate_instructions(self):
        """Should include all 5 gates in prompt"""
        prompt = build_research_gap_prompt([], [], [], [], [])

        assert "GATE 1: VP COMPLETENESS" in prompt
        assert "GATE 2: MARKET VALIDATION" in prompt
        assert "GATE 3: ASSUMPTION TESTING" in prompt
        assert "GATE 4: SCOPE PROTECTION" in prompt
        assert "GATE 5: WOW FACTOR" in prompt

    def test_emphasizes_vp_as_product(self):
        """Should emphasize VP is THE product"""
        prompt = build_research_gap_prompt([], [], [], [], [])

        assert "VP is THE product" in prompt
        assert "VALUE PATH (CORE PRODUCT)" in prompt


class TestConfirmationChannelRecommendation:
    """Tests for email vs meeting recommendation logic"""

    def test_critical_severity_recommends_meeting(self):
        """Critical insights should recommend meeting"""
        insight = {
            "severity": "critical",
            "gate": "completeness",
            "category": "logic",
            "targets": [{"kind": "vp_step", "label": "Step 1"}]
        }

        result = determine_confirmation_channel(insight)

        assert result["recommended_channel"] == "meeting"
        assert result["complexity_score"] >= 6

    def test_single_minor_insight_recommends_email(self):
        """Minor insight with single target should recommend email"""
        insight = {
            "severity": "minor",
            "gate": "wow",
            "category": "ux",
            "targets": [{"kind": "feature", "label": "Feature 1"}]
        }

        result = determine_confirmation_channel(insight)

        assert result["recommended_channel"] == "email"
        assert result["complexity_score"] < 4

    def test_multiple_targets_increases_complexity(self):
        """Multiple affected targets should increase complexity"""
        insight = {
            "severity": "important",
            "gate": "validation",
            "category": "data",
            "targets": [
                {"kind": "vp_step", "label": "Step 1"},
                {"kind": "vp_step", "label": "Step 2"},
                {"kind": "feature", "label": "Feature 1"},
                {"kind": "prd_section", "label": "Section 1"}
            ]
        }

        result = determine_confirmation_channel(insight)

        # 4+ targets should push to meeting
        assert result["complexity_score"] >= 4

    def test_assumption_gate_recommends_meeting(self):
        """Assumption gate insights should recommend meeting"""
        insight = {
            "severity": "important",
            "gate": "assumption",
            "category": "logic",
            "targets": [{"kind": "vp_step", "label": "Step 1"}]
        }

        result = determine_confirmation_channel(insight)

        # assumption gate adds +2 to complexity
        assert result["recommended_channel"] == "meeting"


class TestClientFriendlyFormatting:
    """Tests for client-friendly confirmation formatting"""

    def test_formats_critical_as_important_decision(self):
        """Critical insights should be framed as important decisions"""
        insight = {
            "title": "Missing data schema for user flow",
            "finding": "The user authentication flow lacks defined data structures",
            "why": "We can't build without knowing what data to collect",
            "severity": "critical",
            "gate": "completeness"
        }

        prompt, detail = format_client_friendly_confirmation(insight)

        assert "Important Decision" in prompt
        assert "Missing data schema for user flow" in prompt

    def test_formats_minor_as_quick_question(self):
        """Minor insights should be framed as quick questions"""
        insight = {
            "title": "Button color preference",
            "finding": "Primary button color not specified",
            "why": "Visual consistency matters",
            "severity": "minor",
            "gate": "wow"
        }

        prompt, detail = format_client_friendly_confirmation(insight)

        assert "Quick Question" in prompt

    def test_adds_gate_context(self):
        """Should add contextual explanation based on gate"""
        insight = {
            "title": "Assumption about offline mode",
            "finding": "App assumes always-online connectivity",
            "why": "Users may need offline access",
            "severity": "important",
            "gate": "assumption"
        }

        prompt, detail = format_client_friendly_confirmation(insight)

        assert "confirm an assumption" in detail.lower()

    def test_includes_business_value(self):
        """Should include why it matters section"""
        insight = {
            "title": "Missing payment integration",
            "finding": "No payment processing specified",
            "why": "Revenue collection is critical for business model",
            "severity": "important",
            "gate": "validation"
        }

        prompt, detail = format_client_friendly_confirmation(insight)

        assert "Why this matters:" in detail
        assert "Revenue collection is critical" in detail


class TestIntegration:
    """Integration tests for complete pipeline"""

    @patch("app.chains.red_team_research._get_client")
    def test_end_to_end_research_to_confirmation(self, mock_get_client):
        """Test complete flow from research to confirmation generation"""
        # Setup: VP with gaps
        vp_steps = [
            {
                "step_index": 1,
                "label": "User signup",
                "description": "User creates account",
                "user_benefit_pain": "Quick onboarding",
                "enrichment": {
                    # Missing data_schema - critical gap
                    "business_logic": "Validate email format",
                    "transition_logic": "Redirect to dashboard"
                }
            }
        ]

        # Validate completeness
        gaps, summary = validate_vp_completeness(vp_steps)
        assert not summary["is_prototype_ready"]

        # Mock LLM to generate insight with gate
        mock_client = MagicMock()
        mock_response = Mock()
        mock_response.choices = [Mock(
            finish_reason="stop",
            message=Mock(content="""{
                "insights": [{
                    "severity": "critical",
                    "gate": "completeness",
                    "category": "data",
                    "title": "Missing user data schema for signup",
                    "finding": "User signup step lacks data schema definition",
                    "why": "Cannot build without knowing what user data to collect",
                    "suggested_action": "needs_confirmation",
                    "targets": [{"kind": "vp_step", "id": null, "label": "User signup"}],
                    "evidence": [{"chunk_id": "12345678-1234-5678-9012-123456789012", "excerpt": "User signup", "rationale": "VP step"}]
                }]
            }""")
        )]
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        # Run red team analysis
        from app.chains.red_team_research import run_research_gap_analysis
        output = run_research_gap_analysis(
            research_chunks=[],
            current_features=[],
            current_prd_sections=[],
            current_vp_steps=vp_steps,
            context_chunks=[],
            run_id="test-run"
        )

        # Verify insight generated
        assert len(output.insights) == 1
        insight = output.insights[0]
        assert insight.gate == "completeness"
        assert insight.severity == "critical"

        # Generate confirmation
        insight_dict = insight.model_dump()
        channel_info = determine_confirmation_channel(insight_dict)
        prompt, detail = format_client_friendly_confirmation(insight_dict)

        # Verify email/meeting recommendation
        assert channel_info["recommended_channel"] == "meeting"  # Critical + completeness gate
        assert "Important Decision" in prompt
        assert "confirm an assumption" in detail.lower() or "details needed" in detail.lower()
