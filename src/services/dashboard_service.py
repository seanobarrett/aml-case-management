"""
Dashboard service for case prioritization and queue metrics.

References:
- US-12: Dashboard with prioritized work queue
- FR-024: Cases filtered by status
- FR-025: Cases ordered by SLA priority
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.case import Case, CaseStatus, CaseType, CaseTier
from src.services.sla_calculator import SLACalculator


class SLAIndicator(str, Enum):
    """SLA status indicator for dashboard display."""
    ON_TRACK = "ON_TRACK"
    WARNING = "WARNING"
    BREACHED = "BREACHED"
    PAUSED = "PAUSED"
    NO_SLA = "NO_SLA"


class DashboardService:
    """
    Service for dashboard data including case prioritization and metrics.
    """

    def __init__(self, db: Session):
        """
        Initialize dashboard service.

        Args:
            db: Database session
        """
        self.db = db
        self.sla_calculator = SLACalculator(db)

    def get_my_cases(
        self,
        user_id: UUID,
        status: Optional[CaseStatus] = None,
        case_type: Optional[CaseType] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list[dict], int]:
        """
        Get cases assigned to the user with SLA indicators.

        Cases are ordered by SLA deadline ascending (FR-025).

        Args:
            user_id: User ID to get cases for
            status: Optional status filter
            case_type: Optional case type filter
            page: Page number
            page_size: Items per page

        Returns:
            Tuple of (case list with indicators, total count)
        """
        query = self.db.query(Case).filter(
            Case.assigned_to_id == user_id
        )

        # Apply filters
        if status:
            query = query.filter(Case.status == status)
        if case_type:
            query = query.filter(Case.case_type == case_type)

        # Get total count
        total = query.count()

        # Order by SLA priority (FR-025)
        # Breached first, then by deadline ascending
        query = query.order_by(
            Case.sla_breach.desc(),  # Breached cases first
            Case.sla_deadline.asc().nullslast()  # Then by deadline
        )

        # Apply pagination
        offset = (page - 1) * page_size
        cases = query.offset(offset).limit(page_size).all()

        # Build response with SLA indicators
        result = []
        for case in cases:
            indicator = self._calculate_sla_indicator(case)
            result.append({
                "id": str(case.id),
                "caseReference": case.case_reference,
                "caseType": case.case_type.value,
                "status": case.status.value,
                "tier": case.tier.value,
                "customerId": str(case.customer_id),
                "customerName": case.customer.full_name if case.customer else None,
                "assignedToId": str(case.assigned_to_id) if case.assigned_to_id else None,
                "slaDeadline": case.sla_deadline.isoformat() if case.sla_deadline else None,
                "slaIndicator": indicator.value,
                "slaBreach": case.sla_breach,
                "slaPaused": case.sla_paused,
                "createdAt": case.created_at.isoformat()
            })

        return result, total

    def get_queue_metrics(self, tier: Optional[CaseTier] = None) -> dict:
        """
        Get queue metrics including counts and SLA statistics.

        Args:
            tier: Optional tier filter

        Returns:
            Dict with queue metrics
        """
        # Base query for open cases
        open_statuses = [
            CaseStatus.OPEN,
            CaseStatus.ASSIGNED,
            CaseStatus.PENDING_INFORMATION,
            CaseStatus.ESCALATED,
            CaseStatus.PENDING_APPROVAL
        ]

        base_query = self.db.query(Case).filter(
            Case.status.in_(open_statuses)
        )

        if tier:
            base_query = base_query.filter(Case.tier == tier)

        # Total counts
        total_open = base_query.count()

        total_unassigned = base_query.filter(
            Case.assigned_to_id.is_(None)
        ).count()

        total_assigned = base_query.filter(
            Case.assigned_to_id.isnot(None)
        ).count()

        total_pending_info = self.db.query(Case).filter(
            Case.status == CaseStatus.PENDING_INFORMATION
        ).count()

        # By tier counts
        by_tier = {}
        for t in CaseTier:
            count = base_query.filter(Case.tier == t).count()
            by_tier[t.value] = count

        # By type counts
        by_type = {}
        for ct in CaseType:
            count = base_query.filter(Case.case_type == ct).count()
            if count > 0:
                by_type[ct.value] = count

        # SLA statistics
        sla_stats = self._calculate_sla_stats(base_query)

        return {
            "totalOpen": total_open,
            "totalUnassigned": total_unassigned,
            "totalAssigned": total_assigned,
            "totalPendingInfo": total_pending_info,
            "byTier": by_tier,
            "byType": by_type,
            "slaStats": sla_stats,
            "asOf": datetime.utcnow().isoformat()
        }

    def _calculate_sla_indicator(self, case: Case) -> SLAIndicator:
        """
        Calculate SLA indicator for a case.

        Args:
            case: Case to calculate indicator for

        Returns:
            SLA indicator enum value
        """
        if case.sla_deadline is None:
            return SLAIndicator.NO_SLA

        if case.sla_paused:
            return SLAIndicator.PAUSED

        if case.sla_breach:
            return SLAIndicator.BREACHED

        current_time = datetime.utcnow()

        # Check if breached
        if self.sla_calculator.is_breached(case.sla_deadline, current_time):
            return SLAIndicator.BREACHED

        # Check if approaching
        if self.sla_calculator.is_approaching_breach(
            case.created_at, case.sla_deadline, current_time
        ):
            return SLAIndicator.WARNING

        return SLAIndicator.ON_TRACK

    def _calculate_sla_stats(self, base_query) -> dict:
        """
        Calculate SLA statistics for a set of cases.

        Args:
            base_query: SQLAlchemy query to calculate stats for

        Returns:
            Dict with SLA stats
        """
        cases = base_query.filter(
            Case.sla_deadline.isnot(None)
        ).all()

        on_track = 0
        warning = 0
        breached = 0
        paused = 0

        for case in cases:
            indicator = self._calculate_sla_indicator(case)
            if indicator == SLAIndicator.ON_TRACK:
                on_track += 1
            elif indicator == SLAIndicator.WARNING:
                warning += 1
            elif indicator == SLAIndicator.BREACHED:
                breached += 1
            elif indicator == SLAIndicator.PAUSED:
                paused += 1

        return {
            "onTrack": on_track,
            "warning": warning,
            "breached": breached,
            "paused": paused
        }

    def compute_etag(self, user_id: UUID) -> str:
        """
        Compute ETag for user's dashboard data.

        Used for 30-second polling optimization (D6).

        Args:
            user_id: User ID

        Returns:
            ETag string
        """
        import hashlib

        # Get latest update timestamp for user's cases
        latest_update = self.db.query(func.max(Case.updated_at)).filter(
            Case.assigned_to_id == user_id
        ).scalar()

        # Get count of assigned cases
        count = self.db.query(Case).filter(
            Case.assigned_to_id == user_id
        ).count()

        # Combine into ETag
        data = f"{user_id}:{count}:{latest_update}"
        return hashlib.md5(data.encode()).hexdigest()
