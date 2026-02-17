"""Tests for Smart Project Launch — endpoint, orchestrator, and progress.

Zero-cost: all LLM/enrichment calls are mocked. The real orchestrator logic
(dependency resolution, skip conditions, failure cascading) runs synchronously
via a threading.Thread mock.
"""

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock, call, patch
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

# ---------------------------------------------------------------------------
# Shared IDs
# ---------------------------------------------------------------------------
PROJECT_ID = str(uuid4())
LAUNCH_ID = str(uuid4())
CLIENT_ID = str(uuid4())
STAKEHOLDER_ID_1 = str(uuid4())
STAKEHOLDER_ID_2 = str(uuid4())
SIGNAL_ID = str(uuid4())


def _make_step_dicts(launch_id: str = LAUNCH_ID, status: str = "pending"):
    """Build a list of step dicts matching STEP_DEFINITIONS."""
    definitions = [
        ("onboarding", "Extracting requirements", []),
        ("client_enrichment", "Enriching client profile", []),
        ("stakeholder_enrichment", "Building stakeholder profiles", []),
        ("foundation", "Running foundation analysis", ["onboarding"]),
        ("readiness_check", "Checking discovery readiness", ["foundation", "client_enrichment"]),
        ("discovery", "Running discovery research", ["readiness_check"]),
    ]
    return [
        {
            "id": str(uuid4()),
            "launch_id": launch_id,
            "step_key": key,
            "step_label": label,
            "depends_on": deps,
            "status": status,
            "started_at": None,
            "completed_at": None,
            "result_summary": None,
            "error_message": None,
        }
        for key, label, deps in definitions
    ]


def _safe_asyncio_run(coro):
    """asyncio.run replacement that works inside a running event loop (TestClient).

    TestClient runs async endpoints in an event loop thread. Python 3.11 prevents
    running ANY event loop when another is running in the same thread. For our
    mocked async functions (AsyncMock), the coroutines complete immediately —
    we can extract the return value without an event loop.
    """
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    # If the coroutine didn't finish, close it and raise
    coro.close()
    raise RuntimeError("Coroutine did not complete immediately")


class _SynchronousThread:
    """Drop-in for threading.Thread that runs target synchronously."""

    def __init__(self, *, target=None, args=(), daemon=False, **kwargs):
        self._target = target
        self._args = args

    def start(self):
        if self._target:
            self._target(*self._args)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_launch_deps():
    """Mock every external dependency so the launch endpoint + pipeline run
    synchronously with zero network / LLM calls."""

    steps = _make_step_dicts()
    patchers = []

    def _p(target, **kwargs):
        p = patch(target, **kwargs)
        patchers.append(p)
        return p.start()

    # -- Sync-phase: project / client / stakeholder / signal -------------------
    # These are lazy imports inside function bodies → patch at source module
    m_create_project = _p("app.db.projects.create_project", return_value={"id": PROJECT_ID, "name": "Test"})
    m_create_client = _p("app.db.clients.create_client", return_value={"id": CLIENT_ID, "name": "Acme"})
    m_get_client = _p("app.db.clients.get_client", return_value={"id": CLIENT_ID, "name": "Acme", "website": "https://acme.com"})
    m_link = _p("app.db.clients.link_project_to_client", return_value={"id": str(uuid4())})
    m_create_stakeholder = _p("app.db.stakeholders.create_stakeholder", return_value={"id": STAKEHOLDER_ID_1, "name": "Jane Doe"})
    m_update_stakeholder = _p("app.db.stakeholders.update_stakeholder", return_value={"id": STAKEHOLDER_ID_1})
    m_insert_signal = _p("app.db.phase0.insert_signal", return_value={"id": SIGNAL_ID})
    m_chunk = _p("app.core.chunking.chunk_text", return_value=[{"content": "chunk", "chunk_index": 0, "start_char": 0, "end_char": 5}])
    m_embed = _p("app.core.embeddings.embed_texts", return_value=[[0.1] * 8])
    m_insert_chunks = _p("app.db.phase0.insert_signal_chunks", return_value=[{"id": str(uuid4())}])

    # -- Launch tracking -------------------------------------------------------
    m_create_launch = _p("app.api.project_launch.create_launch", return_value={"id": LAUNCH_ID, "project_id": PROJECT_ID, "status": "pending"})
    m_create_launch_step = _p("app.api.project_launch.create_launch_step", return_value={"id": str(uuid4())})
    m_get_launch_steps = _p("app.api.project_launch.get_launch_steps", return_value=steps)
    m_update_launch_status = _p("app.api.project_launch.update_launch_status")
    m_update_step_status = _p("app.api.project_launch.update_step_status")
    m_get_launch = _p("app.api.project_launch.get_launch", return_value={"id": LAUNCH_ID, "project_id": PROJECT_ID, "status": "completed"})

    # -- Pipeline executors (expensive) ----------------------------------------
    m_create_job = _p("app.db.jobs.create_job", return_value=uuid4())
    m_start_job = _p("app.db.jobs.start_job")
    m_complete_job = _p("app.db.jobs.complete_job")
    m_fail_job = _p("app.db.jobs.fail_job")
    m_run_onboarding = _p("app.graphs.onboarding_graph.run_onboarding", return_value={"features": 3, "personas": 2, "vp_steps": 5})
    m_enrich_client = _p("app.chains.enrich_client.enrich_client", new_callable=AsyncMock, return_value={"fields_enriched": 5})
    m_stakeholder_intel = _p("app.agents.stakeholder_intelligence_agent.invoke_stakeholder_intelligence_agent", new_callable=AsyncMock, return_value={})
    m_foundation = _p("app.chains.run_strategic_foundation.run_strategic_foundation", new_callable=AsyncMock, return_value={"business_drivers_created": 2, "competitor_refs_created": 3})
    m_readiness = _p("app.chains.assess_discovery_readiness.assess_discovery_readiness", return_value={"overall_score": 75})
    m_discovery = _p("app.graphs.discovery_pipeline_graph.run_discovery_pipeline", return_value={"business_drivers_count": 4, "competitors_count": 6})
    m_get_supabase = _p("app.db.supabase_client.get_supabase")

    # -- Thread control + asyncio fix ------------------------------------------
    _p("app.api.project_launch.threading.Thread", new=_SynchronousThread)
    _p("app.api.project_launch.asyncio.run", side_effect=_safe_asyncio_run)

    # Supabase mock for discovery executor's project lookup
    mock_execute = MagicMock()
    mock_execute.data = {"id": PROJECT_ID, "name": "Test", "client_name": "Acme", "metadata": {}}
    (
        m_get_supabase.return_value
        .table.return_value
        .select.return_value
        .eq.return_value
        .maybe_single.return_value
        .execute
    ).return_value = mock_execute

    yield {
        "create_project": m_create_project,
        "create_client": m_create_client,
        "get_client": m_get_client,
        "link_project_to_client": m_link,
        "create_stakeholder": m_create_stakeholder,
        "update_stakeholder": m_update_stakeholder,
        "insert_signal": m_insert_signal,
        "chunk_text": m_chunk,
        "embed_texts": m_embed,
        "insert_signal_chunks": m_insert_chunks,
        "create_launch": m_create_launch,
        "create_launch_step": m_create_launch_step,
        "get_launch_steps": m_get_launch_steps,
        "update_launch_status": m_update_launch_status,
        "update_step_status": m_update_step_status,
        "get_launch": m_get_launch,
        "create_job": m_create_job,
        "start_job": m_start_job,
        "complete_job": m_complete_job,
        "fail_job": m_fail_job,
        "run_onboarding": m_run_onboarding,
        "enrich_client": m_enrich_client,
        "stakeholder_intel": m_stakeholder_intel,
        "foundation": m_foundation,
        "readiness": m_readiness,
        "discovery": m_discovery,
        "get_supabase": m_get_supabase,
    }

    for p in patchers:
        p.stop()


# ===========================================================================
# TestLaunchEndpoint
# ===========================================================================


class TestLaunchEndpoint:
    """Tests for POST /projects/launch — sync phase + response shape."""

    def test_full_launch_happy_path(self, mock_launch_deps):
        mocks = mock_launch_deps

        resp = client.post("/v1/projects/launch", json={
            "project_name": "Acme Portal",
            "problem_description": "We need a customer portal with SSO",
            "client_name": "Acme Corp",
            "client_website": "https://acme.com",
            "stakeholders": [
                {"first_name": "Jane", "last_name": "Doe", "linkedin_url": "https://linkedin.com/in/jane"},
            ],
            "auto_discovery": True,
        })

        assert resp.status_code == 200
        body = resp.json()
        assert body["project_id"] == PROJECT_ID
        assert body["launch_id"] == LAUNCH_ID
        assert body["client_id"] == CLIENT_ID
        assert len(body["stakeholder_ids"]) == 1
        assert body["status"] == "pending"
        assert len(body["steps"]) == 6

        # Sync-phase calls
        mocks["create_project"].assert_called_once()
        mocks["create_client"].assert_called_once()
        mocks["link_project_to_client"].assert_called_once()
        mocks["create_stakeholder"].assert_called_once()
        mocks["insert_signal"].assert_called_once()
        mocks["chunk_text"].assert_called_once()
        mocks["embed_texts"].assert_called_once()
        mocks["insert_signal_chunks"].assert_called_once()

        # Pipeline ran (thread was synchronous)
        mocks["run_onboarding"].assert_called_once()
        mocks["enrich_client"].assert_called_once()
        mocks["stakeholder_intel"].assert_called_once()
        mocks["foundation"].assert_called_once()
        mocks["readiness"].assert_called_once()
        mocks["discovery"].assert_called_once()

    def test_minimal_launch_name_only(self, mock_launch_deps):
        mocks = mock_launch_deps

        resp = client.post("/v1/projects/launch", json={
            "project_name": "Quick Test",
        })

        assert resp.status_code == 200
        body = resp.json()
        assert body["project_id"] == PROJECT_ID
        assert body["client_id"] is None
        assert body["stakeholder_ids"] == []

        # No signal ingestion (no description)
        mocks["insert_signal"].assert_not_called()
        mocks["chunk_text"].assert_not_called()

        # No client
        mocks["create_client"].assert_not_called()
        mocks["link_project_to_client"].assert_not_called()

        # Pipeline: all steps should be skipped (no signal, no client, no stakeholders)
        mocks["run_onboarding"].assert_not_called()
        mocks["enrich_client"].assert_not_called()
        mocks["stakeholder_intel"].assert_not_called()

    def test_existing_client_link(self, mock_launch_deps):
        mocks = mock_launch_deps

        resp = client.post("/v1/projects/launch", json={
            "project_name": "Existing Client Project",
            "client_id": CLIENT_ID,
        })

        assert resp.status_code == 200
        body = resp.json()
        assert body["client_id"] == CLIENT_ID

        # Should link, not create
        mocks["link_project_to_client"].assert_called_once()
        mocks["create_client"].assert_not_called()
        mocks["get_client"].assert_called_once()

    def test_client_failure_nonfatal(self, mock_launch_deps):
        mocks = mock_launch_deps
        mocks["create_client"].side_effect = Exception("DB down")

        resp = client.post("/v1/projects/launch", json={
            "project_name": "Client Fail Test",
            "problem_description": "Some description for signal",
            "client_name": "BadCorp",
        })

        assert resp.status_code == 200
        body = resp.json()
        assert body["project_id"] == PROJECT_ID
        assert body["client_id"] is None

        # Pipeline still runs — onboarding should fire since we have a description
        mocks["run_onboarding"].assert_called_once()

    def test_stakeholder_failure_nonfatal(self, mock_launch_deps):
        mocks = mock_launch_deps
        mocks["create_stakeholder"].side_effect = [
            {"id": STAKEHOLDER_ID_1, "name": "Jane Doe"},
            Exception("DB error on 2nd stakeholder"),
        ]

        resp = client.post("/v1/projects/launch", json={
            "project_name": "Stakeholder Fail Test",
            "stakeholders": [
                {"first_name": "Jane", "last_name": "Doe"},
                {"first_name": "Bad", "last_name": "Person"},
            ],
        })

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["stakeholder_ids"]) == 1
        assert body["stakeholder_ids"][0] == STAKEHOLDER_ID_1

    def test_project_creation_failure_fatal(self, mock_launch_deps):
        mocks = mock_launch_deps
        mocks["create_project"].side_effect = Exception("DB exploded")

        resp = client.post("/v1/projects/launch", json={
            "project_name": "Doomed Project",
        })

        assert resp.status_code == 500

    def test_validation_empty_name(self, mock_launch_deps):
        resp = client.post("/v1/projects/launch", json={
            "project_name": "",
        })

        assert resp.status_code == 422


# ===========================================================================
# TestPipelineOrchestration
# ===========================================================================


class TestPipelineOrchestration:
    """Tests for the background pipeline — dependency resolution, skip logic,
    failure cascading, and final status determination."""

    def test_dependency_resolution(self, mock_launch_deps):
        """All 6 steps run in correct dependency order."""
        mocks = mock_launch_deps

        client.post("/v1/projects/launch", json={
            "project_name": "Full Pipeline",
            "problem_description": "We need everything",
            "client_name": "Acme",
            "client_website": "https://acme.com",
            "stakeholders": [
                {"first_name": "Jane", "last_name": "Doe", "linkedin_url": "https://linkedin.com/in/jane"},
            ],
            "auto_discovery": True,
        })

        # Extract the step keys that were set to "running" (in order)
        running_calls = [
            c for c in mocks["update_step_status"].call_args_list
            if len(c.args) >= 3 and c.args[2] == "running"
        ]
        running_order = [c.args[1] for c in running_calls]

        # Independent steps first (onboarding, client_enrichment, stakeholder_enrichment)
        # Then foundation (after onboarding), readiness (after foundation+client_enrichment),
        # then discovery (after readiness)
        assert "onboarding" in running_order
        assert "client_enrichment" in running_order
        assert "stakeholder_enrichment" in running_order

        idx_onboarding = running_order.index("onboarding")
        idx_foundation = running_order.index("foundation")
        idx_readiness = running_order.index("readiness_check")
        idx_discovery = running_order.index("discovery")

        assert idx_foundation > idx_onboarding
        assert idx_readiness > idx_foundation
        assert idx_discovery > idx_readiness

    def test_onboarding_failure_cascades(self, mock_launch_deps):
        """Onboarding failure → foundation, readiness, discovery skipped.
        client_enrichment and stakeholder_enrichment still run (independent)."""
        mocks = mock_launch_deps
        mocks["run_onboarding"].side_effect = Exception("LLM timeout")

        client.post("/v1/projects/launch", json={
            "project_name": "Cascade Test",
            "problem_description": "Description for signal",
            "client_name": "Acme",
            "client_website": "https://acme.com",
            "stakeholders": [
                {"first_name": "Jane", "last_name": "Doe", "linkedin_url": "https://linkedin.com/in/jane"},
            ],
            "auto_discovery": True,
        })

        status_calls = {
            c.args[1]: c.args[2]
            for c in mocks["update_step_status"].call_args_list
            if len(c.args) >= 3 and c.args[2] in ("completed", "failed", "skipped")
        }

        assert status_calls["onboarding"] == "failed"
        assert status_calls["foundation"] == "skipped"
        # client_enrichment and stakeholder_enrichment are independent
        assert status_calls["client_enrichment"] == "completed"
        assert status_calls["stakeholder_enrichment"] == "completed"

        # Final launch status: onboarding failed → "failed" is possible, but
        # other steps succeeded too. Since onboarding==failed → final = "failed"
        # per the logic: `statuses.get("onboarding") != "failed"` is False
        final_status_call = mocks["update_launch_status"].call_args_list[-1]
        assert final_status_call.args[1] == "failed"

    def test_client_enrichment_soft_dependency(self, mock_launch_deps):
        """client_enrichment failure doesn't block readiness_check (soft dep)."""
        mocks = mock_launch_deps
        mocks["enrich_client"].side_effect = Exception("Enrichment failed")

        client.post("/v1/projects/launch", json={
            "project_name": "Soft Dep Test",
            "problem_description": "Description",
            "client_name": "Acme",
            "client_website": "https://acme.com",
            "auto_discovery": True,
        })

        status_calls = {
            c.args[1]: c.args[2]
            for c in mocks["update_step_status"].call_args_list
            if len(c.args) >= 3 and c.args[2] in ("completed", "failed", "skipped")
        }

        assert status_calls["client_enrichment"] == "failed"
        assert status_calls["foundation"] == "completed"
        # readiness_check should still run — client_enrichment is soft dep
        assert status_calls["readiness_check"] == "completed"
        assert status_calls["discovery"] == "completed"

        final_status_call = mocks["update_launch_status"].call_args_list[-1]
        assert final_status_call.args[1] == "completed_with_errors"

    def test_skip_conditions_no_description(self, mock_launch_deps):
        """No description → onboarding skipped → foundation skipped via cascade."""
        mocks = mock_launch_deps

        client.post("/v1/projects/launch", json={
            "project_name": "Skip Test",
        })

        status_calls = {}
        for c in mocks["update_step_status"].call_args_list:
            if len(c.args) >= 3 and c.args[2] in ("skipped",):
                status_calls[c.args[1]] = c.kwargs.get("result_summary", "") or ""

        assert "onboarding" in status_calls
        assert "No project description" in status_calls["onboarding"]

    def test_skip_conditions_no_client_website(self, mock_launch_deps):
        """No client website → client_enrichment skipped."""
        mocks = mock_launch_deps

        client.post("/v1/projects/launch", json={
            "project_name": "No Website",
            "client_name": "Acme",  # no website
        })

        skip_calls = {
            c.args[1]: c.kwargs.get("result_summary", "")
            for c in mocks["update_step_status"].call_args_list
            if len(c.args) >= 3 and c.args[2] == "skipped"
        }

        assert "client_enrichment" in skip_calls
        assert "No client website" in skip_calls["client_enrichment"]

    def test_skip_conditions_no_linkedin(self, mock_launch_deps):
        """No stakeholders with LinkedIn → stakeholder_enrichment skipped."""
        mocks = mock_launch_deps

        client.post("/v1/projects/launch", json={
            "project_name": "No LinkedIn",
            "stakeholders": [
                {"first_name": "Jane", "last_name": "Doe"},  # no linkedin_url
            ],
        })

        skip_calls = {
            c.args[1]: c.kwargs.get("result_summary", "")
            for c in mocks["update_step_status"].call_args_list
            if len(c.args) >= 3 and c.args[2] == "skipped"
        }

        assert "stakeholder_enrichment" in skip_calls
        assert "No stakeholders with LinkedIn" in skip_calls["stakeholder_enrichment"]

    def test_discovery_readiness_threshold(self, mock_launch_deps):
        """Readiness score below 60 → discovery fails."""
        mocks = mock_launch_deps
        mocks["readiness"].return_value = {"overall_score": 50}

        client.post("/v1/projects/launch", json={
            "project_name": "Low Readiness",
            "problem_description": "Some description",
            "client_name": "Acme",
            "client_website": "https://acme.com",
            "auto_discovery": True,
        })

        # Find the discovery step status
        discovery_fail = [
            c for c in mocks["update_step_status"].call_args_list
            if len(c.args) >= 3 and c.args[1] == "discovery" and c.args[2] == "failed"
        ]
        assert len(discovery_fail) == 1
        error_msg = discovery_fail[0].kwargs.get("error_message", "")
        assert "below threshold" in error_msg

    def test_discovery_disabled(self, mock_launch_deps):
        """auto_discovery=false → discovery skipped."""
        mocks = mock_launch_deps

        client.post("/v1/projects/launch", json={
            "project_name": "No Discovery",
            "problem_description": "Some description",
            "client_name": "Acme",
            "client_website": "https://acme.com",
            "auto_discovery": False,
        })

        skip_calls = {
            c.args[1]: c.kwargs.get("result_summary", "")
            for c in mocks["update_step_status"].call_args_list
            if len(c.args) >= 3 and c.args[2] == "skipped"
        }

        assert "discovery" in skip_calls
        assert "Auto-discovery not enabled" in skip_calls["discovery"]

    def test_final_status_completed(self, mock_launch_deps):
        """All steps succeed → final status 'completed'."""
        mocks = mock_launch_deps

        client.post("/v1/projects/launch", json={
            "project_name": "Happy Path",
            "problem_description": "Full description",
            "client_name": "Acme",
            "client_website": "https://acme.com",
            "stakeholders": [
                {"first_name": "Jane", "last_name": "Doe", "linkedin_url": "https://linkedin.com/in/jane"},
            ],
            "auto_discovery": True,
        })

        final_call = mocks["update_launch_status"].call_args_list[-1]
        assert final_call.args[1] == "completed"

    def test_final_status_completed_with_errors(self, mock_launch_deps):
        """Non-onboarding step fails → 'completed_with_errors'."""
        mocks = mock_launch_deps
        mocks["enrich_client"].side_effect = Exception("Enrichment boom")

        client.post("/v1/projects/launch", json={
            "project_name": "Partial Fail",
            "problem_description": "Has description",
            "client_name": "Acme",
            "client_website": "https://acme.com",
            "auto_discovery": False,
        })

        final_call = mocks["update_launch_status"].call_args_list[-1]
        assert final_call.args[1] == "completed_with_errors"

    def test_final_status_failed(self, mock_launch_deps):
        """Onboarding fails with no independent successes that avoid 'failed'."""
        mocks = mock_launch_deps
        mocks["run_onboarding"].side_effect = Exception("Onboarding crash")

        # Only description, no client/stakeholders → independent steps all skip
        client.post("/v1/projects/launch", json={
            "project_name": "Total Fail",
            "problem_description": "Something",
        })

        final_call = mocks["update_launch_status"].call_args_list[-1]
        assert final_call.args[1] == "failed"


# ===========================================================================
# TestProgressEndpoint
# ===========================================================================


class TestProgressEndpoint:
    """Tests for GET /projects/{project_id}/launch/{launch_id}/progress."""

    def test_progress_happy_path(self, mock_launch_deps):
        mocks = mock_launch_deps

        # Override get_launch_steps for the progress endpoint with mixed statuses
        mixed_steps = _make_step_dicts()
        mixed_steps[0]["status"] = "completed"  # onboarding
        mixed_steps[1]["status"] = "completed"  # client_enrichment
        mixed_steps[2]["status"] = "completed"  # stakeholder_enrichment
        mixed_steps[3]["status"] = "running"    # foundation
        mixed_steps[4]["status"] = "pending"    # readiness_check
        mixed_steps[5]["status"] = "pending"    # discovery
        mocks["get_launch_steps"].return_value = mixed_steps

        resp = client.get(f"/v1/projects/{PROJECT_ID}/launch/{LAUNCH_ID}/progress")

        assert resp.status_code == 200
        body = resp.json()
        assert body["launch_id"] == LAUNCH_ID
        assert body["project_id"] == PROJECT_ID
        assert body["status"] == "completed"  # from get_launch mock
        assert len(body["steps"]) == 6
        # 3 completed out of 6 resolved (running/pending don't count)
        assert body["progress_pct"] == 50

    def test_progress_not_found(self, mock_launch_deps):
        mocks = mock_launch_deps
        mocks["get_launch"].return_value = None

        fake_launch = str(uuid4())
        resp = client.get(f"/v1/projects/{PROJECT_ID}/launch/{fake_launch}/progress")

        assert resp.status_code == 404

    def test_progress_wrong_project(self, mock_launch_deps):
        mocks = mock_launch_deps
        mocks["get_launch"].return_value = {
            "id": LAUNCH_ID,
            "project_id": str(uuid4()),  # different project
            "status": "completed",
        }

        resp = client.get(f"/v1/projects/{PROJECT_ID}/launch/{LAUNCH_ID}/progress")

        assert resp.status_code == 404

    def test_progress_calculation(self, mock_launch_deps):
        """3 completed + 1 failed + 2 pending = 4 resolved / 6 = 66%."""
        mocks = mock_launch_deps

        calc_steps = _make_step_dicts()
        calc_steps[0]["status"] = "completed"
        calc_steps[1]["status"] = "completed"
        calc_steps[2]["status"] = "completed"
        calc_steps[3]["status"] = "failed"
        calc_steps[4]["status"] = "pending"
        calc_steps[5]["status"] = "pending"
        mocks["get_launch_steps"].return_value = calc_steps

        resp = client.get(f"/v1/projects/{PROJECT_ID}/launch/{LAUNCH_ID}/progress")

        assert resp.status_code == 200
        assert resp.json()["progress_pct"] == 66
