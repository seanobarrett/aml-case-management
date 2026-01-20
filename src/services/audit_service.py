"""
Audit service for logging all case operations.

References:
- D1: Append-only log with event sourcing
- D12: PII redaction before logging
- FR-058: All case actions logged immutably
- FR-059: Case view events logged
- FR-060: User attribution
- Principle I: Immutable Audit Trail (NON-NEGOTIABLE)
"""

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.audit_log import AuditLog, AuditActionType
from src.models.timeline_entry import TimelineEntry, TimelineEntryType
from src.services.pii_redaction import redact_pii


class AuditService:
    """Service for creating immutable audit log entries."""

    def __init__(self, db: Session):
        self.db = db

    def log_action(
        self,
        action_type: AuditActionType | str,
        user_id: Optional[UUID] = None,
        case_id: Optional[UUID] = None,
        action_detail: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """
        Log an action to the audit log.

        Automatically redacts PII from the payload before storing.

        Args:
            action_type: Type of action
            user_id: User performing the action
            case_id: Related case ID
            action_detail: Human-readable description
            payload: Action payload (will be redacted)
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Created AuditLog entry
        """
        # Redact PII from payload
        redacted_payload = redact_pii(payload) if payload else None

        # Create audit log entry
        audit_entry = AuditLog.create(
            action_type=action_type,
            user_id=user_id,
            case_id=case_id,
            action_detail=action_detail,
            payload=redacted_payload,
            ip_address=ip_address,
            user_agent=user_agent
        )

        self.db.add(audit_entry)
        self.db.flush()

        return audit_entry

    def log_case_created(
        self,
        case_id: UUID,
        case_reference: str,
        case_type: str,
        webhook_payload: dict[str, Any],
        ip_address: Optional[str] = None
    ) -> tuple[AuditLog, TimelineEntry]:
        """
        Log case creation event.

        Args:
            case_id: ID of created case
            case_reference: Case reference number
            case_type: Type of case
            webhook_payload: Original webhook payload
            ip_address: Source IP address

        Returns:
            Tuple of (AuditLog, TimelineEntry)
        """
        # Audit log
        audit = self.log_action(
            action_type=AuditActionType.CASE_CREATED,
            case_id=case_id,
            action_detail=f"Case {case_reference} created from webhook",
            payload=webhook_payload,
            ip_address=ip_address
        )

        # Timeline entry
        timeline = TimelineEntry.for_case_creation(
            case_id=case_id,
            case_reference=case_reference,
            case_type=case_type
        )
        self.db.add(timeline)
        self.db.flush()

        return audit, timeline

    def log_case_viewed(
        self,
        case_id: UUID,
        user_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AuditLog:
        """
        Log case view event (FR-059).

        Args:
            case_id: Viewed case ID
            user_id: User who viewed
            ip_address: Client IP
            user_agent: Client user agent

        Returns:
            AuditLog entry
        """
        return self.log_action(
            action_type=AuditActionType.CASE_VIEWED,
            user_id=user_id,
            case_id=case_id,
            action_detail="Case viewed",
            ip_address=ip_address,
            user_agent=user_agent
        )

    def log_case_claimed(
        self,
        case_id: UUID,
        user_id: UUID,
        user_email: str,
        ip_address: Optional[str] = None
    ) -> tuple[AuditLog, TimelineEntry]:
        """
        Log case claim event.

        Args:
            case_id: Claimed case ID
            user_id: User claiming
            user_email: User's email
            ip_address: Client IP

        Returns:
            Tuple of (AuditLog, TimelineEntry)
        """
        audit = self.log_action(
            action_type=AuditActionType.CASE_CLAIMED,
            user_id=user_id,
            case_id=case_id,
            action_detail=f"Case claimed by {user_email}",
            ip_address=ip_address
        )

        timeline = TimelineEntry.for_case_claim(
            case_id=case_id,
            user_id=user_id,
            user_email=user_email
        )
        self.db.add(timeline)
        self.db.flush()

        return audit, timeline

    def log_case_closed(
        self,
        case_id: UUID,
        user_id: UUID,
        reason: str,
        documentation: str,
        ip_address: Optional[str] = None
    ) -> tuple[AuditLog, TimelineEntry]:
        """
        Log case closure event.

        Args:
            case_id: Closed case ID
            user_id: User closing
            reason: Closure reason
            documentation: Supporting documentation
            ip_address: Client IP

        Returns:
            Tuple of (AuditLog, TimelineEntry)
        """
        audit = self.log_action(
            action_type=AuditActionType.CASE_CLOSED,
            user_id=user_id,
            case_id=case_id,
            action_detail=f"Case closed: {reason}",
            payload={
                "reason": reason,
                "documentation": documentation
            },
            ip_address=ip_address
        )

        timeline = TimelineEntry.for_case_closure(
            case_id=case_id,
            user_id=user_id,
            reason=reason
        )
        self.db.add(timeline)
        self.db.flush()

        return audit, timeline

    def log_case_escalated(
        self,
        case_id: UUID,
        user_id: UUID,
        reason: str,
        ip_address: Optional[str] = None
    ) -> tuple[AuditLog, TimelineEntry]:
        """
        Log case escalation event.

        Args:
            case_id: Escalated case ID
            user_id: User escalating
            reason: Escalation reason
            ip_address: Client IP

        Returns:
            Tuple of (AuditLog, TimelineEntry)
        """
        audit = self.log_action(
            action_type=AuditActionType.CASE_ESCALATED,
            user_id=user_id,
            case_id=case_id,
            action_detail=f"Case escalated to L2: {reason}",
            payload={"reason": reason},
            ip_address=ip_address
        )

        timeline = TimelineEntry.for_escalation(
            case_id=case_id,
            user_id=user_id,
            reason=reason
        )
        self.db.add(timeline)
        self.db.flush()

        return audit, timeline

    def log_user_role_changed(
        self,
        target_user_id: UUID,
        acting_user_id: UUID,
        old_role: str,
        new_role: str,
        affected_case_ids: list[UUID],
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """
        Log user role change event (FR-027).

        Creates audit entries for the role change and each affected case.

        Args:
            target_user_id: User whose role changed
            acting_user_id: Admin who made the change
            old_role: Previous role
            new_role: New role
            affected_case_ids: Cases that were unassigned
            ip_address: Client IP

        Returns:
            Primary AuditLog entry
        """
        # Log the role change
        audit = self.log_action(
            action_type=AuditActionType.USER_ROLE_CHANGED,
            user_id=acting_user_id,
            action_detail=f"User role changed from {old_role} to {new_role}",
            payload={
                "target_user_id": str(target_user_id),
                "old_role": old_role,
                "new_role": new_role,
                "affected_cases_count": len(affected_case_ids)
            },
            ip_address=ip_address
        )

        # Log unassignment for each affected case
        for case_id in affected_case_ids:
            self.log_action(
                action_type=AuditActionType.CASE_UNASSIGNED,
                user_id=acting_user_id,
                case_id=case_id,
                action_detail=f"Case unassigned due to role change ({old_role} -> {new_role})",
                payload={
                    "reason": "ROLE_CHANGE",
                    "previous_assignee": str(target_user_id)
                },
                ip_address=ip_address
            )

        return audit

    def log_case_reassigned(
        self,
        case_id: UUID,
        old_assignee_id: UUID,
        reason: str,
        changed_by_id: UUID,
        ip_address: Optional[str] = None
    ) -> tuple[AuditLog, TimelineEntry]:
        """
        Log case reassignment event (FR-027).

        Args:
            case_id: Reassigned case ID
            old_assignee_id: Previous assignee
            reason: Reason for reassignment
            changed_by_id: User who triggered the reassignment
            ip_address: Client IP

        Returns:
            Tuple of (AuditLog, TimelineEntry)
        """
        audit = self.log_action(
            action_type=AuditActionType.CASE_UNASSIGNED,
            user_id=changed_by_id,
            case_id=case_id,
            action_detail=f"Case unassigned: {reason}",
            payload={
                "reason": "ROLE_CHANGE",
                "previous_assignee": str(old_assignee_id),
                "reassignment_reason": reason
            },
            ip_address=ip_address
        )

        timeline = TimelineEntry(
            case_id=case_id,
            acting_user_id=changed_by_id,
            entry_type=TimelineEntryType.STATUS_CHANGED.value,
            content=f"Case returned to queue: {reason}"
        )
        self.db.add(timeline)
        self.db.flush()

        return audit, timeline

    def get_case_timeline(self, case_id: UUID) -> list[TimelineEntry]:
        """
        Get timeline entries for a case.

        Args:
            case_id: Case ID

        Returns:
            List of timeline entries, newest first
        """
        return (
            self.db.query(TimelineEntry)
            .filter(TimelineEntry.case_id == case_id)
            .order_by(TimelineEntry.created_at.desc())
            .all()
        )

    def get_case_audit_log(self, case_id: UUID) -> list[AuditLog]:
        """
        Get audit log entries for a case.

        Args:
            case_id: Case ID

        Returns:
            List of audit entries, newest first
        """
        return (
            self.db.query(AuditLog)
            .filter(AuditLog.case_id == case_id)
            .order_by(AuditLog.created_at.desc())
            .all()
        )
