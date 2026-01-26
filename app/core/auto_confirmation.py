"""
Auto-Confirmation Service.

Handles automatic confirmation of entities based on signal authority.

Rules:
- Client signals → confirmed_client
- Consultant signals → confirmed_consultant
- AI-generated → ai_generated (needs review)
- External research → needs_confirmation

Also handles automatic enrichment triggering when entities become confirmed.

Usage:
    from app.core.auto_confirmation import AutoConfirmation

    auto_confirm = AutoConfirmation()

    # Check if signal should auto-confirm entities
    status = auto_confirm.get_confirmation_status(authority="client")

    # Process confirmation change
    auto_confirm.on_entity_confirmed(entity_type, entity_id)
"""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from app.core.logging import get_logger
from app.db.supabase_client import get_supabase

logger = get_logger(__name__)


# Authority levels and their resulting confirmation status
AUTHORITY_STATUS_MAP = {
    "client": "confirmed_client",
    "consultant": "confirmed_consultant",
    "system": "ai_generated",
    "ai": "ai_generated",
    "research": "needs_confirmation",
    "external": "needs_confirmation",
    "unknown": "ai_generated",
}

# Confirmation statuses that count as "confirmed"
CONFIRMED_STATUSES = {"confirmed_client", "confirmed_consultant"}

# Confirmation statuses that should trigger enrichment
ENRICHMENT_TRIGGER_STATUSES = {"confirmed_client", "confirmed_consultant"}


ConfirmationStatus = Literal[
    "ai_generated",
    "confirmed_client",
    "confirmed_consultant",
    "needs_confirmation",
    "needs_client",
]


@dataclass
class ConfirmationResult:
    """Result of a confirmation operation."""
    entity_type: str
    entity_id: str
    old_status: str
    new_status: str
    triggered_enrichment: bool = False
    triggered_cascade: bool = False


class AutoConfirmation:
    """
    Service for automatic entity confirmation based on signal authority.
    """

    def __init__(self):
        self.supabase = get_supabase()

    def get_confirmation_status(self, authority: str) -> ConfirmationStatus:
        """
        Get the confirmation status that should be applied based on signal authority.

        Args:
            authority: Signal authority (client, consultant, system, etc.)

        Returns:
            Confirmation status to apply
        """
        return AUTHORITY_STATUS_MAP.get(authority.lower(), "ai_generated")

    def should_auto_confirm(self, authority: str) -> bool:
        """
        Check if entities from this authority should be auto-confirmed.

        Args:
            authority: Signal authority

        Returns:
            True if should auto-confirm
        """
        status = self.get_confirmation_status(authority)
        return status in CONFIRMED_STATUSES

    def should_trigger_enrichment(self, status: str) -> bool:
        """
        Check if a confirmation status should trigger enrichment.

        Args:
            status: Confirmation status

        Returns:
            True if should trigger enrichment
        """
        return status in ENRICHMENT_TRIGGER_STATUSES

    def confirm_entity(
        self,
        entity_type: str,
        entity_id: UUID | str,
        status: ConfirmationStatus,
        confirmed_by: UUID | str | None = None,
    ) -> ConfirmationResult:
        """
        Update entity confirmation status.

        Args:
            entity_type: Type of entity (feature, persona, vp_step)
            entity_id: Entity UUID
            status: New confirmation status
            confirmed_by: User who confirmed (optional)

        Returns:
            ConfirmationResult with operation details
        """
        from datetime import datetime, timezone

        entity_id_str = str(entity_id)
        table_name = _get_table_name(entity_type)

        # Get current status
        response = (
            self.supabase.table(table_name)
            .select("confirmation_status")
            .eq("id", entity_id_str)
            .single()
            .execute()
        )

        if not response.data:
            raise ValueError(f"{entity_type} {entity_id} not found")

        old_status = response.data.get("confirmation_status", "ai_generated")

        # Skip if already at this status
        if old_status == status:
            return ConfirmationResult(
                entity_type=entity_type,
                entity_id=entity_id_str,
                old_status=old_status,
                new_status=status,
            )

        # Update status
        update_data = {
            "confirmation_status": status,
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
        }
        if confirmed_by:
            update_data["confirmed_by"] = str(confirmed_by)

        self.supabase.table(table_name).update(update_data).eq("id", entity_id_str).execute()

        logger.info(
            f"Confirmed {entity_type} {entity_id}: {old_status} → {status}",
            extra={"entity_type": entity_type, "entity_id": entity_id_str},
        )

        # Check if we should trigger enrichment
        triggered_enrichment = False
        if self.should_trigger_enrichment(status) and not self.should_trigger_enrichment(old_status):
            triggered_enrichment = self._queue_enrichment(entity_type, entity_id_str)

        return ConfirmationResult(
            entity_type=entity_type,
            entity_id=entity_id_str,
            old_status=old_status,
            new_status=status,
            triggered_enrichment=triggered_enrichment,
        )

    def bulk_confirm(
        self,
        entity_type: str,
        entity_ids: list[UUID | str],
        status: ConfirmationStatus,
        confirmed_by: UUID | str | None = None,
    ) -> list[ConfirmationResult]:
        """
        Confirm multiple entities at once.

        Args:
            entity_type: Type of entities
            entity_ids: List of entity UUIDs
            status: New confirmation status
            confirmed_by: User who confirmed

        Returns:
            List of ConfirmationResult for each entity
        """
        results = []
        for entity_id in entity_ids:
            try:
                result = self.confirm_entity(entity_type, entity_id, status, confirmed_by)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to confirm {entity_type} {entity_id}: {e}")
                results.append(ConfirmationResult(
                    entity_type=entity_type,
                    entity_id=str(entity_id),
                    old_status="unknown",
                    new_status=status,
                ))
        return results

    def on_entity_confirmed(
        self,
        entity_type: str,
        entity_id: UUID | str,
    ) -> dict:
        """
        Handle post-confirmation actions.

        Called when an entity transitions to a confirmed status.
        Triggers enrichment queue and any cascades.

        Args:
            entity_type: Type of entity
            entity_id: Entity UUID

        Returns:
            Dict with actions taken
        """
        entity_id_str = str(entity_id)
        actions = {
            "enrichment_queued": False,
            "cascade_triggered": False,
        }

        # Queue for enrichment
        actions["enrichment_queued"] = self._queue_enrichment(entity_type, entity_id_str)

        # Trigger cascade to update dependent entities
        actions["cascade_triggered"] = self._trigger_cascade(entity_type, entity_id_str)

        return actions

    def _queue_enrichment(self, entity_type: str, entity_id: str) -> bool:
        """Queue entity for enrichment."""
        try:
            # Get project_id from entity
            table_name = _get_table_name(entity_type)
            response = (
                self.supabase.table(table_name)
                .select("project_id")
                .eq("id", entity_id)
                .single()
                .execute()
            )

            if not response.data:
                return False

            project_id = response.data["project_id"]

            # Insert into enrichment queue
            self.supabase.table("enrichment_queue").insert({
                "project_id": project_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "status": "pending",
                "priority": 5,
            }).execute()

            logger.info(f"Queued {entity_type} {entity_id} for enrichment")
            return True

        except Exception as e:
            # Table might not exist yet
            logger.debug(f"Could not queue enrichment: {e}")
            return False

    def _trigger_cascade(self, entity_type: str, entity_id: str) -> bool:
        """Trigger cascade to update dependent entities."""
        try:
            # For now, just log that we would cascade
            # Full cascade implementation is in dependency_manager
            logger.debug(f"Would trigger cascade for {entity_type} {entity_id}")
            return False
        except Exception:
            return False


def _get_table_name(entity_type: str) -> str:
    """Get database table name for entity type."""
    table_map = {
        "feature": "features",
        "persona": "personas",
        "vp_step": "vp_steps",
    }
    return table_map.get(entity_type, f"{entity_type}s")


# Convenience functions

def get_confirmation_status_for_authority(authority: str) -> ConfirmationStatus:
    """Get confirmation status for a signal authority."""
    return AutoConfirmation().get_confirmation_status(authority)


def auto_confirm_from_signal(
    entity_type: str,
    entity_id: UUID | str,
    signal_authority: str,
) -> ConfirmationResult | None:
    """
    Auto-confirm an entity if the signal authority allows it.

    Args:
        entity_type: Type of entity
        entity_id: Entity UUID
        signal_authority: Authority of the source signal

    Returns:
        ConfirmationResult if confirmed, None if not auto-confirmable
    """
    service = AutoConfirmation()

    if not service.should_auto_confirm(signal_authority):
        return None

    status = service.get_confirmation_status(signal_authority)
    return service.confirm_entity(entity_type, entity_id, status)
