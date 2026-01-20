"""
Notification model for user notifications.

References:
- FR-066: SLA breach notifications
- FR-067: Escalation notifications
- FR-068: SMR submission notifications
- FR-069: Notification retrieval
- D6: Celery async tasks + email provider
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from src.models.base import DatabaseAgnosticUUID
from sqlalchemy.orm import Mapped, relationship

from src.models.base import Base, UUIDPrimaryKeyMixin


class NotificationType(str, Enum):
    """Types of notifications."""

    # SLA related (FR-066)
    SLA_WARNING = "SLA_WARNING"
    SLA_BREACH = "SLA_BREACH"

    # Escalation (FR-067)
    CASE_ESCALATED = "CASE_ESCALATED"

    # SMR workflow (FR-068)
    SMR_SUBMITTED = "SMR_SUBMITTED"
    SMR_APPROVED = "SMR_APPROVED"
    SMR_REJECTED = "SMR_REJECTED"

    # Assignment
    CASE_ASSIGNED = "CASE_ASSIGNED"
    CASE_UNASSIGNED = "CASE_UNASSIGNED"

    # L2 Review
    L2_REVIEW_REQUIRED = "L2_REVIEW_REQUIRED"
    L2_REVIEW_COMPLETE = "L2_REVIEW_COMPLETE"

    # General
    CASE_REOPENED = "CASE_REOPENED"
    INFORMATION_RECEIVED = "INFORMATION_RECEIVED"
    INFO = "INFO"  # General informational notifications (e.g., linked cases)


class Notification(Base, UUIDPrimaryKeyMixin):
    """
    User notification entity.

    Notifications are created asynchronously via Celery tasks
    and can be delivered via in-app notification and/or email.
    """

    __tablename__ = "notifications"

    # Target user
    user_id: Mapped[UUID] = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    # Notification type
    notification_type: Mapped[str] = Column(
        String(50),
        nullable=False,
        index=True
    )

    # Message content
    title: Mapped[str] = Column(String(255), nullable=False)
    message: Mapped[str] = Column(Text, nullable=False)

    # Related case (optional)
    case_id: Mapped[Optional[UUID]] = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("cases.id"),
        nullable=True,
        index=True
    )

    # Read status
    is_read: Mapped[bool] = Column(Boolean, nullable=False, default=False)
    read_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True), nullable=True)

    # Email delivery status
    email_sent: Mapped[bool] = Column(Boolean, nullable=False, default=False)
    email_sent_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Notification {self.notification_type} user={self.user_id}>"

    def mark_as_read(self) -> None:
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()

    def mark_email_sent(self) -> None:
        """Mark email as sent."""
        self.email_sent = True
        self.email_sent_at = datetime.utcnow()

    @classmethod
    def create(
        cls,
        user_id: UUID,
        notification_type: NotificationType | str,
        title: str,
        message: str,
        case_id: Optional[UUID] = None
    ) -> "Notification":
        """
        Create a new notification.

        Args:
            user_id: Target user
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            case_id: Related case ID

        Returns:
            New Notification instance
        """
        type_str = notification_type.value if isinstance(notification_type, NotificationType) else notification_type

        return cls(
            user_id=user_id,
            notification_type=type_str,
            title=title,
            message=message,
            case_id=case_id,
        )

    @classmethod
    def for_sla_warning(
        cls,
        user_id: UUID,
        case_id: UUID,
        case_reference: str,
        hours_remaining: int
    ) -> "Notification":
        """Create SLA warning notification."""
        return cls.create(
            user_id=user_id,
            notification_type=NotificationType.SLA_WARNING,
            title=f"SLA Warning: {case_reference}",
            message=f"Case {case_reference} has {hours_remaining} hours remaining until SLA deadline.",
            case_id=case_id
        )

    @classmethod
    def for_sla_breach(
        cls,
        user_id: UUID,
        case_id: UUID,
        case_reference: str
    ) -> "Notification":
        """Create SLA breach notification."""
        return cls.create(
            user_id=user_id,
            notification_type=NotificationType.SLA_BREACH,
            title=f"SLA Breach: {case_reference}",
            message=f"Case {case_reference} has breached its SLA deadline.",
            case_id=case_id
        )

    @classmethod
    def for_escalation(
        cls,
        user_id: UUID,
        case_id: UUID,
        case_reference: str
    ) -> "Notification":
        """Create escalation notification for L2 queue."""
        return cls.create(
            user_id=user_id,
            notification_type=NotificationType.CASE_ESCALATED,
            title=f"Case Escalated: {case_reference}",
            message=f"Case {case_reference} has been escalated to L2 for investigation.",
            case_id=case_id
        )

    @classmethod
    def for_smr_submission(
        cls,
        manager_id: UUID,
        case_id: UUID,
        case_reference: str
    ) -> "Notification":
        """Create SMR submission notification for manager."""
        return cls.create(
            user_id=manager_id,
            notification_type=NotificationType.SMR_SUBMITTED,
            title=f"SMR Pending Approval: {case_reference}",
            message=f"SMR recommendation for case {case_reference} requires your approval.",
            case_id=case_id
        )
