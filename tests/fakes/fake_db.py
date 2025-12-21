"""Fake in-memory database layer for Phase 2B behavioral testing."""

from typing import Any, Dict, List
from uuid import UUID

from tests.fixtures_phase2b import (
    CANONICAL_BASELINE,
    EXTRACTED_FACTS_ID_1,
    EXTRACTED_FACTS_ID_2,
    PROJECT_ID,
    SAMPLE_CHUNKS,
    SAMPLE_EXTRACTED_FACTS,
    SAMPLE_SIGNALS,
)


class FakeDB:
    """In-memory database implementation for testing."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all stores to initial state."""
        self.signals: Dict[str, Dict[str, Any]] = SAMPLE_SIGNALS.copy()
        self.signal_chunks: Dict[str, List[Dict[str, Any]]] = SAMPLE_CHUNKS.copy()
        self.extracted_facts: List[Dict[str, Any]] = SAMPLE_EXTRACTED_FACTS.copy()
        self.prd_sections: List[Dict[str, Any]] = CANONICAL_BASELINE["prd_sections"].copy()
        self.vp_steps: List[Dict[str, Any]] = CANONICAL_BASELINE["vp_steps"].copy()
        self.features: List[Dict[str, Any]] = CANONICAL_BASELINE["features"].copy()
        self.confirmations: List[Dict[str, Any]] = []
        self.project_state: Dict[str, Any] = {
            "project_id": str(PROJECT_ID),
            "last_reconciled_at": None,
            "last_extracted_facts_id": str(EXTRACTED_FACTS_ID_1),  # Start with first facts processed
            "last_insight_id": None,
            "last_signal_id": None,
        }
        self.revisions: List[Dict[str, Any]] = []

    # Signal operations
    def get_signal(self, signal_id: UUID) -> Dict[str, Any] | None:
        """Get signal by ID."""
        return self.signals.get(str(signal_id))

    def insert_signal(self, signal_data: Dict[str, Any]) -> UUID:
        """Insert a new signal."""
        signal_id = signal_data["id"]
        self.signals[signal_id] = signal_data
        return UUID(signal_id)

    def list_signal_chunks(self, signal_id: UUID) -> List[Dict[str, Any]]:
        """List chunks for a signal."""
        return self.signal_chunks.get(str(signal_id), [])

    # Extracted facts operations
    def list_latest_extracted_facts(self, project_id: UUID, limit: int = 5) -> List[Dict[str, Any]]:
        """List latest extracted facts for a project."""
        facts = [f for f in self.extracted_facts if f["project_id"] == str(project_id)]
        facts.sort(key=lambda x: x["created_at"], reverse=True)
        return facts[:limit]

    def insert_extracted_facts(self, facts_data: Dict[str, Any]) -> UUID:
        """Insert extracted facts."""
        facts_id = facts_data["id"]
        self.extracted_facts.append(facts_data)
        return UUID(facts_id)

    # PRD sections operations
    def list_prd_sections(self, project_id: UUID) -> List[Dict[str, Any]]:
        """List PRD sections for a project."""
        return [s for s in self.prd_sections if s["project_id"] == str(project_id)]

    def upsert_prd_section(self, project_id: UUID, slug: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Upsert PRD section."""
        # Find existing section
        existing = None
        for section in self.prd_sections:
            if section["project_id"] == str(project_id) and section["slug"] == slug:
                existing = section
                break

        if existing:
            # Update existing
            existing.update(payload)
            return existing
        else:
            # Create new
            new_section = {
                "id": payload.get("id", str(UUID(int=0))),  # Generate ID if not provided
                "project_id": str(project_id),
                "slug": slug,
                **payload
            }
            self.prd_sections.append(new_section)
            return new_section

    # VP steps operations
    def list_vp_steps(self, project_id: UUID) -> List[Dict[str, Any]]:
        """List VP steps for a project."""
        return [s for s in self.vp_steps if s["project_id"] == str(project_id)]

    def upsert_vp_step(self, project_id: UUID, step_index: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Upsert VP step."""
        # Find existing step
        existing = None
        for step in self.vp_steps:
            if step["project_id"] == str(project_id) and step["step_index"] == step_index:
                existing = step
                break

        if existing:
            # Update existing
            existing.update(payload)
            return existing
        else:
            # Create new
            new_step = {
                "id": payload.get("id", str(UUID(int=0))),
                "project_id": str(project_id),
                "step_index": step_index,
                **payload
            }
            self.vp_steps.append(new_step)
            return new_step

    # Features operations
    def list_features(self, project_id: UUID) -> List[Dict[str, Any]]:
        """List features for a project."""
        return [f for f in self.features if f["project_id"] == str(project_id)]

    def bulk_replace_features(self, project_id: UUID, features: List[Dict[str, Any]]) -> int:
        """Replace all features for a project."""
        # Remove existing features
        self.features = [f for f in self.features if f["project_id"] != str(project_id)]

        # Add new features
        for feature in features:
            feature["project_id"] = str(project_id)
            if "id" not in feature:
                feature["id"] = str(UUID(int=0))  # Generate ID if not provided
            self.features.append(feature)

        return len(features)

    # Confirmations operations
    def upsert_confirmation_item(self, project_id: UUID, key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Upsert confirmation item with unique constraint on (project_id, key)."""
        # Find existing confirmation
        existing = None
        for conf in self.confirmations:
            if conf["project_id"] == str(project_id) and conf["key"] == key:
                existing = conf
                break

        if existing:
            # Update existing
            existing.update(payload)
            return existing
        else:
            # Create new
            new_conf = {
                "id": payload.get("id", str(UUID(int=0))),
                "project_id": str(project_id),
                "key": key,
                **payload
            }
            self.confirmations.append(new_conf)
            return new_conf

    def list_confirmation_items(self, project_id: UUID, status: str | None = None) -> List[Dict[str, Any]]:
        """List confirmation items for a project, optionally filtered by status."""
        confs = [c for c in self.confirmations if c["project_id"] == str(project_id)]
        if status:
            confs = [c for c in confs if c["status"] == status]
        return confs

    def get_confirmation_item(self, confirmation_id: UUID) -> Dict[str, Any] | None:
        """Get confirmation item by ID."""
        for conf in self.confirmations:
            if conf["id"] == str(confirmation_id):
                return conf
        return None

    def set_confirmation_status(self, confirmation_id: UUID, status: str, resolution_evidence: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Update confirmation status."""
        for conf in self.confirmations:
            if conf["id"] == str(confirmation_id):
                conf["status"] = status
                if resolution_evidence:
                    conf["resolution_evidence"] = resolution_evidence
                return conf
        raise ValueError(f"Confirmation item {confirmation_id} not found")

    # Project state operations
    def get_project_state(self, project_id: UUID) -> Dict[str, Any]:
        """Get project state."""
        if self.project_state["project_id"] == str(project_id):
            return self.project_state.copy()
        return {
            "project_id": str(project_id),
            "last_reconciled_at": None,
            "last_extracted_facts_id": None,
            "last_insight_id": None,
            "last_signal_id": None,
        }

    def update_project_state(self, project_id: UUID, patch: Dict[str, Any]) -> Dict[str, Any]:
        """Update project state."""
        if self.project_state["project_id"] == str(project_id):
            self.project_state.update(patch)
            return self.project_state.copy()

        # Create new state if doesn't exist
        self.project_state = {
            "project_id": str(project_id),
            **patch
        }
        return self.project_state.copy()

    # Revisions operations
    def insert_state_revision(self, project_id: UUID, run_id: UUID, job_id: UUID | None, input_summary: Dict[str, Any], diff: Dict[str, Any]) -> UUID:
        """Insert state revision."""
        revision_id = UUID(int=0)  # Generate simple ID for testing
        revision = {
            "id": str(revision_id),
            "project_id": str(project_id),
            "run_id": str(run_id),
            "job_id": str(job_id) if job_id else None,
            "input_summary": input_summary,
            "diff": diff,
            "created_at": "2025-12-21T21:00:00.000000+00:00"
        }
        self.revisions.append(revision)
        return revision_id

    def list_state_revisions(self, project_id: UUID, limit: int = 10) -> List[Dict[str, Any]]:
        """List state revisions for a project."""
        revisions = [r for r in self.revisions if r["project_id"] == str(project_id)]
        revisions.sort(key=lambda x: x["created_at"], reverse=True)
        return revisions[:limit]


# Global fake DB instance
fake_db = FakeDB()
