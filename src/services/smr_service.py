"""
SMR (Suspicious Matter Report) service.

References:
- FR-014: Only L2 or higher can create SMR recommendations
- FR-039: SMR recommendation must include justification
- FR-020, FR-021: Manager approval workflow
- BR-SMR-001: SMR can only be created by L2 or AML Manager
- BR-SMR-002: Different analyst must approve SMR
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.case import Case, CaseStatus
from src.models.smr_recommendation import (
    SMRRecommendation,
    SMRRecommendationType,
    SMRStatus
)
from src.models.timeline_entry import TimelineEntry
from src.services.notification_service import NotificationService


class SMRService:
    """Service for SMR recommendation management."""

    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService(db)

    def create_recommendation(
        self,
        case_id: UUID,
        user_id: UUID,
        recommendation_type: str,
        justification: str,
        suspicious_activity: str,
        supporting_documents: list[str]
    ) -> SMRRecommendation:
        """
        Create an SMR recommendation.

        Args:
            case_id: Case ID
            user_id: L2 analyst or manager ID
            recommendation_type: SUBMIT or DO_NOT_SUBMIT
            justification: Detailed justification
            suspicious_activity: Description of suspicious activity
            supporting_documents: List of supporting document names

        Returns:
            Created SMRRecommendation

        Raises:
            ValueError: If case not found
        """
        # Get case
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ValueError(f"Case not found: {case_id}")

        # Parse recommendation type
        rec_type = SMRRecommendationType(recommendation_type.upper())

        # Create recommendation
        smr = SMRRecommendation.create(
            case_id=case_id,
            recommended_by_id=user_id,
            recommendation_type=rec_type,
            justification=justification,
            suspicious_activity=suspicious_activity,
            supporting_documents=supporting_documents
        )
        self.db.add(smr)

        # Update case status to PENDING_APPROVAL
        case.status = CaseStatus.PENDING_APPROVAL

        # Create timeline entry
        timeline_entry = TimelineEntry.create(
            case_id=case_id,
            entry_type="SMR_RECOMMENDED",
            content=f"SMR recommendation: {rec_type.value}",
            acting_user_id=user_id,
            metadata={
                "recommendation_type": rec_type.value,
                "has_supporting_docs": len(supporting_documents) > 0
            }
        )
        self.db.add(timeline_entry)

        # Notify managers (FR-068)
        self.notification_service.notify_smr_submission(
            case_id=case_id,
            case_reference=case.case_reference
        )

        self.db.commit()
        self.db.refresh(smr)

        return smr

    def get_case_recommendations(self, case_id: UUID) -> list[SMRRecommendation]:
        """Get all SMR recommendations for a case."""
        return (
            self.db.query(SMRRecommendation)
            .filter(SMRRecommendation.case_id == case_id)
            .order_by(SMRRecommendation.created_at.desc())
            .all()
        )

    def get_pending_recommendations(self) -> list[SMRRecommendation]:
        """Get all pending SMR recommendations."""
        return (
            self.db.query(SMRRecommendation)
            .filter(SMRRecommendation.status == SMRStatus.PENDING_APPROVAL)
            .order_by(SMRRecommendation.created_at.asc())
            .all()
        )

    def approve(
        self,
        smr_id: UUID,
        approver_id: UUID
    ) -> SMRRecommendation:
        """
        Approve an SMR recommendation.

        Args:
            smr_id: SMR recommendation ID
            approver_id: Manager approving the SMR

        Returns:
            Updated SMRRecommendation

        Raises:
            ValueError: If SMR not found or approver is the recommender
        """
        smr = self.db.query(SMRRecommendation).filter(
            SMRRecommendation.id == smr_id
        ).first()

        if not smr:
            raise ValueError(f"SMR recommendation not found: {smr_id}")

        # Enforce segregation of duties (BR-SMR-002)
        smr.approve(approver_id)

        # Update case status
        case = self.db.query(Case).filter(Case.id == smr.case_id).first()
        if case:
            case.status = CaseStatus.APPROVED

        # Create timeline entry
        timeline_entry = TimelineEntry.create(
            case_id=smr.case_id,
            entry_type="SMR_APPROVED",
            content="SMR recommendation approved by manager",
            acting_user_id=approver_id,
            metadata={
                "filing_deadline": smr.filing_deadline.isoformat() if smr.filing_deadline else None
            }
        )
        self.db.add(timeline_entry)

        self.db.commit()
        self.db.refresh(smr)

        return smr

    def reject(
        self,
        smr_id: UUID,
        rejector_id: UUID,
        reason: str
    ) -> SMRRecommendation:
        """
        Reject an SMR recommendation.

        Args:
            smr_id: SMR recommendation ID
            rejector_id: Manager rejecting the SMR
            reason: Rejection reason

        Returns:
            Updated SMRRecommendation
        """
        smr = self.db.query(SMRRecommendation).filter(
            SMRRecommendation.id == smr_id
        ).first()

        if not smr:
            raise ValueError(f"SMR recommendation not found: {smr_id}")

        smr.reject(reason)

        # Update case status back to assigned
        case = self.db.query(Case).filter(Case.id == smr.case_id).first()
        if case:
            case.status = CaseStatus.ASSIGNED

        # Create timeline entry
        timeline_entry = TimelineEntry.create(
            case_id=smr.case_id,
            entry_type="SMR_REJECTED",
            content=f"SMR recommendation rejected: {reason[:100]}...",
            acting_user_id=rejector_id,
            metadata={
                "rejection_reason": reason
            }
        )
        self.db.add(timeline_entry)

        self.db.commit()
        self.db.refresh(smr)

        return smr

    def record_filing(
        self,
        smr_id: UUID,
        user_id: UUID,
        austrac_reference: str
    ) -> SMRRecommendation:
        """
        Record AUSTRAC filing details.

        Args:
            smr_id: SMR recommendation ID
            user_id: User recording the filing
            austrac_reference: AUSTRAC reference number

        Returns:
            Updated SMRRecommendation
        """
        smr = self.db.query(SMRRecommendation).filter(
            SMRRecommendation.id == smr_id
        ).first()

        if not smr:
            raise ValueError(f"SMR recommendation not found: {smr_id}")

        if smr.status != SMRStatus.APPROVED:
            raise ValueError("SMR must be approved before filing can be recorded")

        smr.record_filing(austrac_reference)

        # Update case status
        case = self.db.query(Case).filter(Case.id == smr.case_id).first()
        if case:
            case.status = CaseStatus.CLOSED

        # Create timeline entry
        timeline_entry = TimelineEntry.create(
            case_id=smr.case_id,
            entry_type="SMR_FILED",
            content=f"SMR filed with AUSTRAC. Reference: {austrac_reference}",
            acting_user_id=user_id,
            metadata={
                "austrac_reference": austrac_reference
            }
        )
        self.db.add(timeline_entry)

        self.db.commit()
        self.db.refresh(smr)

        return smr
