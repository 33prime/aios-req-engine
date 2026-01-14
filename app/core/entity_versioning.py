"""
Entity Versioning Service.

Provides comprehensive version tracking for all entity types:
- Full version history with snapshots
- Field-level diffs between any two versions
- Source attribution (which signals contributed to which fields)
- Version comparison and restoration

Builds on top of existing change_tracking.py and enrichment_revisions infrastructure.

Usage:
    from app.core.entity_versioning import EntityVersioning

    versioning = EntityVersioning()

    # Get version history
    history = versioning.get_history("feature", feature_id)

    # Compare two versions
    diff = versioning.compare_versions("feature", feature_id, version_a=1, version_b=3)

    # Get source attribution for a field
    sources = versioning.get_field_sources("feature", feature_id, "acceptance_criteria")

    # Create a snapshot before making changes
    version_id = versioning.create_snapshot("feature", feature_id, entity_data)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


# Fields to exclude from diffs (metadata)
METADATA_FIELDS = {
    "id",
    "project_id",
    "created_at",
    "updated_at",
    "details_updated_at",
    "enriched_at",
    "confirmed_at",
}

# Fields that are too large for inline diff display
LARGE_FIELDS = {
    "embedding",
    "snapshot",
    "details",
    "enrichment",
}


@dataclass
class FieldChange:
    """Represents a change to a single field."""
    field_name: str
    old_value: Any
    new_value: Any
    change_type: str  # "added", "removed", "modified"

    def to_dict(self) -> dict:
        return {
            "field": self.field_name,
            "old": self.old_value,
            "new": self.new_value,
            "type": self.change_type,
        }


@dataclass
class VersionDiff:
    """Represents the diff between two versions."""
    entity_type: str
    entity_id: str
    from_version: int
    to_version: int
    changes: list[FieldChange]
    summary: str

    @property
    def has_changes(self) -> bool:
        return len(self.changes) > 0

    @property
    def changed_fields(self) -> list[str]:
        return [c.field_name for c in self.changes]

    def to_dict(self) -> dict:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "changes": [c.to_dict() for c in self.changes],
            "summary": self.summary,
            "has_changes": self.has_changes,
        }


@dataclass
class Version:
    """Represents a single version of an entity."""
    id: str
    version_number: int
    entity_type: str
    entity_id: str
    entity_label: str
    snapshot: dict[str, Any]
    changes: dict[str, Any]
    diff_summary: str
    revision_type: str
    trigger_event: str | None
    source_signal_id: str | None
    created_by: str | None
    created_at: datetime

    @classmethod
    def from_revision(cls, revision: dict) -> "Version":
        """Create Version from enrichment_revisions row."""
        created_at = revision.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        return cls(
            id=revision.get("id", ""),
            version_number=revision.get("revision_number", 0),
            entity_type=revision.get("entity_type", ""),
            entity_id=revision.get("entity_id", ""),
            entity_label=revision.get("entity_label", ""),
            snapshot=revision.get("snapshot", {}),
            changes=revision.get("changes", {}),
            diff_summary=revision.get("diff_summary") or revision.get("context_summary", ""),
            revision_type=revision.get("revision_type", ""),
            trigger_event=revision.get("trigger_event"),
            source_signal_id=revision.get("source_signal_id"),
            created_by=revision.get("created_by"),
            created_at=created_at,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "version_number": self.version_number,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "entity_label": self.entity_label,
            "snapshot": self.snapshot,
            "changes": self.changes,
            "diff_summary": self.diff_summary,
            "revision_type": self.revision_type,
            "trigger_event": self.trigger_event,
            "source_signal_id": self.source_signal_id,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


@dataclass
class FieldAttribution:
    """Tracks which signal contributed to a field value."""
    entity_type: str
    entity_id: str
    field_path: str
    signal_id: str
    signal_source: str | None
    contributed_at: datetime
    version_number: int


class EntityVersioning:
    """
    Service for entity version management.

    Provides a unified interface for:
    - Creating version snapshots
    - Retrieving version history
    - Comparing versions
    - Tracking field attributions
    """

    def __init__(self):
        self.supabase = get_supabase()

    # =========================================================================
    # Version History
    # =========================================================================

    def get_history(
        self,
        entity_type: str,
        entity_id: UUID | str,
        limit: int = 50,
    ) -> list[Version]:
        """
        Get version history for an entity.

        Args:
            entity_type: Type of entity (feature, persona, vp_step)
            entity_id: Entity UUID
            limit: Maximum versions to return

        Returns:
            List of Version objects, newest first
        """
        try:
            response = (
                self.supabase.table("enrichment_revisions")
                .select("*")
                .eq("entity_type", entity_type)
                .eq("entity_id", str(entity_id))
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

            return [Version.from_revision(r) for r in (response.data or [])]

        except Exception as e:
            logger.error(f"Failed to get history for {entity_type} {entity_id}: {e}")
            return []

    def get_version(
        self,
        entity_type: str,
        entity_id: UUID | str,
        version_number: int,
    ) -> Version | None:
        """
        Get a specific version of an entity.

        Args:
            entity_type: Type of entity
            entity_id: Entity UUID
            version_number: Version number to retrieve

        Returns:
            Version object or None if not found
        """
        try:
            response = (
                self.supabase.table("enrichment_revisions")
                .select("*")
                .eq("entity_type", entity_type)
                .eq("entity_id", str(entity_id))
                .eq("revision_number", version_number)
                .maybe_single()
                .execute()
            )

            if response.data:
                return Version.from_revision(response.data)
            return None

        except Exception as e:
            logger.error(f"Failed to get version {version_number} for {entity_type} {entity_id}: {e}")
            return None

    def get_latest_version(
        self,
        entity_type: str,
        entity_id: UUID | str,
    ) -> Version | None:
        """
        Get the most recent version of an entity.

        Args:
            entity_type: Type of entity
            entity_id: Entity UUID

        Returns:
            Latest Version object or None if no versions
        """
        history = self.get_history(entity_type, entity_id, limit=1)
        return history[0] if history else None

    def get_version_count(
        self,
        entity_type: str,
        entity_id: UUID | str,
    ) -> int:
        """Get total number of versions for an entity."""
        try:
            response = (
                self.supabase.table("enrichment_revisions")
                .select("id", count="exact")
                .eq("entity_type", entity_type)
                .eq("entity_id", str(entity_id))
                .execute()
            )
            return response.count or 0
        except Exception:
            return 0

    # =========================================================================
    # Version Creation
    # =========================================================================

    def create_snapshot(
        self,
        entity_type: str,
        entity_id: UUID | str,
        entity_data: dict[str, Any],
        entity_label: str | None = None,
        trigger_event: str = "manual_snapshot",
        source_signal_id: UUID | str | None = None,
        created_by: str = "system",
        changes: dict[str, Any] | None = None,
        diff_summary: str | None = None,
    ) -> str | None:
        """
        Create a version snapshot for an entity.

        Args:
            entity_type: Type of entity
            entity_id: Entity UUID
            entity_data: Current entity state to snapshot
            entity_label: Human-readable label (defaults to name/slug)
            trigger_event: What triggered this snapshot
            source_signal_id: Signal that triggered this change
            created_by: Who created this version
            changes: Pre-computed changes dict
            diff_summary: Pre-computed diff summary

        Returns:
            Version ID (revision UUID) or None if failed
        """
        try:
            # Determine label
            if not entity_label:
                entity_label = (
                    entity_data.get("name")
                    or entity_data.get("slug")
                    or entity_data.get("title")
                    or str(entity_id)
                )

            # Get next version number
            latest = self.get_latest_version(entity_type, entity_id)
            next_version = (latest.version_number + 1) if latest else 1

            # Get project_id from entity data
            project_id = entity_data.get("project_id", "")

            # Determine revision type
            revision_type = "created" if next_version == 1 else "updated"

            # Create revision record
            data = {
                "project_id": str(project_id),
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "entity_label": str(entity_label),
                "revision_type": revision_type,
                "revision_number": next_version,
                "trigger_event": trigger_event,
                "snapshot": entity_data,
                "changes": changes or {},
                "diff_summary": diff_summary or f"Version {next_version}",
                "context_summary": diff_summary or f"Version {next_version}",
                "source_signal_id": str(source_signal_id) if source_signal_id else None,
                "created_by": created_by,
            }

            response = self.supabase.table("enrichment_revisions").insert(data).execute()

            if response.data:
                version_id = response.data[0]["id"]
                logger.info(
                    f"Created version {next_version} for {entity_type} {entity_label}",
                    extra={
                        "entity_type": entity_type,
                        "entity_id": str(entity_id),
                        "version_number": next_version,
                    },
                )
                return version_id

            return None

        except Exception as e:
            logger.error(f"Failed to create snapshot for {entity_type} {entity_id}: {e}")
            return None

    # =========================================================================
    # Version Comparison
    # =========================================================================

    def compare_versions(
        self,
        entity_type: str,
        entity_id: UUID | str,
        from_version: int,
        to_version: int,
    ) -> VersionDiff | None:
        """
        Compare two versions of an entity.

        Args:
            entity_type: Type of entity
            entity_id: Entity UUID
            from_version: Earlier version number
            to_version: Later version number

        Returns:
            VersionDiff object or None if versions not found
        """
        version_a = self.get_version(entity_type, entity_id, from_version)
        version_b = self.get_version(entity_type, entity_id, to_version)

        if not version_a or not version_b:
            return None

        changes = self._compute_field_changes(
            version_a.snapshot,
            version_b.snapshot,
        )

        summary = self._generate_diff_summary(changes)

        return VersionDiff(
            entity_type=entity_type,
            entity_id=str(entity_id),
            from_version=from_version,
            to_version=to_version,
            changes=changes,
            summary=summary,
        )

    def compare_with_current(
        self,
        entity_type: str,
        entity_id: UUID | str,
        current_data: dict[str, Any],
        version_number: int | None = None,
    ) -> VersionDiff | None:
        """
        Compare a version with current entity state.

        Args:
            entity_type: Type of entity
            entity_id: Entity UUID
            current_data: Current entity state
            version_number: Version to compare against (default: latest)

        Returns:
            VersionDiff object or None
        """
        if version_number is None:
            version = self.get_latest_version(entity_type, entity_id)
        else:
            version = self.get_version(entity_type, entity_id, version_number)

        if not version:
            return None

        changes = self._compute_field_changes(
            version.snapshot,
            current_data,
        )

        return VersionDiff(
            entity_type=entity_type,
            entity_id=str(entity_id),
            from_version=version.version_number,
            to_version=version.version_number + 1,  # Represents "current"
            changes=changes,
            summary=self._generate_diff_summary(changes),
        )

    def _compute_field_changes(
        self,
        old_data: dict[str, Any],
        new_data: dict[str, Any],
    ) -> list[FieldChange]:
        """Compute field-level changes between two states."""
        changes = []
        all_fields = set(old_data.keys()) | set(new_data.keys())

        for field_name in all_fields:
            if field_name in METADATA_FIELDS:
                continue

            old_value = old_data.get(field_name)
            new_value = new_data.get(field_name)

            if old_value == new_value:
                continue

            # Determine change type
            if old_value is None:
                change_type = "added"
            elif new_value is None:
                change_type = "removed"
            else:
                change_type = "modified"

            # Truncate large values
            display_old = self._truncate_for_display(old_value, field_name)
            display_new = self._truncate_for_display(new_value, field_name)

            changes.append(FieldChange(
                field_name=field_name,
                old_value=display_old,
                new_value=display_new,
                change_type=change_type,
            ))

        return changes

    def _truncate_for_display(self, value: Any, field_name: str, max_length: int = 200) -> Any:
        """Truncate values for display in diffs."""
        if value is None:
            return None

        if field_name in LARGE_FIELDS:
            if value:
                return f"[{field_name} - {type(value).__name__}]"
            return None

        if isinstance(value, str) and len(value) > max_length:
            return value[:max_length] + "..."

        if isinstance(value, list):
            if len(value) > 5:
                return value[:5] + [f"... +{len(value) - 5} more"]
            return value

        if isinstance(value, dict) and len(str(value)) > max_length:
            return {"_summary": f"{len(value)} keys", "_keys": list(value.keys())[:5]}

        return value

    def _generate_diff_summary(self, changes: list[FieldChange]) -> str:
        """Generate human-readable summary of changes."""
        if not changes:
            return "No changes"

        added = [c.field_name for c in changes if c.change_type == "added"]
        removed = [c.field_name for c in changes if c.change_type == "removed"]
        modified = [c.field_name for c in changes if c.change_type == "modified"]

        parts = []
        if modified:
            if len(modified) <= 3:
                parts.append(f"Updated {', '.join(modified)}")
            else:
                parts.append(f"Updated {', '.join(modified[:2])} +{len(modified) - 2} more")

        if added:
            parts.append(f"Added {', '.join(added[:2])}" + (f" +{len(added) - 2}" if len(added) > 2 else ""))

        if removed:
            parts.append(f"Removed {', '.join(removed[:2])}" + (f" +{len(removed) - 2}" if len(removed) > 2 else ""))

        return "; ".join(parts) if parts else "Minor changes"

    # =========================================================================
    # Field Attribution
    # =========================================================================

    def record_field_attribution(
        self,
        entity_type: str,
        entity_id: UUID | str,
        field_path: str,
        signal_id: UUID | str,
        version_number: int | None = None,
    ) -> bool:
        """
        Record that a signal contributed to a field value.

        Args:
            entity_type: Type of entity
            entity_id: Entity UUID
            field_path: Path to field (e.g., "name", "acceptance_criteria[0]")
            signal_id: Signal UUID that contributed
            version_number: Version where this attribution applies

        Returns:
            True if recorded successfully
        """
        try:
            # Get current version if not specified
            if version_number is None:
                latest = self.get_latest_version(entity_type, entity_id)
                version_number = latest.version_number if latest else 1

            data = {
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "field_path": field_path,
                "signal_id": str(signal_id),
                "version_number": version_number,
            }

            self.supabase.table("field_attributions").insert(data).execute()

            logger.debug(
                f"Recorded attribution: {entity_type}/{entity_id}.{field_path} <- signal {signal_id}"
            )
            return True

        except Exception as e:
            logger.warning(f"Failed to record field attribution: {e}")
            return False

    def record_bulk_attributions(
        self,
        entity_type: str,
        entity_id: UUID | str,
        field_signal_map: dict[str, UUID | str],
        version_number: int | None = None,
    ) -> int:
        """
        Record multiple field attributions at once.

        Args:
            entity_type: Type of entity
            entity_id: Entity UUID
            field_signal_map: Dict of field_path -> signal_id
            version_number: Version where these attributions apply

        Returns:
            Number of attributions recorded
        """
        count = 0
        for field_path, signal_id in field_signal_map.items():
            if self.record_field_attribution(
                entity_type, entity_id, field_path, signal_id, version_number
            ):
                count += 1
        return count

    def get_field_sources(
        self,
        entity_type: str,
        entity_id: UUID | str,
        field_path: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get source attribution for entity fields.

        Args:
            entity_type: Type of entity
            entity_id: Entity UUID
            field_path: Specific field (None = all fields)

        Returns:
            List of attribution records with signal details
        """
        try:
            query = (
                self.supabase.table("field_attributions")
                .select("*, signals(id, source, source_type, title, created_at)")
                .eq("entity_type", entity_type)
                .eq("entity_id", str(entity_id))
            )

            if field_path:
                query = query.eq("field_path", field_path)

            response = query.order("contributed_at", desc=True).execute()

            return response.data or []

        except Exception as e:
            logger.error(f"Failed to get field sources for {entity_type} {entity_id}: {e}")
            return []

    def get_signal_contributions(
        self,
        signal_id: UUID | str,
    ) -> list[dict[str, Any]]:
        """
        Get all fields that a signal contributed to.

        Args:
            signal_id: Signal UUID

        Returns:
            List of attribution records
        """
        try:
            response = (
                self.supabase.table("field_attributions")
                .select("*")
                .eq("signal_id", str(signal_id))
                .order("contributed_at", desc=True)
                .execute()
            )

            return response.data or []

        except Exception as e:
            logger.error(f"Failed to get signal contributions for {signal_id}: {e}")
            return []

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_changes_by_signal(
        self,
        signal_id: UUID | str,
    ) -> list[Version]:
        """
        Get all versions that were triggered by a specific signal.

        Args:
            signal_id: Signal UUID

        Returns:
            List of Version objects
        """
        try:
            response = (
                self.supabase.table("enrichment_revisions")
                .select("*")
                .eq("source_signal_id", str(signal_id))
                .order("created_at", desc=True)
                .execute()
            )

            return [Version.from_revision(r) for r in (response.data or [])]

        except Exception as e:
            logger.error(f"Failed to get changes for signal {signal_id}: {e}")
            return []

    def get_recent_changes(
        self,
        project_id: UUID | str,
        entity_type: str | None = None,
        limit: int = 20,
    ) -> list[Version]:
        """
        Get recent changes across a project.

        Args:
            project_id: Project UUID
            entity_type: Filter by entity type (optional)
            limit: Maximum versions to return

        Returns:
            List of Version objects, newest first
        """
        try:
            query = (
                self.supabase.table("enrichment_revisions")
                .select("*")
                .eq("project_id", str(project_id))
            )

            if entity_type:
                query = query.eq("entity_type", entity_type)

            response = query.order("created_at", desc=True).limit(limit).execute()

            return [Version.from_revision(r) for r in (response.data or [])]

        except Exception as e:
            logger.error(f"Failed to get recent changes for project {project_id}: {e}")
            return []

    def restore_version(
        self,
        entity_type: str,
        entity_id: UUID | str,
        version_number: int,
    ) -> dict[str, Any] | None:
        """
        Get the snapshot data to restore an entity to a previous version.

        Note: This returns the data but doesn't actually update the entity.
        The caller is responsible for updating the entity with this data.

        Args:
            entity_type: Type of entity
            entity_id: Entity UUID
            version_number: Version to restore to

        Returns:
            Snapshot data or None if version not found
        """
        version = self.get_version(entity_type, entity_id, version_number)
        if version:
            return version.snapshot
        return None


# Convenience function for common use
def get_entity_history(
    entity_type: str,
    entity_id: UUID | str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Get version history for an entity as dicts.

    Convenience wrapper for API endpoints.
    """
    versioning = EntityVersioning()
    versions = versioning.get_history(entity_type, entity_id, limit)
    return [v.to_dict() for v in versions]


def track_entity_update(
    entity_type: str,
    entity_id: UUID | str,
    old_data: dict[str, Any],
    new_data: dict[str, Any],
    trigger_event: str,
    source_signal_id: UUID | str | None = None,
    created_by: str = "system",
) -> str | None:
    """
    Track an entity update with automatic diff computation.

    Convenience wrapper that computes diff and creates snapshot.
    """
    versioning = EntityVersioning()

    # Compute changes
    changes_list = versioning._compute_field_changes(old_data, new_data)

    if not changes_list:
        # No actual changes
        return None

    changes_dict = {c.field_name: {"old": c.old_value, "new": c.new_value} for c in changes_list}
    diff_summary = versioning._generate_diff_summary(changes_list)

    return versioning.create_snapshot(
        entity_type=entity_type,
        entity_id=entity_id,
        entity_data=new_data,
        trigger_event=trigger_event,
        source_signal_id=source_signal_id,
        created_by=created_by,
        changes=changes_dict,
        diff_summary=diff_summary,
    )
