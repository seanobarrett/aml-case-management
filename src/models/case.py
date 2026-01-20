"""
Case model for AML investigations.

References:
- FR-003: System generates unique case reference (AML-NNNN)
- FR-004: System captures case creation timestamp
- FR-005: System sets initial case status (OPEN)
- D9: PostgreSQL SEQUENCE with AML-NNNN prefix
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, relationship

from src.models.base import Base, UUIDPrimaryKeyMixin, VersionedMixin, DatabaseAgnosticUUID

if TYPE_CHECKING:
    from src.models.customer import Customer
    from src.models.user import User
    from src.models.assignment import Assignment
    from src.models.onboarding_block import OnboardingBlock
    from src.models.case_link import CaseLink


class CaseStatus(str, Enum):
    """Case status enumeration."""

    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    PENDING_INFORMATION = "PENDING_INFORMATION"
    ESCALATED = "ESCALATED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    CLOSED = "CLOSED"


class CaseType(str, Enum):
    """Case type enumeration."""

    KYC_REMEDIATION = "KYC_REMEDIATION"
    PEP_SCREENING = "PEP_SCREENING"
    PEP_HIGH_CONFIDENCE = "PEP_HIGH_CONFIDENCE"
    PEP_LOW_CONFIDENCE = "PEP_LOW_CONFIDENCE"
    SANCTIONS_ONBOARDING = "SANCTIONS_ONBOARDING"
    SANCTIONS_EXISTING_CUSTOMER = "SANCTIONS_EXISTING_CUSTOMER"
    SANCTIONS_PEP_COMBINED = "SANCTIONS_PEP_COMBINED"  # FR-035: Combined alerts
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"
    SMR_SUPPLEMENTARY = "SMR_SUPPLEMENTARY"  # FR-044: Supplementary SMR filing


class CaseTier(str, Enum):
    """Case tier for analyst assignment."""

    L1 = "L1"
    L2 = "L2"


class L2ReviewStatus(str, Enum):
    """L2 quality review status for L1 closures."""

    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING_REVIEW = "PENDING_REVIEW"
    REVIEWED_ACCEPTED = "REVIEWED_ACCEPTED"
    REVIEWED_REOPENED = "REVIEWED_REOPENED"


class Case(Base, UUIDPrimaryKeyMixin, VersionedMixin):
    """
    AML Case entity for investigations.

    Cases are created from GreenID/Indue webhooks and progress through
    a workflow from OPEN to CLOSED with various intermediate states.
    """

    __tablename__ = "cases"

    # Reference - auto-generated from sequence (D9)
    case_reference: Mapped[str] = Column(
        String(20),
        nullable=False,
        unique=True,
        # Default handled by PostgreSQL sequence in migration
    )

    # Type and status
    case_type: Mapped[CaseType] = Column(
        SQLEnum(CaseType, name="case_type", create_type=False),
        nullable=False
    )
    status: Mapped[CaseStatus] = Column(
        SQLEnum(CaseStatus, name="case_status", create_type=False),
        nullable=False,
        default=CaseStatus.OPEN
    )
    tier: Mapped[CaseTier] = Column(
        SQLEnum(CaseTier, name="case_tier", create_type=False),
        nullable=False,
        default=CaseTier.L1
    )

    # Customer relationship (snapshot at case creation)
    customer_id: Mapped[UUID] = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("customers.id"),
        nullable=False
    )
    customer: Mapped["Customer"] = relationship("Customer", back_populates="cases")

    # Assignment
    assigned_to_id: Mapped[Optional[UUID]] = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("users.id"),
        nullable=True
    )
    assigned_to: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="assigned_cases",
        foreign_keys=[assigned_to_id]
    )

    # L2 review status for L1 closures
    l2_review_status: Mapped[L2ReviewStatus] = Column(
        SQLEnum(L2ReviewStatus, name="l2_review_status", create_type=False),
        nullable=False,
        default=L2ReviewStatus.NOT_REQUIRED
    )

    # SLA tracking
    sla_deadline: Mapped[Optional[datetime]] = Column(DateTime(timezone=True), nullable=True)
    sla_paused: Mapped[bool] = Column(Boolean, nullable=False, default=False)
    sla_pause_start: Mapped[Optional[datetime]] = Column(DateTime(timezone=True), nullable=True)
    sla_warning_sent: Mapped[bool] = Column(Boolean, nullable=False, default=False)
    sla_warning_sent_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True), nullable=True)
    sla_breach: Mapped[bool] = Column(Boolean, nullable=False, default=False)
    sla_breach_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True), nullable=True)

    # Closure details
    closure_reason: Mapped[Optional[str]] = Column(Text, nullable=True)
    closure_documentation: Mapped[Optional[str]] = Column(Text, nullable=True)
    closed_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True), nullable=True)

    # Special flags
    enhanced_monitoring: Mapped[bool] = Column(Boolean, nullable=False, default=False)

    # Escalation details
    escalation_reason: Mapped[Optional[str]] = Column(Text, nullable=True)
    escalation_findings: Mapped[Optional[str]] = Column(Text, nullable=True)
    escalated_by_id: Mapped[Optional[UUID]] = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("users.id"),
        nullable=True
    )
    escalated_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True), nullable=True)

    # External references
    external_verification_id: Mapped[Optional[str]] = Column(String(255), nullable=True)
    external_screening_id: Mapped[Optional[str]] = Column(String(255), nullable=True)

    # PEP-specific
    pep_match_score: Mapped[Optional[int]] = Column(Integer, nullable=True)

    # Source payload (for audit)
    source_webhook_payload: Mapped[Optional[dict]] = Column(JSONB, nullable=True)

    # Alert types for combined alerts
    alert_types: Mapped[Optional[list]] = Column(JSONB, nullable=True)

    # Supplementary SMR fields (FR-044, FR-046)
    original_case_id: Mapped[Optional[UUID]] = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("cases.id"),
        nullable=True
    )
    supplementary_reason: Mapped[Optional[str]] = Column(Text, nullable=True)
    supplementary_evidence: Mapped[Optional[str]] = Column(Text, nullable=True)

    # Relationships
    assignments: Mapped[list["Assignment"]] = relationship(
        "Assignment",
        back_populates="case",
        order_by="Assignment.assigned_at.desc()"
    )

    # Onboarding block relationship
    onboarding_block: Mapped[Optional["OnboardingBlock"]] = relationship(
        "OnboardingBlock",
        back_populates="case",
        uselist=False
    )

    # Case links - outgoing and incoming for bidirectional navigation
    outgoing_links: Mapped[list["CaseLink"]] = relationship(
        "CaseLink",
        foreign_keys="CaseLink.source_case_id",
        back_populates="source_case"
    )
    incoming_links: Mapped[list["CaseLink"]] = relationship(
        "CaseLink",
        foreign_keys="CaseLink.target_case_id",
        back_populates="target_case"
    )

    # Class-level counter for reference generation (used when DB sequence unavailable)
    _reference_counter: int = 0

    def __repr__(self) -> str:
        return f"<Case {self.case_reference} [{self.status.value}]>"

    @classmethod
    def generate_reference(cls, db_session=None) -> str:
        """
        Generate a unique case reference (AML-NNNN format).

        In PostgreSQL, this is handled by a database sequence.
        For SQLite (testing), uses a class-level counter with max ID lookup.

        Args:
            db_session: Optional database session for max ID lookup

        Returns:
            Unique case reference string
        """
        if db_session:
            # Get max ID from existing cases
            from sqlalchemy import func
            result = db_session.query(func.count(cls.id)).scalar()
            next_num = (result or 0) + 1
        else:
            # Fallback to class counter
            cls._reference_counter += 1
            next_num = cls._reference_counter

        return f"AML-{next_num:04d}"

    # Alias properties for backwards compatibility
    @property
    def sla_paused_at(self) -> Optional[datetime]:
        """Alias for sla_pause_start for backwards compatibility."""
        return self.sla_pause_start

    @property
    def sla_breached(self) -> bool:
        """Alias for sla_breach for backwards compatibility."""
        return self.sla_breach

    @property
    def is_open(self) -> bool:
        """Check if case is in an open state."""
        return self.status not in (CaseStatus.CLOSED, CaseStatus.APPROVED)

    @property
    def is_assigned(self) -> bool:
        """Check if case is currently assigned to an analyst."""
        return self.assigned_to_id is not None

    @property
    def requires_l2_review(self) -> bool:
        """Check if case requires L2 quality review."""
        return self.l2_review_status == L2ReviewStatus.PENDING_REVIEW

    def claim(self, user_id: UUID) -> None:
        """
        Claim the case for an analyst.

        Args:
            user_id: ID of the claiming user
        """
        self.assigned_to_id = user_id
        self.status = CaseStatus.ASSIGNED

    def close(
        self,
        reason: str,
        documentation: str,
        requires_l2_review: bool = False
    ) -> None:
        """
        Close the case with documentation.

        Args:
            reason: Reason for closure
            documentation: Supporting documentation
            requires_l2_review: Whether to flag for L2 quality review
        """
        self.status = CaseStatus.CLOSED
        self.closure_reason = reason
        self.closure_documentation = documentation
        self.closed_at = datetime.utcnow()

        if requires_l2_review:
            self.l2_review_status = L2ReviewStatus.PENDING_REVIEW

    def escalate(self) -> None:
        """Escalate case from L1 to L2."""
        self.tier = CaseTier.L2
        self.status = CaseStatus.ESCALATED
        self.assigned_to_id = None  # Unassign for L2 queue

    def reopen(self) -> None:
        """Reopen a closed case."""
        self.status = CaseStatus.OPEN
        self.closure_reason = None
        self.closure_documentation = None
        self.closed_at = None
        self.l2_review_status = L2ReviewStatus.REVIEWED_REOPENED

    @property
    def linked_cases(self) -> list["CaseLink"]:
        """Get all linked cases (both directions)."""
        return self.outgoing_links

    @property
    def has_onboarding_block(self) -> bool:
        """Check if case has an active onboarding block."""
        return (
            self.onboarding_block is not None and
            self.onboarding_block.is_active
        )
