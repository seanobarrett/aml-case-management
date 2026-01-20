"""
SLA service for managing case SLA tracking, warnings, and breaches.

References:
- FR-048: SLA calculation with business days
- FR-049: Case type SLA configuration
- FR-050: SLA warning notifications
- FR-051: Automatic escalation on breach
- FR-052: Manager notification for breaches
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.case import Case, CaseStatus, CaseTier
from src.services.sla_calculator import SLACalculator


class SLAService:
    """
    Service for managing SLA tracking, warnings, and breach handling.
    """

    def __init__(self, db: Session):
        """
        Initialize SLA service.

        Args:
            db: Database session
        """
        self.db = db
        self.calculator = SLACalculator(db)

    def set_sla_deadline(self, case: Case) -> datetime:
        """
        Set initial SLA deadline for a case.

        Args:
            case: Case to set deadline for

        Returns:
            Calculated SLA deadline
        """
        deadline = self.calculator.calculate_sla_deadline(
            case_type=case.case_type,
            created_at=case.created_at
        )
        case.sla_deadline = deadline
        self.db.flush()
        return deadline

    def check_sla_status(self, case: Case) -> dict:
        """
        Check current SLA status for a case.

        Args:
            case: Case to check

        Returns:
            Dict with SLA status information
        """
        if case.sla_deadline is None:
            return {
                "has_deadline": False,
                "is_breached": False,
                "is_approaching": False,
                "sla_paused": case.sla_paused,
            }

        current_time = datetime.utcnow()
        is_breached = self.calculator.is_breached(case.sla_deadline, current_time)
        is_approaching = self.calculator.is_approaching_breach(
            case.created_at, case.sla_deadline, current_time
        )

        return {
            "has_deadline": True,
            "sla_deadline": case.sla_deadline,
            "is_breached": is_breached,
            "is_approaching": is_approaching and not is_breached,
            "sla_paused": case.sla_paused,
            "warning_sent": case.sla_warning_sent,
            "breach_recorded": case.sla_breach,
        }

    def pause_sla(self, case: Case, reason: Optional[str] = None) -> None:
        """
        Pause SLA timer for a case (e.g., waiting for customer information).

        Args:
            case: Case to pause SLA for
            reason: Optional reason for pausing
        """
        if case.sla_paused:
            return  # Already paused

        case.sla_paused = True
        case.sla_pause_start = datetime.utcnow()
        self.db.flush()

    def resume_sla(self, case: Case) -> Optional[datetime]:
        """
        Resume SLA timer and adjust deadline.

        Args:
            case: Case to resume SLA for

        Returns:
            New adjusted deadline, or None if not paused
        """
        if not case.sla_paused or case.sla_pause_start is None:
            return None

        resume_time = datetime.utcnow()

        # Calculate adjusted deadline
        if case.sla_deadline:
            new_deadline = self.calculator.calculate_adjusted_deadline(
                original_deadline=case.sla_deadline,
                pause_start=case.sla_pause_start,
                resume_time=resume_time
            )
            case.sla_deadline = new_deadline

        case.sla_paused = False
        case.sla_pause_start = None
        self.db.flush()

        return case.sla_deadline

    def record_warning_sent(self, case: Case) -> None:
        """
        Record that SLA warning was sent.

        Args:
            case: Case that received warning
        """
        case.sla_warning_sent = True
        case.sla_warning_sent_at = datetime.utcnow()
        self.db.flush()

    def record_breach(self, case: Case) -> None:
        """
        Record SLA breach and trigger escalation.

        Args:
            case: Case that breached SLA
        """
        if case.sla_breach:
            return  # Already recorded

        case.sla_breach = True
        case.sla_breach_at = datetime.utcnow()
        self.db.flush()

    def escalate_for_breach(self, case: Case) -> bool:
        """
        Escalate case due to SLA breach (FR-051).

        Args:
            case: Case to escalate

        Returns:
            True if case was escalated
        """
        # Don't escalate if already at highest tier or closed
        if case.tier == CaseTier.L2 or case.status == CaseStatus.CLOSED:
            return False

        # Escalate L1 to L2
        if case.tier == CaseTier.L1:
            case.tier = CaseTier.L2
            # Unassign so L2 analyst can claim
            case.assigned_to = None
            case.status = CaseStatus.NEW
            self.db.flush()
            return True

        return False

    def get_cases_approaching_sla(self) -> list[Case]:
        """
        Get all cases approaching SLA deadline.

        Returns:
            List of cases approaching SLA
        """
        # Get all open cases with SLA deadlines
        cases = self.db.query(Case).filter(
            Case.status.in_([CaseStatus.NEW, CaseStatus.ASSIGNED, CaseStatus.PENDING_INFO]),
            Case.sla_deadline.isnot(None),
            Case.sla_paused == False,
            Case.sla_warning_sent == False,
            Case.sla_breach == False,
        ).all()

        approaching = []
        for case in cases:
            if self.calculator.is_approaching_breach(
                case.created_at, case.sla_deadline
            ):
                approaching.append(case)

        return approaching

    def get_breached_cases(self) -> list[Case]:
        """
        Get all cases that have breached SLA.

        Returns:
            List of breached cases
        """
        # Get all open cases with SLA deadlines
        cases = self.db.query(Case).filter(
            Case.status.in_([CaseStatus.NEW, CaseStatus.ASSIGNED, CaseStatus.PENDING_INFO]),
            Case.sla_deadline.isnot(None),
            Case.sla_paused == False,
            Case.sla_breach == False,
        ).all()

        breached = []
        for case in cases:
            if self.calculator.is_breached(case.sla_deadline):
                breached.append(case)

        return breached

    def process_sla_warnings(self) -> list[UUID]:
        """
        Process SLA warnings for all approaching cases.

        Returns:
            List of case IDs that received warnings
        """
        cases = self.get_cases_approaching_sla()
        warned_case_ids = []

        for case in cases:
            self.record_warning_sent(case)
            warned_case_ids.append(case.id)

        self.db.commit()
        return warned_case_ids

    def process_sla_breaches(self) -> list[dict]:
        """
        Process all SLA breaches: record and escalate.

        Returns:
            List of dicts with breach info (case_id, escalated)
        """
        cases = self.get_breached_cases()
        results = []

        for case in cases:
            self.record_breach(case)
            escalated = self.escalate_for_breach(case)
            results.append({
                "case_id": case.id,
                "escalated": escalated,
                "case_reference": case.case_reference,
            })

        self.db.commit()
        return results
