"""
SMR (Suspicious Matter Report) recommendation model.

References:
- FR-014: Only L2 or higher can create SMR recommendations
- FR-039: SMR recommendation must include justification
- BR-SMR-001: SMR can only be created by L2 or AML Manager
- BR-SMR-002: Different analyst must approve SMR
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from src.models.base import DatabaseAgnosticUUID
from sqlalchemy.orm import Mapped, relationship

from src.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.case import Case
    from src.models.user import User


class SMRRecommendationType(str, Enum):
    """SMR recommendation type."""

    SUBMIT = "SUBMIT"
    DO_NOT_SUBMIT = "DO_NOT_SUBMIT"


class SMRStatus(str, Enum):
    """SMR workflow status."""

    DRAFT = "DRAFT"
    PENDING = "PENDING_APPROVAL"  # Alias for backwards compatibility
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FILED = "FILED"


class SMRRecommendation(Base, UUIDPrimaryKeyMixin):
    """
    Suspicious Matter Report recommendation.

    Tracks the SMR workflow from recommendation through approval and filing.
    """

    __tablename__ = "smr_recommendations"

    # Case relationship
    case_id: Mapped[UUID] = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("cases.id"),
        nullable=False,
        index=True
    )
    case: Mapped["Case"] = relationship("Case", backref="smr_recommendations")

    # Recommendation details
    recommendation_type: Mapped[SMRRecommendationType] = Column(
        SQLEnum(SMRRecommendationType, name="smr_recommendation_type", create_type=False),
        nullable=False
    )
    justification: Mapped[str] = Column(Text, nullable=False)
    suspicious_activity: Mapped[str] = Column(Text, nullable=False)

    # Supporting documents as JSON array
    supporting_documents: Mapped[list] = Column(JSONB, nullable=False, default=list)

    # Status
    status: Mapped[SMRStatus] = Column(
        SQLEnum(SMRStatus, name="smr_status", create_type=False),
        nullable=False,
        default=SMRStatus.DRAFT
    )

    # Recommender (L2 analyst)
    recommended_by_id: Mapped[UUID] = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("users.id"),
        nullable=False
    )
    recommended_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[recommended_by_id]
    )
    recommended_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )

    # Approver (Manager) - BR-SMR-002: Must be different from recommender
    approved_by_id: Mapped[Optional[UUID]] = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("users.id"),
        nullable=True
    )
    approved_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[approved_by_id]
    )
    approved_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True),
        nullable=True
    )

    # Rejection details
    rejection_reason: Mapped[Optional[str]] = Column(Text, nullable=True)
    rejected_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True),
        nullable=True
    )

    # AUSTRAC filing details
    austrac_reference: Mapped[Optional[str]] = Column(String(100), nullable=True)
    filed_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True),
        nullable=True
    )
    filing_deadline: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True),
        nullable=True
    )

    # Timestamps
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
        return f"<SMRRecommendation case={self.case_id} status={self.status.value}>"

    @classmethod
    def create(
        cls,
        case_id: UUID,
        recommended_by_id: UUID,
        recommendation_type: SMRRecommendationType,
        justification: str,
        suspicious_activity: str,
        supporting_documents: list[str]
    ) -> "SMRRecommendation":
        """
        Create a new SMR recommendation.

        Args:
            case_id: Case ID
            recommended_by_id: L2 analyst ID
            recommendation_type: Submit or do not submit
            justification: Detailed justification
            suspicious_activity: Description of suspicious activity
            supporting_documents: List of supporting document names

        Returns:
            New SMRRecommendation instance
        """
        return cls(
            case_id=case_id,
            recommended_by_id=recommended_by_id,
            recommendation_type=recommendation_type,
            justification=justification,
            suspicious_activity=suspicious_activity,
            supporting_documents=supporting_documents,
            status=SMRStatus.PENDING_APPROVAL
        )

    def approve(self, approver_id: UUID) -> None:
        """
        Approve the SMR recommendation.

        Args:
            approver_id: Manager approving the SMR

        Raises:
            ValueError: If approver is the same as recommender
        """
        if approver_id == self.recommended_by_id:
            raise ValueError("SMR cannot be approved by the same person who recommended it")

        self.approved_by_id = approver_id
        self.approved_at = datetime.utcnow()
        self.status = SMRStatus.APPROVED

        # Set 3-day filing deadline (FR-042)
        from datetime import timedelta
        self.filing_deadline = datetime.utcnow() + timedelta(days=3)

    def reject(self, reason: str) -> None:
        """
        Reject the SMR recommendation.

        Args:
            reason: Reason for rejection
        """
        self.rejection_reason = reason
        self.rejected_at = datetime.utcnow()
        self.status = SMRStatus.REJECTED

    def record_filing(self, austrac_reference: str) -> None:
        """
        Record AUSTRAC filing details.

        Args:
            austrac_reference: AUSTRAC reference number
        """
        self.austrac_reference = austrac_reference
        self.filed_at = datetime.utcnow()
        self.status = SMRStatus.FILED
