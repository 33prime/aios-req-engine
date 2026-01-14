"""
Unified Dependency Manager.

Manages relationships between entities and handles cascade propagation.
Replaces cascade_handler.py and entity_cascade.py with a single system.

Entity Relationships:
- Feature → Persona (feature serves persona's goals)
- Feature → VP Step (feature enables VP step)
- Persona → VP Step (persona experiences VP step)
- VP Step → Feature (VP step requires feature)

Cascade Types:
- staleness: Mark dependents as potentially stale
- notification: Notify about upstream changes
- enrichment: Queue dependents for re-enrichment

Usage:
    from app.core.dependency_manager import DependencyManager

    manager = DependencyManager(project_id)

    # Register a dependency
    manager.register_dependency(
        from_type="feature",
        from_id=feature_id,
        to_type="vp_step",
        to_id=vp_step_id,
        relationship="enables"
    )

    # Propagate changes
    affected = manager.propagate_change(
        entity_type="feature",
        entity_id=feature_id,
        change_type="updated"
    )
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


class RelationshipType(Enum):
    """Types of relationships between entities."""
    SERVES = "serves"          # Feature serves persona
    ENABLES = "enables"        # Feature enables VP step
    EXPERIENCES = "experiences"  # Persona experiences VP step
    REQUIRES = "requires"      # VP step requires feature
    DEPENDS_ON = "depends_on"  # Generic dependency
    REFERENCES = "references"  # Soft reference


class CascadeType(Enum):
    """Types of cascade actions."""
    STALENESS = "staleness"       # Mark as stale
    NOTIFICATION = "notification"  # Create notification
    ENRICHMENT = "enrichment"     # Queue for re-enrichment
    HEALTH_CHECK = "health_check"  # Trigger health recalculation


@dataclass
class Dependency:
    """A dependency relationship between two entities."""
    id: str
    from_type: str
    from_id: str
    to_type: str
    to_id: str
    relationship: RelationshipType
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None


@dataclass
class CascadeResult:
    """Result of a cascade operation."""
    source_type: str
    source_id: str
    change_type: str
    affected_entities: list[dict[str, Any]]
    notifications_created: int = 0
    staleness_marked: int = 0
    enrichment_queued: int = 0


class DependencyManager:
    """
    Unified dependency management and cascade propagation.
    """

    def __init__(self, project_id: UUID | str):
        self.project_id = str(project_id)
        self.supabase = get_supabase()

    # =========================================================================
    # Dependency Registration
    # =========================================================================

    def register_dependency(
        self,
        from_type: str,
        from_id: UUID | str,
        to_type: str,
        to_id: UUID | str,
        relationship: str | RelationshipType,
        metadata: dict[str, Any] | None = None,
    ) -> Dependency | None:
        """
        Register a dependency between two entities.

        Args:
            from_type: Source entity type
            from_id: Source entity ID
            to_type: Target entity type
            to_id: Target entity ID
            relationship: Type of relationship
            metadata: Additional metadata

        Returns:
            Created Dependency or None if already exists
        """
        from_id_str = str(from_id)
        to_id_str = str(to_id)

        if isinstance(relationship, str):
            try:
                relationship = RelationshipType(relationship)
            except ValueError:
                relationship = RelationshipType.DEPENDS_ON

        # Check if dependency already exists
        existing = (
            self.supabase.table("entity_dependencies")
            .select("id")
            .eq("project_id", self.project_id)
            .eq("from_entity_type", from_type)
            .eq("from_entity_id", from_id_str)
            .eq("to_entity_type", to_type)
            .eq("to_entity_id", to_id_str)
            .maybe_single()
            .execute()
        )

        if existing.data:
            logger.debug(f"Dependency already exists: {from_type}:{from_id_str} → {to_type}:{to_id_str}")
            return None

        # Create dependency
        data = {
            "project_id": self.project_id,
            "from_entity_type": from_type,
            "from_entity_id": from_id_str,
            "to_entity_type": to_type,
            "to_entity_id": to_id_str,
            "relationship_type": relationship.value,
            "metadata": metadata or {},
        }

        try:
            response = self.supabase.table("entity_dependencies").insert(data).execute()

            if response.data:
                dep = response.data[0]
                logger.info(
                    f"Registered dependency: {from_type}:{from_id_str} → {to_type}:{to_id_str} ({relationship.value})"
                )
                return Dependency(
                    id=dep["id"],
                    from_type=from_type,
                    from_id=from_id_str,
                    to_type=to_type,
                    to_id=to_id_str,
                    relationship=relationship,
                    metadata=metadata or {},
                )
        except Exception as e:
            logger.error(f"Failed to register dependency: {e}")

        return None

    def remove_dependency(
        self,
        from_type: str,
        from_id: UUID | str,
        to_type: str,
        to_id: UUID | str,
    ) -> bool:
        """Remove a specific dependency."""
        try:
            self.supabase.table("entity_dependencies").delete().eq(
                "project_id", self.project_id
            ).eq("from_entity_type", from_type).eq(
                "from_entity_id", str(from_id)
            ).eq("to_entity_type", to_type).eq(
                "to_entity_id", str(to_id)
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to remove dependency: {e}")
            return False

    # =========================================================================
    # Dependency Queries
    # =========================================================================

    def get_dependents(
        self,
        entity_type: str,
        entity_id: UUID | str,
    ) -> list[Dependency]:
        """
        Get all entities that depend on this entity.

        Args:
            entity_type: Entity type
            entity_id: Entity ID

        Returns:
            List of dependent entity references
        """
        try:
            response = (
                self.supabase.table("entity_dependencies")
                .select("*")
                .eq("project_id", self.project_id)
                .eq("from_entity_type", entity_type)
                .eq("from_entity_id", str(entity_id))
                .execute()
            )

            return [
                Dependency(
                    id=d["id"],
                    from_type=d["from_entity_type"],
                    from_id=d["from_entity_id"],
                    to_type=d["to_entity_type"],
                    to_id=d["to_entity_id"],
                    relationship=RelationshipType(d.get("relationship_type", "depends_on")),
                    metadata=d.get("metadata", {}),
                )
                for d in (response.data or [])
            ]
        except Exception as e:
            logger.error(f"Failed to get dependents: {e}")
            return []

    def get_dependencies(
        self,
        entity_type: str,
        entity_id: UUID | str,
    ) -> list[Dependency]:
        """
        Get all entities this entity depends on.

        Args:
            entity_type: Entity type
            entity_id: Entity ID

        Returns:
            List of dependency references
        """
        try:
            response = (
                self.supabase.table("entity_dependencies")
                .select("*")
                .eq("project_id", self.project_id)
                .eq("to_entity_type", entity_type)
                .eq("to_entity_id", str(entity_id))
                .execute()
            )

            return [
                Dependency(
                    id=d["id"],
                    from_type=d["from_entity_type"],
                    from_id=d["from_entity_id"],
                    to_type=d["to_entity_type"],
                    to_id=d["to_entity_id"],
                    relationship=RelationshipType(d.get("relationship_type", "depends_on")),
                    metadata=d.get("metadata", {}),
                )
                for d in (response.data or [])
            ]
        except Exception as e:
            logger.error(f"Failed to get dependencies: {e}")
            return []

    def get_dependency_graph(self) -> dict[str, list[dict]]:
        """
        Get the full dependency graph for the project.

        Returns:
            Dict with edges grouped by source entity
        """
        try:
            response = (
                self.supabase.table("entity_dependencies")
                .select("*")
                .eq("project_id", self.project_id)
                .execute()
            )

            graph = {}
            for d in (response.data or []):
                key = f"{d['from_entity_type']}:{d['from_entity_id']}"
                if key not in graph:
                    graph[key] = []
                graph[key].append({
                    "to_type": d["to_entity_type"],
                    "to_id": d["to_entity_id"],
                    "relationship": d.get("relationship_type", "depends_on"),
                })

            return graph
        except Exception:
            return {}

    # =========================================================================
    # Cascade Propagation
    # =========================================================================

    def propagate_change(
        self,
        entity_type: str,
        entity_id: UUID | str,
        change_type: str,
        cascade_types: list[CascadeType] | None = None,
    ) -> CascadeResult:
        """
        Propagate a change through the dependency graph.

        Args:
            entity_type: Type of changed entity
            entity_id: ID of changed entity
            change_type: Type of change (created, updated, deleted, confirmed)
            cascade_types: Types of cascade actions to perform

        Returns:
            CascadeResult with affected entities and actions taken
        """
        entity_id_str = str(entity_id)

        if cascade_types is None:
            cascade_types = [CascadeType.STALENESS, CascadeType.NOTIFICATION]

        logger.info(
            f"Propagating {change_type} change for {entity_type}:{entity_id_str}",
            extra={"project_id": self.project_id},
        )

        # Get all dependents
        dependents = self.get_dependents(entity_type, entity_id_str)

        affected_entities = []
        staleness_marked = 0
        notifications_created = 0
        enrichment_queued = 0

        for dep in dependents:
            affected = {
                "type": dep.to_type,
                "id": dep.to_id,
                "relationship": dep.relationship.value,
            }
            affected_entities.append(affected)

            # Apply cascade actions
            if CascadeType.STALENESS in cascade_types:
                if self._mark_stale(dep.to_type, dep.to_id, entity_type, entity_id_str):
                    staleness_marked += 1

            if CascadeType.NOTIFICATION in cascade_types:
                if self._create_notification(dep.to_type, dep.to_id, change_type, entity_type, entity_id_str):
                    notifications_created += 1

            if CascadeType.ENRICHMENT in cascade_types:
                if self._queue_enrichment(dep.to_type, dep.to_id):
                    enrichment_queued += 1

        logger.info(
            f"Cascade complete: {len(affected_entities)} affected, "
            f"{staleness_marked} marked stale, {notifications_created} notifications",
            extra={"entity_type": entity_type, "entity_id": entity_id_str},
        )

        return CascadeResult(
            source_type=entity_type,
            source_id=entity_id_str,
            change_type=change_type,
            affected_entities=affected_entities,
            notifications_created=notifications_created,
            staleness_marked=staleness_marked,
            enrichment_queued=enrichment_queued,
        )

    def mark_stale(
        self,
        entity_type: str,
        entity_id: UUID | str,
        reason: str,
    ) -> list[dict]:
        """
        Mark an entity and its dependents as stale.

        Args:
            entity_type: Entity type
            entity_id: Entity ID
            reason: Reason for staleness

        Returns:
            List of affected entities
        """
        affected = []

        # Mark the entity itself
        if self._mark_stale(entity_type, str(entity_id), "direct", reason):
            affected.append({"type": entity_type, "id": str(entity_id)})

        # Get and mark dependents
        dependents = self.get_dependents(entity_type, entity_id)
        for dep in dependents:
            if self._mark_stale(dep.to_type, dep.to_id, entity_type, str(entity_id)):
                affected.append({"type": dep.to_type, "id": dep.to_id})

        return affected

    def _mark_stale(
        self,
        entity_type: str,
        entity_id: str,
        source_type: str,
        source_id: str,
    ) -> bool:
        """Mark a single entity as stale."""
        try:
            table_name = _get_table_name(entity_type)

            # Update staleness metadata
            self.supabase.table(table_name).update({
                "is_stale": True,
                "stale_reason": f"Upstream {source_type} {source_id} changed",
                "stale_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", entity_id).execute()

            return True
        except Exception as e:
            logger.debug(f"Could not mark stale (column might not exist): {e}")
            return False

    def _create_notification(
        self,
        entity_type: str,
        entity_id: str,
        change_type: str,
        source_type: str,
        source_id: str,
    ) -> bool:
        """Create a notification for entity change."""
        try:
            self.supabase.table("activity_feed").insert({
                "project_id": self.project_id,
                "activity_type": "cascade_notification",
                "entity_type": entity_type,
                "entity_id": entity_id,
                "message": f"Upstream {source_type} was {change_type}",
                "metadata": {
                    "source_type": source_type,
                    "source_id": source_id,
                    "change_type": change_type,
                },
            }).execute()
            return True
        except Exception as e:
            logger.debug(f"Could not create notification: {e}")
            return False

    def _queue_enrichment(self, entity_type: str, entity_id: str) -> bool:
        """Queue entity for re-enrichment."""
        try:
            self.supabase.table("enrichment_queue").insert({
                "project_id": self.project_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "status": "pending",
                "priority": 3,  # Lower priority for cascade-triggered enrichment
            }).execute()
            return True
        except Exception:
            return False

    # =========================================================================
    # Auto-Discovery
    # =========================================================================

    def auto_discover_dependencies(self) -> int:
        """
        Auto-discover and register dependencies based on related_* fields.

        Scans entities for related_features, related_personas, etc. and
        creates dependency records.

        Returns:
            Number of dependencies discovered
        """
        count = 0

        # Features → Personas (via personas.related_features)
        count += self._discover_from_related_field(
            source_table="personas",
            source_type="persona",
            related_field="related_features",
            target_type="feature",
            relationship=RelationshipType.SERVES,
        )

        # Features → VP Steps (via vp_steps.related_features or features list)
        count += self._discover_from_related_field(
            source_table="vp_steps",
            source_type="vp_step",
            related_field="features",
            target_type="feature",
            relationship=RelationshipType.REQUIRES,
        )

        # Personas → VP Steps (via personas.related_vp_steps)
        count += self._discover_from_related_field(
            source_table="personas",
            source_type="persona",
            related_field="related_vp_steps",
            target_type="vp_step",
            relationship=RelationshipType.EXPERIENCES,
        )

        logger.info(f"Auto-discovered {count} dependencies")
        return count

    def _discover_from_related_field(
        self,
        source_table: str,
        source_type: str,
        related_field: str,
        target_type: str,
        relationship: RelationshipType,
    ) -> int:
        """Discover dependencies from a related_* field."""
        count = 0
        try:
            response = (
                self.supabase.table(source_table)
                .select(f"id, {related_field}")
                .eq("project_id", self.project_id)
                .execute()
            )

            for entity in (response.data or []):
                related_ids = entity.get(related_field) or []
                for target_id in related_ids:
                    if self.register_dependency(
                        from_type=target_type,  # Dependency is FROM target TO source
                        from_id=target_id,
                        to_type=source_type,
                        to_id=entity["id"],
                        relationship=relationship,
                    ):
                        count += 1

        except Exception as e:
            logger.debug(f"Could not discover from {source_table}.{related_field}: {e}")

        return count


def _get_table_name(entity_type: str) -> str:
    """Get database table name for entity type."""
    table_map = {
        "feature": "features",
        "persona": "personas",
        "vp_step": "vp_steps",
        "prd_section": "prd_sections",
    }
    return table_map.get(entity_type, f"{entity_type}s")


# Convenience functions

def propagate_entity_change(
    project_id: UUID | str,
    entity_type: str,
    entity_id: UUID | str,
    change_type: str,
) -> CascadeResult:
    """Propagate a change through the dependency graph."""
    manager = DependencyManager(project_id)
    return manager.propagate_change(entity_type, entity_id, change_type)


def get_entity_dependents(
    project_id: UUID | str,
    entity_type: str,
    entity_id: UUID | str,
) -> list[dict]:
    """Get all entities that depend on this entity."""
    manager = DependencyManager(project_id)
    deps = manager.get_dependents(entity_type, entity_id)
    return [{"type": d.to_type, "id": d.to_id, "relationship": d.relationship.value} for d in deps]
