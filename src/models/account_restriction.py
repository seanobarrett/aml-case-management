"""
Account restriction recommendation model for existing customer sanctions.

References:
- FR-038: Account restriction recommendation capability
- US-17: Existing customer sanctions screening
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, String, Text, Boolean
from src.models.base import DatabaseAgnosticUUID
from sqlalchemy.orm import Mapped, relationship

from src.models.base import Base


class RestrictionType(str, Enum):
    """Types of account restriction."""
    FULL = "FULL"  # Complete account freeze
    PARTIAL = "PARTIAL"  # Limited functionality
    ENHANCED_MONITORING = "ENHANCED_MONITORING"  # No restrictions, but increased monitoring
    NONE = "NONE"  # No restriction recommended


class RestrictionStatus(str, Enum):
    """Status of restriction recommendation."""
    RECOMMENDED = "RECOMMENDED"  # Analyst has recommended
    APPROVED = "APPROVED"  # Manager has approved
    REJECTED = "REJECTED"  # Manager has rejected
    IMPLEMENTED = "IMPLEMENTED"  # Restriction is in place
    LIFTED = "LIFTED"  # Restriction has been removed


class AccountRestriction(Base):
    """
    Account restriction recommendation for existing customer sanctions cases.

    Allows analysts to recommend restrictions on existing customer accounts
    when sanctions matches are identified.
    """

    __tablename__ = "account_restrictions"

    id: Mapped[UUID] = Column(DatabaseAgnosticUUID(), primary_key=True, default=uuid4)

    case_id: Mapped[UUID] = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("cases.id"),
        nullable=False
    )

    customer_id: Mapped[str] = Column(String(255), nullable=False, index=True)

    restriction_type: Mapped[RestrictionType] = Column(
        SQLEnum(RestrictionType, name="restriction_type", create_type=False),
        nullable=False
    )

    status: Mapped[RestrictionStatus] = Column(
        SQLEnum(RestrictionStatus, name="restriction_status", create_type=False),
        nullable=False,
        default=RestrictionStatus.RECOMMENDED
    )

    reason: Mapped[str] = Column(Text, nullable=False)

    effective_immediately: Mapped[bool] = Column(Boolean, nullable=False, default=False)

    recommended_by_id: Mapped[UUID] = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("users.id"),
        nullable=False
    )

    recommended_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )

    approved_by_id: Mapped[Optional[UUID]] = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("users.id"),
        nullable=True
    )

    approved_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True),
        nullable=True
    )

    implemented_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True),
        nullable=True
    )

    lifted_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True),
        nullable=True
    )

    notes: Mapped[Optional[str]] = Column(Text, nullable=True)

    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )

    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<AccountRestriction {self.restriction_type.value} for {self.customer_id}>"

    @classmethod
    def create(
        cls,
        case_id: UUID,
        customer_id: str,
        restriction_type: RestrictionType,
        reason: str,
        recommended_by_id: UUID,
        effective_immediately: bool = False
    ) -> "AccountRestriction":
        """
        Create a new account restriction recommendation.

        Args:
            case_id: Associated case ID
            customer_id: Customer external ID
            restriction_type: Type of restriction
            reason: Justification for restriction
            recommended_by_id: User making recommendation
            effective_immediately: Whether to implement immediately

        Returns:
            New AccountRestriction instance
        """
        return cls(
            case_id=case_id,
            customer_id=customer_id,
            restriction_type=restriction_type,
            reason=reason,
            recommended_by_id=recommended_by_id,
            effective_immediately=effective_immediately,
            status=RestrictionStatus.RECOMMENDED
        )

    def approve(self, approved_by_id: UUID) -> None:
        """Approve the restriction recommendation."""
        self.status = RestrictionStatus.APPROVED
        self.approved_by_id = approved_by_id
        self.approved_at = datetime.utcnow()

    def reject(self, approved_by_id: UUID, notes: Optional[str] = None) -> None:
        """Reject the restriction recommendation."""
        self.status = RestrictionStatus.REJECTED
        self.approved_by_id = approved_by_id
        self.approved_at = datetime.utcnow()
        if notes:
            self.notes = notes

    def mark_implemented(self) -> None:
        """Mark the restriction as implemented."""
        self.status = RestrictionStatus.IMPLEMENTED
        self.implemented_at = datetime.utcnow()

    def lift(self, notes: Optional[str] = None) -> None:
        """Lift the restriction."""
        self.status = RestrictionStatus.LIFTED
        self.lifted_at = datetime.utcnow()
        if notes:
            self.notes = notes
