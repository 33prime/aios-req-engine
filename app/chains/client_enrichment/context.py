"""Shared context loading for client enrichment chains.

Loads client, projects, stakeholders, and signals ONCE and shares
across all chain invocations via PydanticAI dependency injection.
"""

import json
from dataclasses import dataclass, field
from uuid import UUID

from app.db.clients import get_client, get_client_projects
from app.db.supabase_client import get_supabase


@dataclass
class ClientContext:
    """Pre-loaded client data shared across enrichment chains."""

    client_id: UUID
    client: dict
    projects: list[dict] = field(default_factory=list)
    stakeholders: list[dict] = field(default_factory=list)
    signals: list[dict] = field(default_factory=list)
    constraints: list[dict] = field(default_factory=list)
    drivers: list[dict] = field(default_factory=list)
    features: list[dict] = field(default_factory=list)

    @property
    def client_name(self) -> str:
        return self.client.get("name", "Unknown")

    @property
    def industry(self) -> str:
        return self.client.get("industry", "Unknown")

    @property
    def project_ids(self) -> list[str]:
        return [str(p["id"]) for p in self.projects if p.get("id")]


async def load_client_context(client_id: UUID) -> ClientContext:
    """Load all cross-project data for a client in one pass.

    This replaces the pattern where each tool independently re-loaded
    the same client/projects/stakeholders data.
    """
    client = get_client(client_id)
    if not client:
        raise ValueError(f"Client {client_id} not found")

    projects = get_client_projects(client_id)
    project_ids = [p["id"] for p in projects]

    if not project_ids:
        return ClientContext(client_id=client_id, client=client, projects=projects)

    sb = get_supabase()

    # Load cross-project data in batch
    stakeholders = []
    signals = []
    constraints = []
    drivers = []
    features = []

    for pid in project_ids:
        sh = (
            sb.table("stakeholders")
            .select(
                "id, name, first_name, last_name, role, email, stakeholder_type, "
                "influence_level, is_primary_contact, decision_authority, domain_expertise, "
                "concerns, project_id"
            )
            .eq("project_id", pid)
            .execute()
        )
        stakeholders.extend(sh.data)

        sig = (
            sb.table("signals")
            .select("raw_text, signal_type, source, project_id")
            .eq("project_id", pid)
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        signals.extend(sig.data)

        c = (
            sb.table("constraints")
            .select("title, description, constraint_type, severity")
            .eq("project_id", pid)
            .execute()
        )
        constraints.extend(c.data)

        d = (
            sb.table("business_drivers")
            .select("description, driver_type, severity")
            .eq("project_id", pid)
            .execute()
        )
        drivers.extend(d.data)

        ft = (
            sb.table("features")
            .select("name, overview, priority_group")
            .eq("project_id", pid)
            .limit(20)
            .execute()
        )
        features.extend(ft.data)

    return ClientContext(
        client_id=client_id,
        client=client,
        projects=projects,
        stakeholders=stakeholders,
        signals=signals,
        constraints=constraints,
        drivers=drivers,
        features=features,
    )


def safe_json(val, expected_type=list):
    """Parse JSON string safely, returning default on failure."""
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            if isinstance(parsed, expected_type):
                return parsed
        except (ValueError, TypeError):
            pass
        return expected_type()
    return val if isinstance(val, expected_type) else expected_type()
