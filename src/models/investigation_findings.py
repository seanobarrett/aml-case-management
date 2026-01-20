"""
Investigation findings model for L2 case investigations.

References:
- US-4: L2 Analyst investigates case and recommends SMR
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


class RiskAssessment(str, Enum):
    """Risk assessment level."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class InvestigationRecommendation(str, Enum):
    """Investigation outcome recommendation."""

    FALSE_POSITIVE = "FALSE_POSITIVE"
    TRUE_MATCH_NO_SMR = "TRUE_MATCH_NO_SMR"
    FURTHER_REVIEW = "FURTHER_REVIEW"
    SMR_REQUIRED = "SMR_REQUIRED"


class InvestigationFindings(Base, UUIDPrimaryKeyMixin):
    """
    Investigation findings documented by L2 analyst.

    Captures the investigation methodology, key findings, risk assessment,
    and recommendation for case disposition.
    """

    __tablename__ = "investigation_findings"

    # Case relationship
    case_id: Mapped[UUID] = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("cases.id"),
        nullable=False,
        index=True
    )
    case: Mapped["Case"] = relationship("Case", backref="investigation_findings")

    # Investigator
    investigator_id: Mapped[UUID] = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("users.id"),
        nullable=False
    )
    investigator: Mapped["User"] = relationship("User")

    # Investigation summary
    summary: Mapped[str] = Column(Text, nullable=False)
    methodology: Mapped[str] = Column(Text, nullable=False)

    # Key findings as JSON array
    key_findings: Mapped[list] = Column(JSONB, nullable=False, default=list)

    # Assessment and recommendation
    risk_assessment: Mapped[RiskAssessment] = Column(
        SQLEnum(RiskAssessment, name="risk_assessment", create_type=False),
        nullable=False
    )
    recommendation: Mapped[InvestigationRecommendation] = Column(
        SQLEnum(InvestigationRecommendation, name="investigation_recommendation", create_type=False),
        nullable=False
    )

    # Optional notes
    additional_notes: Mapped[Optional[str]] = Column(Text, nullable=True)

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
        return f"<InvestigationFindings case={self.case_id} risk={self.risk_assessment.value}>"

    @classmethod
    def create(
        cls,
        case_id: UUID,
        investigator_id: UUID,
        summary: str,
        methodology: str,
        key_findings: list[str],
        risk_assessment: RiskAssessment,
        recommendation: InvestigationRecommendation,
        additional_notes: Optional[str] = None
    ) -> "InvestigationFindings":
        """
        Create new investigation findings.

        Args:
            case_id: Case being investigated
            investigator_id: L2 analyst conducting investigation
            summary: Investigation summary
            methodology: Investigation methodology used
            key_findings: List of key findings
            risk_assessment: Risk assessment level
            recommendation: Investigation recommendation
            additional_notes: Optional additional notes

        Returns:
            New InvestigationFindings instance
        """
        return cls(
            case_id=case_id,
            investigator_id=investigator_id,
            summary=summary,
            methodology=methodology,
            key_findings=key_findings,
            risk_assessment=risk_assessment,
            recommendation=recommendation,
            additional_notes=additional_notes
        )
