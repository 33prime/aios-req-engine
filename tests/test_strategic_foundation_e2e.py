"""
End-to-end tests for Strategic Foundation entity lifecycle.

Tests the complete flow:
1. Entity creation via smart_upsert
2. Entity enrichment via LLM chains
3. Source attribution and evidence tracking
4. Change history and revisions
5. Impact on readiness gates
6. Analytics computation
"""

import pytest

pytestmark = pytest.mark.integration
from uuid import uuid4, UUID
from unittest.mock import patch, MagicMock, AsyncMock

from app.db import (
    business_drivers,
    competitor_refs,
    stakeholders,
    risks,
)
from app.chains.enrich_kpi import enrich_kpi
from app.chains.enrich_pain_point import enrich_pain_point
from app.chains.enrich_goal import enrich_goal
from app.chains.enrich_competitor import enrich_competitor
from app.chains.enrich_stakeholder import enrich_stakeholder
from app.chains.enrich_risk import enrich_risk
from app.api.strategic_analytics import get_strategic_analytics
from app.core.readiness.gate_impact import get_entity_gate_impact_summary


@pytest.fixture
def project_id():
    """Test project ID."""
    return uuid4()


@pytest.fixture
def signal_id():
    """Test signal ID."""
    return uuid4()


class TestBusinessDriverLifecycle:
    """Test complete lifecycle for business drivers (KPIs, pains, goals)."""

    @pytest.mark.anyio
    async def test_create_and_enrich_kpi(self, project_id, signal_id):
        """Create KPI via smart_upsert, enrich it, and verify impact on gates."""

        # Step 1: Create KPI using smart_upsert
        kpi, action = business_drivers.smart_upsert_business_driver(
            project_id=project_id,
            driver_type="kpi",
            description="Reduce customer support tickets by 40%",
            measurement="From 500/week to 300/week",
            timeframe="Within 6 months",
            priority=5,
            new_evidence=[
                {
                    "signal_id": str(signal_id),
                    "chunk_id": str(uuid4()),
                    "text": "reduce customer support tickets by 40% within 6 months",
                    "confidence": 0.95,
                }
            ],
            source_signal_id=signal_id,
            created_by="test",
        )

        assert action == "created"
        assert kpi["driver_type"] == "kpi"
        assert kpi["description"] == "Reduce customer support tickets by 40%"
        assert kpi["confirmation_status"] == "ai_generated"  # Default for system-created
        assert len(kpi["evidence"]) == 1
        assert signal_id in [UUID(sid) for sid in kpi["source_signal_ids"]]

        kpi_id = UUID(kpi["id"])

        # Step 2: Enrich the KPI
        with patch("app.chains.enrich_kpi.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = """{
                "baseline_value": "500 support tickets per week",
                "current_state": "High volume of repetitive onboarding questions",
                "target_state": "300 tickets per week with better self-service",
                "success_criteria": "40% reduction sustained for 2 consecutive months",
                "stakeholder_importance": "Critical for VP of Customer Success",
                "business_impact": "Reduces support costs by ~$120K annually"
            }"""
            mock_llm.invoke = MagicMock(return_value=mock_response)
            mock_get_llm.return_value = mock_llm

            enriched = await enrich_kpi(
                project_id=project_id,
                kpi_id=kpi_id,
            )

        assert enriched["enrichment_status"] == "enriched"
        assert enriched["baseline_value"] == "500 support tickets per week"
        assert enriched["business_impact"] is not None
        assert "120K" in enriched["business_impact"]

        # Step 3: Verify gate impact
        impact = get_entity_gate_impact_summary(project_id)

        # KPIs with baseline_value and business_impact should boost business_case gate
        business_case_impact = next(
            (g for g in impact["gates"] if g["gate_name"] == "business_case"),
            None,
        )
        assert business_case_impact is not None
        assert business_case_impact["contributing_entities"] > 0

    @pytest.mark.anyio
    async def test_smart_upsert_merges_evidence(self, project_id, signal_id):
        """Test smart upsert merges evidence for confirmed entities."""

        # First creation - mark as confirmed_client
        kpi1, action1 = business_drivers.smart_upsert_business_driver(
            project_id=project_id,
            driver_type="kpi",
            description="Reduce support tickets by 40%",
            measurement="500 to 300 tickets/week",
            priority=5,
            new_evidence=[
                {
                    "signal_id": str(signal_id),
                    "chunk_id": str(uuid4()),
                    "text": "reduce tickets by 40%",
                    "confidence": 0.95,
                }
            ],
            source_signal_id=signal_id,
            created_by="test",
        )
        assert action1 == "created"

        # Update to confirmed status
        business_drivers.update_business_driver(
            driver_id=UUID(kpi1["id"]),
            confirmation_status="confirmed_client",
        )

        # Second upsert - should merge evidence, not replace fields
        signal_id2 = uuid4()
        kpi2, action2 = business_drivers.smart_upsert_business_driver(
            project_id=project_id,
            driver_type="kpi",
            description="Reduce support tickets by 40%",  # Same description
            measurement="Target 300 tickets weekly",  # Different wording
            priority=4,  # Different priority
            new_evidence=[
                {
                    "signal_id": str(signal_id2),
                    "chunk_id": str(uuid4()),
                    "text": "support ticket reduction goal",
                    "confidence": 0.85,
                }
            ],
            source_signal_id=signal_id2,
            created_by="test",
        )

        # Should merge (matched via similarity)
        assert action2 == "merged"
        assert kpi2["id"] == kpi1["id"]
        assert kpi2["confirmation_status"] == "confirmed_client"  # Preserved
        assert len(kpi2["evidence"]) == 2  # Merged evidence
        assert len(kpi2["source_signal_ids"]) == 2  # Merged sources


class TestCompetitorLifecycle:
    """Test complete lifecycle for competitor references."""

    @pytest.mark.anyio
    async def test_create_and_enrich_competitor(self, project_id, signal_id):
        """Create competitor, enrich it, and verify wow_moment gate impact."""

        # Step 1: Create competitor
        comp, action = competitor_refs.smart_upsert_competitor_ref(
            project_id=project_id,
            reference_type="competitor",
            name="Acme Corp",
            category="Customer Support Software",
            strengths=["Better onboarding"],
            weaknesses=["Lacks advanced analytics"],
            new_evidence=[
                {
                    "signal_id": str(signal_id),
                    "chunk_id": str(uuid4()),
                    "text": "Acme Corp - better onboarding but lack analytics",
                    "confidence": 0.9,
                }
            ],
            source_signal_id=signal_id,
            created_by="test",
        )

        assert action == "created"
        assert comp["name"] == "Acme Corp"
        assert "Better onboarding" in comp["strengths"]

        comp_id = UUID(comp["id"])

        # Step 2: Enrich
        with patch("app.chains.enrich_competitor.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = """{
                "market_position": "Market leader with 35% share",
                "pricing_model": "Tiered SaaS: $49-$199/user/month",
                "key_differentiator": "White-glove onboarding with dedicated success manager",
                "target_customers": "Mid-market companies (100-1000 employees)",
                "core_features": ["Visual workflow builder", "24/7 live chat support"]
            }"""
            mock_llm.invoke = MagicMock(return_value=mock_response)
            mock_get_llm.return_value = mock_llm

            enriched = await enrich_competitor(
                project_id=project_id,
                competitor_id=comp_id,
            )

        assert enriched["enrichment_status"] == "enriched"
        assert "Market leader" in enriched["market_position"]
        assert enriched["key_differentiator"] is not None

        # Step 3: Verify gate impact
        impact = get_entity_gate_impact_summary(project_id)

        # Competitors with key_differentiator should boost wow_moment gate
        wow_impact = next(
            (g for g in impact["gates"] if g["gate_name"] == "wow_moment"),
            None,
        )
        assert wow_impact is not None


class TestStakeholderLifecycle:
    """Test complete lifecycle for stakeholders."""

    @pytest.mark.anyio
    async def test_create_and_enrich_stakeholder(self, project_id, signal_id):
        """Create stakeholder, enrich it, and verify persona gate impact."""

        # Step 1: Create stakeholder
        stakeholder, action = stakeholders.smart_upsert_stakeholder(
            project_id=project_id,
            name="Sarah Chen",
            role="VP of Customer Success",
            stakeholder_type="champion",
            influence_level="high",
            is_economic_buyer=True,
            priorities=["Reduce support tickets", "Improve onboarding"],
            new_evidence=[
                {
                    "signal_id": str(signal_id),
                    "chunk_id": str(uuid4()),
                    "text": "Sarah Chen is our VP of Customer Success",
                    "confidence": 0.95,
                }
            ],
            source_signal_id=signal_id,
            created_by="test",
        )

        assert action == "created"
        assert stakeholder["name"] == "Sarah Chen"
        assert stakeholder["is_economic_buyer"] is True

        stakeholder_id = UUID(stakeholder["id"])

        # Step 2: Enrich
        with patch("app.chains.enrich_stakeholder.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = """{
                "engagement_level": "highly_engaged",
                "decision_authority": "Budget authority up to $500K for customer success tools",
                "engagement_strategy": "Weekly sync meetings, involve in feature prioritization",
                "risk_if_disengaged": "Project may lose executive sponsorship and budget",
                "win_conditions": ["Measurable ticket reduction", "Positive team feedback"],
                "key_concerns": ["Implementation timeline", "Team adoption"]
            }"""
            mock_llm.invoke = MagicMock(return_value=mock_response)
            mock_get_llm.return_value = mock_llm

            enriched = await enrich_stakeholder(
                project_id=project_id,
                stakeholder_id=stakeholder_id,
            )

        assert enriched["enrichment_status"] == "enriched"
        assert enriched["engagement_level"] == "highly_engaged"
        assert "500K" in enriched["decision_authority"]
        assert len(enriched["win_conditions"]) > 0

        # Step 3: Verify gate impact
        impact = get_entity_gate_impact_summary(project_id)

        # Economic buyers with decision_authority boost primary_persona gate
        persona_impact = next(
            (g for g in impact["gates"] if g["gate_name"] == "primary_persona"),
            None,
        )
        assert persona_impact is not None


class TestRiskLifecycle:
    """Test complete lifecycle for risks."""

    @pytest.mark.anyio
    async def test_create_and_enrich_risk(self, project_id, signal_id):
        """Create risk, enrich it, and verify it appears in analytics."""

        # Step 1: Create risk
        risk, action = risks.smart_upsert_risk(
            project_id=project_id,
            title="Support team bandwidth constraints",
            risk_type="resource",
            severity="high",
            description="Support team already stretched thin",
            new_evidence=[
                {
                    "signal_id": str(signal_id),
                    "chunk_id": str(uuid4()),
                    "text": "support team is already stretched thin",
                    "confidence": 0.9,
                }
            ],
            source_signal_id=signal_id,
            created_by="test",
        )

        assert action == "created"
        assert risk["severity"] == "high"
        assert "bandwidth" in risk["title"].lower()

        risk_id = UUID(risk["id"])

        # Step 2: Enrich
        with patch("app.chains.enrich_risk.get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.content = """{
                "impact_on_timeline": "Could delay testing phase by 2-3 weeks",
                "impact_on_budget": "May require temp contractor support ($15K)",
                "affected_stakeholders": ["Support team", "Implementation manager"],
                "probability": "high",
                "mitigation_strategy": "Hire 2 temp support agents during implementation",
                "contingency_plan": "Phase rollout to reduce support burden"
            }"""
            mock_llm.invoke = MagicMock(return_value=mock_response)
            mock_get_llm.return_value = mock_llm

            enriched = await enrich_risk(
                project_id=project_id,
                risk_id=risk_id,
            )

        assert enriched["enrichment_status"] == "enriched"
        assert enriched["probability"] == "high"
        assert enriched["mitigation_strategy"] is not None

        # Step 3: Verify analytics includes risks
        analytics = await get_strategic_analytics(project_id=project_id)

        assert analytics.entity_counts.risks == 1


class TestAnalyticsComputation:
    """Test strategic analytics computation across all entity types."""

    @pytest.mark.anyio
    async def test_comprehensive_analytics(self, project_id, signal_id):
        """Test analytics with multiple entity types."""

        # Create a mix of entities with different statuses

        # 2 KPIs (1 enriched, 1 not)
        business_drivers.create_business_driver(
            project_id=project_id,
            driver_type="kpi",
            description="KPI 1",
            confirmation_status="confirmed_client",
            enrichment_status="enriched",
            source_signal_ids=[str(signal_id)],
            evidence=[{"chunk_id": str(uuid4()), "text": "test", "confidence": 0.9}],
        )
        business_drivers.create_business_driver(
            project_id=project_id,
            driver_type="kpi",
            description="KPI 2",
            confirmation_status="ai_generated",
            enrichment_status="none",
            source_signal_ids=[],
            evidence=[],
        )

        # 1 Pain
        business_drivers.create_business_driver(
            project_id=project_id,
            driver_type="pain",
            description="Pain 1",
            confirmation_status="needs_confirmation",
            enrichment_status="none",
            source_signal_ids=[str(signal_id)],
            evidence=[],
        )

        # 1 Goal
        business_drivers.create_business_driver(
            project_id=project_id,
            driver_type="goal",
            description="Goal 1",
            confirmation_status="confirmed_consultant",
            enrichment_status="enriched",
            source_signal_ids=[str(signal_id)],
            evidence=[{"chunk_id": str(uuid4()), "text": "test", "confidence": 0.8}],
        )

        # 1 Competitor
        competitor_refs.create_competitor_ref(
            project_id=project_id,
            name="Competitor 1",
            confirmation_status="confirmed_client",
            enrichment_status="enriched",
            source_signal_ids=[str(signal_id)],
        )

        # 1 Stakeholder
        stakeholders.create_stakeholder(
            project_id=project_id,
            name="Stakeholder 1",
            stakeholder_type="champion",
            influence_level="high",
            confirmation_status="confirmed_client",
            enrichment_status="none",
            source_signal_ids=[str(signal_id)],
        )

        # 1 Risk
        risks.create_risk(
            project_id=project_id,
            title="Risk 1",
            risk_type="technical",
            confirmation_status="ai_generated",
            enrichment_status="none",
            source_signal_ids=[],
        )

        # Compute analytics
        analytics = await get_strategic_analytics(project_id=project_id)

        # Verify entity counts
        assert analytics.entity_counts.business_drivers == 4  # 2 KPIs + 1 pain + 1 goal
        assert analytics.entity_counts.kpis == 2
        assert analytics.entity_counts.pains == 1
        assert analytics.entity_counts.goals == 1
        assert analytics.entity_counts.competitor_refs == 1
        assert analytics.entity_counts.stakeholders == 1
        assert analytics.entity_counts.risks == 1
        assert analytics.entity_counts.total == 7

        # Verify enrichment stats
        # 3 enriched (KPI1, Goal1, Competitor1) out of 7 total = 42.9%
        assert analytics.enrichment_stats.enriched == 3
        assert analytics.enrichment_stats.none == 4
        assert 0.4 < analytics.enrichment_stats.enrichment_rate < 0.5

        # Verify confirmation stats
        # confirmed_client: KPI1, Competitor1, Stakeholder1 = 3
        # confirmed_consultant: Goal1 = 1
        # ai_generated: KPI2, Risk1 = 2
        # needs_confirmation: Pain1 = 1
        assert analytics.confirmation_stats.confirmed_client == 3
        assert analytics.confirmation_stats.confirmed_consultant == 1
        assert analytics.confirmation_stats.ai_generated == 2
        assert analytics.confirmation_stats.needs_confirmation == 1
        assert analytics.confirmation_stats.confirmation_rate == 4/7  # (3+1)/7

        # Verify source coverage
        # Entities with sources: KPI1, Pain1, Goal1, Competitor1, Stakeholder1 = 5 out of 7
        assert analytics.source_coverage.entities_with_sources == 5
        assert analytics.source_coverage.total_entities == 7
        assert analytics.source_coverage.coverage_rate == 5/7

        # Verify recommendations generated
        assert len(analytics.recommendations) > 0


class TestGateImpact:
    """Test entity enrichment impact on readiness gates."""

    @pytest.mark.anyio
    async def test_enriched_entities_boost_gates(self, project_id):
        """Test that enriched entities contribute to gate confidence."""

        # Create enriched KPI with baseline_value (impacts business_case)
        business_drivers.create_business_driver(
            project_id=project_id,
            driver_type="kpi",
            description="KPI with baseline",
            enrichment_status="enriched",
            baseline_value="500 tickets/week",
            business_impact="$120K annual savings",
        )

        # Create enriched competitor with key_differentiator (impacts wow_moment)
        competitor_refs.create_competitor_ref(
            project_id=project_id,
            name="Competitor",
            enrichment_status="enriched",
            key_differentiator="White-glove onboarding",
            market_position="Market leader",
        )

        # Create enriched stakeholder as economic buyer (impacts primary_persona)
        stakeholders.create_stakeholder(
            project_id=project_id,
            name="Decision Maker",
            stakeholder_type="sponsor",
            influence_level="high",
            is_economic_buyer=True,
            enrichment_status="enriched",
            decision_authority="Budget authority $500K",
        )

        # Get gate impact
        impact = get_entity_gate_impact_summary(project_id)

        # Should have impact on multiple gates
        assert len(impact["gates"]) > 0

        # Overall summary
        assert impact["overall"]["total_strategic_entities"] == 3
        assert impact["overall"]["total_confidence_boost"] > 0
