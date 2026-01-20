"""
AuditLog model for immutable action logging.

References:
- D1: Append-only log with event sourcing
- FR-058: All case actions logged immutably
- FR-060: User attribution on all entries
- FR-061: 7-year retention
- Principle I: Immutable Audit Trail (NON-NEGOTIABLE)
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from src.models.base import DatabaseAgnosticUUID
from sqlalchemy.orm import Mapped

from src.models.base import Base, UUIDPrimaryKeyMixin


class AuditActionType(str, Enum):
    """Types of auditable actions."""

    # Case lifecycle
    CASE_CREATED = "CASE_CREATED"
    CASE_VIEWED = "CASE_VIEWED"
    CASE_CLAIMED = "CASE_CLAIMED"
    CASE_UNASSIGNED = "CASE_UNASSIGNED"
    CASE_CLOSED = "CASE_CLOSED"
    CASE_REOPENED = "CASE_REOPENED"
    CASE_ESCALATED = "CASE_ESCALATED"

    # Investigation
    INVESTIGATION_FINDINGS_ADDED = "INVESTIGATION_FINDINGS_ADDED"
    INVESTIGATION_FINDINGS_UPDATED = "INVESTIGATION_FINDINGS_UPDATED"

    # SMR workflow
    SMR_RECOMMENDED = "SMR_RECOMMENDED"
    SMR_APPROVED = "SMR_APPROVED"
    SMR_REJECTED = "SMR_REJECTED"
    SMR_RESUBMITTED = "SMR_RESUBMITTED"
    SMR_REFERENCE_RECORDED = "SMR_REFERENCE_RECORDED"

    # Customer communication
    INFORMATION_REQUESTED = "INFORMATION_REQUESTED"
    RESPONSE_RECORDED = "RESPONSE_RECORDED"

    # EDD
    EDD_CHECKLIST_UPDATED = "EDD_CHECKLIST_UPDATED"

    # Sanctions/Onboarding
    ONBOARDING_BLOCK_CREATED = "ONBOARDING_BLOCK_CREATED"
    ONBOARDING_BLOCK_CLEARED = "ONBOARDING_BLOCK_CLEARED"

    # User management
    USER_ROLE_CHANGED = "USER_ROLE_CHANGED"

    # L2 Review
    L2_REVIEW_ACCEPTED = "L2_REVIEW_ACCEPTED"
    L2_REVIEW_REOPENED = "L2_REVIEW_REOPENED"


class AuditLog(Base, UUIDPrimaryKeyMixin):
    """
    Immutable audit log entry.

    This model enforces append-only semantics at the database level
    via triggers that prevent UPDATE and DELETE operations.

    All entries include:
    - Action type identifying what happened
    - User who performed the action (null for system actions)
    - Case reference (if applicable)
    - Redacted payload with PII removed
    - Timestamp
    """

    __tablename__ = "audit_logs"

    # Action type
    action_type: Mapped[str] = Column(
        String(50),
        nullable=False,
        index=True
    )

    # Action detail/description
    action_detail: Mapped[Optional[str]] = Column(Text, nullable=True)

    # User who performed the action (null for webhook/system actions)
    user_id: Mapped[Optional[UUID]] = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("users.id"),
        nullable=True,
        index=True
    )

    # Case reference (if applicable)
    case_id: Mapped[Optional[UUID]] = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("cases.id"),
        nullable=True,
        index=True
    )

    # Redacted payload (PII fields masked)
    payload: Mapped[Optional[dict]] = Column(JSONB, nullable=True)

    # Client information for forensics
    ip_address: Mapped[Optional[str]] = Column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = Column(String(500), nullable=True)

    # Timestamp (immutable, set once on creation)
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action_type} user={self.user_id} case={self.case_id}>"

    @classmethod
    def create(
        cls,
        action_type: AuditActionType | str,
        user_id: Optional[UUID] = None,
        case_id: Optional[UUID] = None,
        action_detail: Optional[str] = None,
        payload: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> "AuditLog":
        """
        Create a new audit log entry.

        Note: Payload should already have PII redacted before passing here.

        Args:
            action_type: Type of action being logged
            user_id: User performing the action (None for system)
            case_id: Related case ID (if applicable)
            action_detail: Human-readable description
            payload: Redacted payload data
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            New AuditLog instance
        """
        action_str = action_type.value if isinstance(action_type, AuditActionType) else action_type

        return cls(
            action_type=action_str,
            user_id=user_id,
            case_id=case_id,
            action_detail=action_detail,
            payload=payload,
            ip_address=ip_address,
            user_agent=user_agent,
        )
