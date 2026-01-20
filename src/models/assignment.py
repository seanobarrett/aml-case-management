"""
Assignment model for case-analyst assignments.

Tracks the full history of case assignments for audit purposes.

References:
- D13: Manual claim from queue - cases enter unassigned queue; analysts self-select
- FR-026: Role change triggers case reassignment
- FR-027: Audit entry created for each affected case
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Enum as SQLEnum
from src.models.base import DatabaseAgnosticUUID
from sqlalchemy.orm import Mapped, relationship

from src.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.case import Case
    from src.models.user import User


class AssignmentReason(str, Enum):
    """Reason for case assignment."""

    MANUAL_CLAIM = "MANUAL_CLAIM"
    ESCALATION = "ESCALATION"
    REOPEN = "REOPEN"
    ROLE_CHANGE = "ROLE_CHANGE"
    ADMIN_REASSIGN = "ADMIN_REASSIGN"


class Assignment(Base, UUIDPrimaryKeyMixin):
    """
    Case assignment record.

    Tracks when a case is assigned to or unassigned from an analyst.
    Multiple assignments per case create a complete assignment history.
    """

    __tablename__ = "assignments"

    # Case reference
    case_id: Mapped[UUID] = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("cases.id"),
        nullable=False,
        index=True
    )
    case: Mapped["Case"] = relationship("Case", back_populates="assignments")

    # Analyst reference
    user_id: Mapped[UUID] = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    user: Mapped["User"] = relationship("User", back_populates="assignments")

    # Assignment reason
    reason: Mapped[AssignmentReason] = Column(
        SQLEnum(AssignmentReason, name="assignment_reason", create_type=False),
        nullable=False
    )

    # Timestamps
    assigned_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    unassigned_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True),
        nullable=True
    )

    # Active flag (only one active assignment per case)
    is_active: Mapped[bool] = Column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        status = "active" if self.is_active else "inactive"
        return f"<Assignment case={self.case_id} user={self.user_id} [{status}]>"

    def unassign(self) -> None:
        """Mark this assignment as inactive."""
        self.is_active = False
        self.unassigned_at = datetime.utcnow()

    @property
    def duration_seconds(self) -> Optional[float]:
        """
        Get duration of this assignment in seconds.

        Returns:
            Duration in seconds, or None if still active
        """
        if self.unassigned_at is None:
            return None
        return (self.unassigned_at - self.assigned_at).total_seconds()

    @classmethod
    def create_claim(cls, case_id: UUID, user_id: UUID) -> "Assignment":
        """
        Create a new manual claim assignment.

        Args:
            case_id: Case being claimed
            user_id: User claiming the case

        Returns:
            New Assignment instance
        """
        return cls(
            case_id=case_id,
            user_id=user_id,
            reason=AssignmentReason.MANUAL_CLAIM,
            is_active=True,
        )

    @classmethod
    def create_escalation(cls, case_id: UUID, user_id: UUID) -> "Assignment":
        """
        Create an escalation assignment.

        Args:
            case_id: Case being escalated
            user_id: L2 analyst receiving the case

        Returns:
            New Assignment instance
        """
        return cls(
            case_id=case_id,
            user_id=user_id,
            reason=AssignmentReason.ESCALATION,
            is_active=True,
        )

    @classmethod
    def create_reopen(cls, case_id: UUID, user_id: UUID) -> "Assignment":
        """
        Create a reopen assignment.

        Args:
            case_id: Case being reopened
            user_id: Analyst receiving the reopened case

        Returns:
            New Assignment instance
        """
        return cls(
            case_id=case_id,
            user_id=user_id,
            reason=AssignmentReason.REOPEN,
            is_active=True,
        )
