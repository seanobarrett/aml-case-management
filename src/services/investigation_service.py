"""
Investigation service for L2 case investigations.

References:
- US-4: L2 Analyst investigates case and recommends SMR
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.investigation_findings import (
    InvestigationFindings,
    RiskAssessment,
    InvestigationRecommendation
)
from src.models.timeline_entry import TimelineEntry


class InvestigationService:
    """Service for managing investigation findings."""

    def __init__(self, db: Session):
        self.db = db

    def create_findings(
        self,
        case_id: UUID,
        investigator_id: UUID,
        summary: str,
        methodology: str,
        key_findings: list[str],
        risk_assessment: str,
        recommendation: str,
        additional_notes: Optional[str] = None
    ) -> InvestigationFindings:
        """
        Create investigation findings for a case.

        Args:
            case_id: Case ID
            investigator_id: L2 analyst ID
            summary: Investigation summary
            methodology: Investigation methodology
            key_findings: List of key findings
            risk_assessment: Risk level (LOW/MEDIUM/HIGH/CRITICAL)
            recommendation: Investigation recommendation
            additional_notes: Optional notes

        Returns:
            Created InvestigationFindings instance
        """
        # Parse enums
        risk = RiskAssessment(risk_assessment.upper())
        rec = InvestigationRecommendation(recommendation.upper())

        # Create findings
        findings = InvestigationFindings.create(
            case_id=case_id,
            investigator_id=investigator_id,
            summary=summary,
            methodology=methodology,
            key_findings=key_findings,
            risk_assessment=risk,
            recommendation=rec,
            additional_notes=additional_notes
        )
        self.db.add(findings)

        # Create timeline entry
        timeline_entry = TimelineEntry.create(
            case_id=case_id,
            entry_type="FINDINGS_DOCUMENTED",
            content=f"Investigation findings documented. Risk: {risk.value}. Recommendation: {rec.value}. Findings: {len(key_findings)}",
            acting_user_id=investigator_id
        )
        self.db.add(timeline_entry)

        self.db.commit()
        self.db.refresh(findings)

        return findings

    def get_case_findings(self, case_id: UUID) -> list[InvestigationFindings]:
        """
        Get all investigation findings for a case.

        Args:
            case_id: Case ID

        Returns:
            List of findings ordered by creation date
        """
        return (
            self.db.query(InvestigationFindings)
            .filter(InvestigationFindings.case_id == case_id)
            .order_by(InvestigationFindings.created_at.desc())
            .all()
        )

    def get_latest_findings(self, case_id: UUID) -> Optional[InvestigationFindings]:
        """
        Get the most recent investigation findings for a case.

        Args:
            case_id: Case ID

        Returns:
            Latest InvestigationFindings or None
        """
        return (
            self.db.query(InvestigationFindings)
            .filter(InvestigationFindings.case_id == case_id)
            .order_by(InvestigationFindings.created_at.desc())
            .first()
        )

    def has_findings(self, case_id: UUID) -> bool:
        """
        Check if a case has any investigation findings.

        Args:
            case_id: Case ID

        Returns:
            True if findings exist
        """
        return (
            self.db.query(InvestigationFindings)
            .filter(InvestigationFindings.case_id == case_id)
            .count() > 0
        )
