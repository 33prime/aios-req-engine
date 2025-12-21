"""Phase 2B behavioral tests: contradictions, idempotency, overrides, research conflicts."""

import pytest
from unittest.mock import patch
from uuid import uuid4

from tests.fakes.fake_db import fake_db
from tests.fixtures_phase2b import (
    EXTRACTED_FACTS_ID_2,
    JOB_ID_1,
    PROJECT_ID,
    RUN_ID_1,
    SIGNAL_ID_2,
)


@pytest.fixture(autouse=True)
def reset_fake_db():
    """Reset fake DB before each test."""
    fake_db.reset()


@pytest.fixture
def mock_db_helpers():
    """Mock all DB helpers to use fake DB."""
    from unittest.mock import MagicMock

    mock_output = MagicMock()
    mock_output.summary = 'Mock reconciliation - no changes needed'
    mock_output.prd_section_patches = []
    mock_output.vp_step_patches = []
    mock_output.feature_ops = []
    mock_output.confirmation_items = []
    mock_output.model_dump.return_value = {
        'summary': 'Mock reconciliation - no changes needed',
        'prd_section_patches': [],
        'vp_step_patches': [],
        'feature_ops': [],
        'confirmation_items': []
    }

    patches = [
        patch("app.db.signals.get_signal", side_effect=lambda signal_id: fake_db.get_signal(signal_id)),
        patch("app.db.signals.list_signal_chunks", side_effect=lambda signal_id: fake_db.list_signal_chunks(signal_id)),
        patch("app.db.facts.list_latest_extracted_facts", side_effect=fake_db.list_latest_extracted_facts),
        patch("app.db.insights.list_latest_insights", side_effect=lambda project_id, limit=50, statuses=None: []),
        patch("app.db.prd.list_prd_sections", side_effect=fake_db.list_prd_sections),
        patch("app.db.prd.upsert_prd_section", side_effect=fake_db.upsert_prd_section),
        patch("app.db.vp.list_vp_steps", side_effect=fake_db.list_vp_steps),
        patch("app.db.vp.upsert_vp_step", side_effect=fake_db.upsert_vp_step),
        patch("app.db.features.list_features", side_effect=fake_db.list_features),
        patch("app.db.features.bulk_replace_features", side_effect=fake_db.bulk_replace_features),
        patch("app.db.confirmations.upsert_confirmation_item", side_effect=fake_db.upsert_confirmation_item),
        patch("app.db.confirmations.list_confirmation_items", side_effect=fake_db.list_confirmation_items),
        patch("app.db.confirmations.get_confirmation_item", side_effect=fake_db.get_confirmation_item),
        patch("app.db.confirmations.set_confirmation_status", side_effect=fake_db.set_confirmation_status),
        patch("app.db.project_state.get_project_state", side_effect=fake_db.get_project_state),
        patch("app.db.project_state.update_project_state", side_effect=fake_db.update_project_state),
        patch("app.db.revisions.insert_state_revision", side_effect=fake_db.insert_state_revision),
        patch("app.db.revisions.list_state_revisions", side_effect=fake_db.list_state_revisions),
        patch("app.core.embeddings.embed_texts", side_effect=lambda texts: [[0.1] * 1536 for _ in texts]),
        patch("app.db.phase0.search_signal_chunks", side_effect=lambda query_embedding, match_count, project_id=None: fake_db.signal_chunks.get(str(list(fake_db.signal_chunks.keys())[0]) if fake_db.signal_chunks else [], [])),
    ]

    # Start all patches
    for p in patches:
        p.start()

    yield

    # Stop all patches
    for p in patches:
        p.stop()


class TestPhase2BBehavioral:
    """Phase 2B behavioral tests."""

    def test_contradiction_must_create_confirmations(self, mock_db_helpers):
        """Test 1: Contradiction MUST create confirmations."""
        from app.core.schemas_reconcile import (
            ConfirmationItemSpec,
            EvidenceRef,
            FeatureOp,
            ReconcileOutput,
        )
        from app.core.schemas_facts import ExtractFactsOutput, FactItem
        from app.graphs.reconcile_state_graph import run_reconcile_agent
        from app.chains.extract_facts import extract_facts_from_chunks

        # Step 1: Setup contradiction signal
        signal = {
            "id": str(SIGNAL_ID_2),
            "project_id": str(PROJECT_ID),
            "signal_type": "email",
            "source": "client@example.com",
            "raw_text": "UPDATE: The in-app Document Viewer is REQUIRED for MVP success. Users need to preview PDFs side-by-side with the builder. This is a critical decision point that requires immediate alignment.",
            "metadata": {"authority": "client", "from": "patel", "subject": "Critical MVP Update"},
        }
        fake_db.insert_signal(signal)

        chunks = [
            {
                "chunk_id": str(uuid4()),
                "signal_id": str(SIGNAL_ID_2),
                "chunk_index": 0,
                "content": "UPDATE: The in-app Document Viewer is REQUIRED for MVP success. Users need to preview PDFs side-by-side with the builder. This is a critical decision point that requires immediate alignment.",
                "start_char": 0,
                "end_char": 200,
                "metadata": {"authority": "client"},
                "signal_metadata": signal["metadata"],
            }
        ]
        fake_db.signal_chunks[str(SIGNAL_ID_2)] = chunks

        # Step 2: Mock extract_facts to return contradicting fact
        mock_extract_output = ExtractFactsOutput(
            summary="Client requires document viewer in MVP - contradicts current state",
            facts=[
                FactItem(
                    fact_type="feature",
                    title="Document Viewer Required in MVP",
                    detail="Client explicitly states Document Viewer is REQUIRED for MVP success",
                    confidence="high",
                    evidence=[
                        {
                            "chunk_id": chunks[0]["chunk_id"],
                            "excerpt": "Document Viewer is REQUIRED for MVP success",
                            "rationale": "Client explicitly requires this feature"
                        }
                    ]
                )
            ],
            open_questions=[],
            contradictions=[]
        )

        with patch("app.chains.extract_facts.extract_facts_from_chunks", return_value=mock_extract_output):
            from app.chains.extract_facts import extract_facts_from_chunks
            # Extract facts
            facts_result = extract_facts_from_chunks(
                signal=signal,
                chunks=chunks,
                settings=type('Settings', (), {
                    'FACTS_MODEL': 'gpt-4o-mini',
                    'OPENAI_API_KEY': 'dummy'
                })()
            )

            # Insert extracted facts
            fake_db.insert_extracted_facts({
                "id": str(EXTRACTED_FACTS_ID_2),
                "project_id": str(PROJECT_ID),
                "signal_id": str(SIGNAL_ID_2),
                "run_id": str(uuid4()),
                "job_id": str(uuid4()),
                "model": "gpt-4o-mini",
                "prompt_version": "facts_v1",
                "schema_version": "facts_v1",
                "facts": facts_result.model_dump(),
                "summary": facts_result.summary,
                "created_at": "2025-12-21T20:35:00.000000+00:00"
            })

        # Step 3: Mock reconcile to create contradiction confirmation
        mock_reconcile_output = ReconcileOutput(
            summary="Contradiction detected: Document Viewer required but currently excluded from MVP",
            prd_section_patches=[],
            vp_step_patches=[],
            feature_ops=[
                FeatureOp(
                    op="upsert",
                    name="In-app Document Viewer",
                    category="UI Features",
                    is_mvp=True,  # Changed from False to True
                    confidence="high",
                    set_status="needs_confirmation",  # Not auto-confirmed
                    evidence=[
                        {
                            "chunk_id": chunks[0]["chunk_id"],
                            "excerpt": "Document Viewer is REQUIRED for MVP success",
                            "rationale": "Client explicitly requires this feature"
                        }
                    ],
                    reason="Client requirement contradicts current MVP scope"
                )
            ],
            confirmation_items=[
                ConfirmationItemSpec(
                    key="feature:doc_viewer:mvp_scope",
                    kind="feature",
                    title="Document Viewer MVP Scope Contradiction",
                    why="Current canonical excludes Document Viewer from MVP, but client signal requires it",
                    ask="Should the in-app Document Viewer be included in MVP despite current scope decisions?",
                    priority="high",
                    suggested_method="meeting",  # Should trigger meeting due to "decision point" + "alignment"
                    evidence=[
                        {
                            "chunk_id": chunks[0]["chunk_id"],
                            "excerpt": "This is a critical decision point that requires immediate alignment",
                            "rationale": "Client signals this needs discussion and alignment"
                        }
                    ],
                    target_table="features",
                    target_id="b2c3d4e5-f6a7-4321-8765-123456789abd"  # Doc viewer feature ID
                )
            ]
        )

        # Override the general mock with specific contradiction output
        with patch("app.chains.reconcile_state.reconcile_state", return_value=mock_reconcile_output) as mock_reconcile:
            # Run reconcile
            changed_counts, confirmations_open_count, summary = run_reconcile_agent(
                project_id=PROJECT_ID,
                run_id=RUN_ID_1,
                job_id=JOB_ID_1,
                include_research=False,
                top_k_context=24
            )

        # Step 4: Assert outcomes
        assert changed_counts["features_updated"] == 1
        assert confirmations_open_count == 1
        assert "Contradiction detected" in summary

        # Check confirmation was created
        confirmations = fake_db.list_confirmation_items(PROJECT_ID, status="open")
        assert len(confirmations) == 1
        conf = confirmations[0]
        assert conf["key"] == "feature:doc_viewer:mvp_scope"
        assert conf["kind"] == "feature"
        assert conf["priority"] == "high"
        assert conf["suggested_method"] == "meeting"
        assert "contradicts current MVP scope" in conf["why"]

        # Check feature was updated but not auto-confirmed
        features = fake_db.list_features(PROJECT_ID)
        doc_viewer = next(f for f in features if f["name"] == "In-app Document Viewer")
        assert doc_viewer["is_mvp"] is True  # Updated due to contradiction
        assert doc_viewer["status"] == "draft"  # NOT auto-confirmed

        # Check outreach recommends meeting
        from app.api.outreach import _decide_outreach_method
        method, reason = _decide_outreach_method(confirmations)
        assert method == "meeting"
        assert "decision point" in reason or "alignment" in reason

    def test_same_input_twice_idempotency(self, mock_db_helpers):
        """Test 2: Same input twice (idempotency)."""
        from app.core.schemas_reconcile import ReconcileOutput
        from app.graphs.reconcile_state_graph import run_reconcile_agent

        # First run - should process changes
        mock_output = ReconcileOutput(
            summary="First reconciliation run",
            prd_section_patches=[],
            vp_step_patches=[],
            feature_ops=[],
            confirmation_items=[]
        )

        with patch("app.chains.reconcile_state.reconcile_state", return_value=mock_output):
            run_reconcile_agent(PROJECT_ID, RUN_ID_1, JOB_ID_1)

        # Check state after first run
        initial_revisions_count = len(fake_db.revisions)
        initial_state = fake_db.get_project_state(PROJECT_ID)

        # Second run - should do nothing (no new inputs)
        changed_counts, confirmations_open_count, summary = run_reconcile_agent(
            PROJECT_ID, uuid4(), uuid4()
        )

        # Assert idempotency
        assert changed_counts == {}  # No changes
        assert confirmations_open_count == 0
        assert "No new inputs to reconcile" in summary

        # Revisions count should be unchanged (no new revision for no-op)
        assert len(fake_db.revisions) == initial_revisions_count

        # Project state should be unchanged
        final_state = fake_db.get_project_state(PROJECT_ID)
        assert final_state["last_reconciled_at"] == initial_state["last_reconciled_at"]

    def test_consultant_override_protection(self, mock_db_helpers):
        """Test 3: Consultant override protection."""
        from app.core.schemas_reconcile import ConfirmationItemSpec, EvidenceRef, ReconcileOutput
        from app.graphs.reconcile_state_graph import run_reconcile_agent

        # Step 1: Set up confirmed_consultant state
        prd_sections = fake_db.list_prd_sections(PROJECT_ID)
        happy_path = next(s for s in prd_sections if s["slug"] == "happy_path")
        happy_path["status"] = "confirmed_consultant"
        happy_path["fields"]["content"] = "CONSULTANT APPROVED: The ideal user journey..."

        # Step 2: Mock weak conflicting signal
        mock_output = ReconcileOutput(
            summary="Weak signal conflicts with confirmed consultant decision",
            prd_section_patches=[
                {
                    "slug": "happy_path",
                    "set_fields": {"content": "CONFLICTING: Maybe skip surveys in happy path"},
                    "set_status": "needs_confirmation",
                    "add_client_needs": [],
                    "evidence": []
                }
            ],
            vp_step_patches=[],
            feature_ops=[],
            confirmation_items=[
                ConfirmationItemSpec(
                    key="prd:happy_path:consultant_conflict",
                    kind="prd",
                    title="Happy Path Consultant Override Attempt",
                    why="Weak signal conflicts with consultant-confirmed happy path",
                    ask="Should we override the consultant-approved happy path?",
                    priority="medium",
                    suggested_method="email",
                    evidence=[],
                    target_table="prd_sections",
                    target_id=happy_path["id"]
                )
            ]
        )

        with patch("app.chains.reconcile_state.reconcile_state", return_value=mock_output):
            # Run reconcile
            changed_counts, confirmations_open_count, summary = run_reconcile_agent(
                PROJECT_ID, RUN_ID_1, JOB_ID_1
            )

        # Step 3: Assert protection
        assert confirmations_open_count == 1

        # Check happy path was NOT overwritten
        updated_sections = fake_db.list_prd_sections(PROJECT_ID)
        updated_happy_path = next(s for s in updated_sections if s["slug"] == "happy_path")
        assert updated_happy_path["status"] == "confirmed_consultant"  # Unchanged
        assert "CONSULTANT APPROVED" in updated_happy_path["fields"]["content"]  # Unchanged

        # Check confirmation was created
        confirmations = fake_db.list_confirmation_items(PROJECT_ID, status="open")
        assert len(confirmations) == 1
        assert "consultant_conflict" in confirmations[0]["key"]

    def test_research_vs_client_truth(self, mock_db_helpers):
        """Test 4: Research conflict vs client truth (authority model)."""
        from app.core.schemas_reconcile import ConfirmationItemSpec, EvidenceRef, ReconcileOutput
        from app.graphs.reconcile_state_graph import run_reconcile_agent

        # Step 1: Add research insight (simulated)
        # Research suggests including doc viewer
        research_conf = {
            "id": str(uuid4()),
            "project_id": str(PROJECT_ID),
            "kind": "feature",
            "target_table": "features",
            "target_id": "b2c3d4e5-f6a7-4321-8765-123456789abd",
            "key": "research:doc_viewer:premium_perception",
            "title": "Research: Document Viewer for Premium Perception",
            "why": "Industry research shows document viewers are essential for premium SaaS perception",
            "ask": "Consider including document viewer for premium positioning?",
            "status": "open",
            "suggested_method": "email",
            "priority": "low",
            "evidence": [],
            "created_from": {"source": "industry_research"}
        }
        fake_db.confirmations.append(research_conf)

        # Step 2: Client explicitly rejects (authority="client")
        client_signal = {
            "id": str(uuid4()),
            "project_id": str(PROJECT_ID),
            "signal_type": "email",
            "source": "client@example.com",
            "raw_text": "Client decision: NO document viewer in MVP. Handle externally.",
            "metadata": {"authority": "client", "from": "patel"}
        }

        mock_output = ReconcileOutput(
            summary="Client explicitly rejects document viewer - overrides research recommendation",
            prd_section_patches=[],
            vp_step_patches=[],
            feature_ops=[
                {
                    "op": "upsert",
                    "name": "In-app Document Viewer",
                    "category": "UI Features",
                    "is_mvp": False,  # Client says NO
                    "confidence": "high",
                    "set_status": "confirmed_client",  # Can be confirmed since it's client decision
                    "evidence": [],
                    "reason": "Client explicitly rejects for MVP"
                }
            ],
            confirmation_items=[]
        )

        with patch("app.chains.reconcile_state.reconcile_state", return_value=mock_output):
            # Run reconcile
            changed_counts, confirmations_open_count, summary = run_reconcile_agent(
                PROJECT_ID, RUN_ID_1, JOB_ID_1
            )

        # Step 3: Assert client truth wins
        assert changed_counts["features_updated"] == 1

        # Check feature reflects client decision
        features = fake_db.list_features(PROJECT_ID)
        doc_viewer = next(f for f in features if f["name"] == "In-app Document Viewer")
        assert doc_viewer["is_mvp"] is False  # Client decision
        assert doc_viewer["status"] == "confirmed_client"  # Can be confirmed for client decisions

        # Research confirmation should still exist but may be resolved
        all_confirmations = fake_db.list_confirmation_items(PROJECT_ID)
        research_confs = [c for c in all_confirmations if "research" in c["key"]]
        assert len(research_confs) >= 1  # Research insight persists but doesn't override

        assert "Client explicitly rejects" in summary
