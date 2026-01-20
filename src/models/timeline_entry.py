"""
TimelineEntry model for case activity history.

Timeline entries provide a human-readable view of case history,
separate from the technical audit log.

References:
- Principle I: Immutable Audit Trail (NON-NEGOTIABLE)
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, JSON
from src.models.base import DatabaseAgnosticUUID
from sqlalchemy.orm import Mapped, relationship

from src.models.base import Base, UUIDPrimaryKeyMixin


class TimelineEntryType(str, Enum):
    """Types of timeline entries."""

    # Case lifecycle
    CASE_CREATED = "CASE_CREATED"
    CASE_CLAIMED = "CASE_CLAIMED"
    CASE_UNASSIGNED = "CASE_UNASSIGNED"
    CASE_CLOSED = "CASE_CLOSED"
    CASE_REOPENED = "CASE_REOPENED"
    CASE_ESCALATED = "CASE_ESCALATED"

    # Status changes
    STATUS_CHANGED = "STATUS_CHANGED"
    TIER_CHANGED = "TIER_CHANGED"

    # Investigation
    INVESTIGATION_STARTED = "INVESTIGATION_STARTED"
    FINDINGS_DOCUMENTED = "FINDINGS_DOCUMENTED"

    # SMR workflow
    SMR_RECOMMENDED = "SMR_RECOMMENDED"
    SMR_APPROVED = "SMR_APPROVED"
    SMR_REJECTED = "SMR_REJECTED"
    SMR_RESUBMITTED = "SMR_RESUBMITTED"
    AUSTRAC_REFERENCE_RECORDED = "AUSTRAC_REFERENCE_RECORDED"

    # Customer communication
    INFORMATION_REQUESTED = "INFORMATION_REQUESTED"
    CUSTOMER_RESPONSE_RECORDED = "CUSTOMER_RESPONSE_RECORDED"

    # EDD
    EDD_CHECKLIST_COMPLETED = "EDD_CHECKLIST_COMPLETED"

    # Sanctions/Onboarding
    ONBOARDING_BLOCKED = "ONBOARDING_BLOCKED"
    ONBOARDING_UNBLOCKED = "ONBOARDING_UNBLOCKED"

    # L2 Review
    L2_REVIEW_ACCEPTED = "L2_REVIEW_ACCEPTED"
    L2_REVIEW_REJECTED = "L2_REVIEW_REJECTED"

    # Notes
    NOTE_ADDED = "NOTE_ADDED"

    # Documents
    DOCUMENT_ATTACHED = "DOCUMENT_ATTACHED"


class TimelineEntry(Base, UUIDPrimaryKeyMixin):
    """
    Human-readable timeline entry for case history.

    Each entry represents a significant event in the case lifecycle.
    Entries are immutable once created.
    """

    __tablename__ = "timeline_entries"

    # Case reference
    case_id: Mapped[UUID] = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("cases.id"),
        nullable=False,
        index=True
    )

    # Entry type
    entry_type: Mapped[str] = Column(
        String(50),
        nullable=False,
        index=True
    )

    # Content/description
    content: Mapped[str] = Column(Text, nullable=False)

    # User who performed the action (null for system/webhook events)
    acting_user_id: Mapped[Optional[UUID]] = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("users.id"),
        nullable=True
    )

    # Timestamp (immutable)
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )

    # Optional metadata for additional context
    entry_metadata: Mapped[Optional[dict]] = Column(
        JSON,
        nullable=True,
        default=None
    )

    def __repr__(self) -> str:
        return f"<TimelineEntry {self.entry_type} case={self.case_id}>"

    @classmethod
    def create(
        cls,
        case_id: UUID,
        entry_type: TimelineEntryType | str,
        content: str,
        acting_user_id: Optional[UUID] = None,
        metadata: Optional[dict] = None
    ) -> "TimelineEntry":
        """
        Create a new timeline entry.

        Args:
            case_id: Case this entry belongs to
            entry_type: Type of timeline event
            content: Human-readable description
            acting_user_id: User who triggered the event
            metadata: Optional additional metadata

        Returns:
            New TimelineEntry instance
        """
        type_str = entry_type.value if isinstance(entry_type, TimelineEntryType) else entry_type

        return cls(
            case_id=case_id,
            entry_type=type_str,
            content=content,
            acting_user_id=acting_user_id,
            entry_metadata=metadata,
        )

    @classmethod
    def for_case_creation(
        cls,
        case_id: UUID,
        case_reference: str,
        case_type: str
    ) -> "TimelineEntry":
        """Create timeline entry for case creation."""
        return cls.create(
            case_id=case_id,
            entry_type=TimelineEntryType.CASE_CREATED,
            content=f"Case {case_reference} created for {case_type.replace('_', ' ').title()}"
        )

    @classmethod
    def for_case_claim(
        cls,
        case_id: UUID,
        user_id: UUID,
        user_email: str
    ) -> "TimelineEntry":
        """Create timeline entry for case claim."""
        return cls.create(
            case_id=case_id,
            entry_type=TimelineEntryType.CASE_CLAIMED,
            content=f"Case claimed by {user_email}",
            acting_user_id=user_id
        )

    @classmethod
    def for_case_closure(
        cls,
        case_id: UUID,
        user_id: UUID,
        reason: str
    ) -> "TimelineEntry":
        """Create timeline entry for case closure."""
        return cls.create(
            case_id=case_id,
            entry_type=TimelineEntryType.CASE_CLOSED,
            content=f"Case closed: {reason}",
            acting_user_id=user_id
        )

    @classmethod
    def for_escalation(
        cls,
        case_id: UUID,
        user_id: UUID,
        reason: str
    ) -> "TimelineEntry":
        """Create timeline entry for escalation."""
        return cls.create(
            case_id=case_id,
            entry_type=TimelineEntryType.CASE_ESCALATED,
            content=f"Case escalated to L2: {reason}",
            acting_user_id=user_id
        )

    @classmethod
    def for_smr_recommendation(
        cls,
        case_id: UUID,
        user_id: UUID
    ) -> "TimelineEntry":
        """Create timeline entry for SMR recommendation."""
        return cls.create(
            case_id=case_id,
            entry_type=TimelineEntryType.SMR_RECOMMENDED,
            content="SMR recommendation submitted for approval",
            acting_user_id=user_id
        )
