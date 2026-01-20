"""
Report service for generating case analytics and metrics.

References:
- US-10: Read-only reports access
- FR-070: Case volume reports
- FR-071: SMR metrics reports
- FR-073: Aged cases report
"""

from datetime import datetime, date, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import func, case as sql_case
from sqlalchemy.orm import Session

from src.models.case import Case, CaseStatus, CaseType, CaseTier
from src.models.smr_recommendation import SMRRecommendation, SMRStatus


class ReportService:
    """
    Service for generating reports and analytics.
    """

    def __init__(self, db: Session):
        """
        Initialize report service.

        Args:
            db: Database session
        """
        self.db = db

    def get_volume_report(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> dict:
        """
        Get case volume report with breakdown by type, status, and tier.

        Args:
            start_date: Start of period (default: 30 days ago)
            end_date: End of period (default: today)

        Returns:
            Volume report data
        """
        if not start_date:
            start_date = datetime.utcnow().date() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow().date()

        # Base query for period
        base_query = self.db.query(Case).filter(
            func.date(Case.created_at) >= start_date,
            func.date(Case.created_at) <= end_date
        )

        # Total count
        total = base_query.count()

        # By type
        by_type = {}
        for case_type in CaseType:
            count = base_query.filter(Case.case_type == case_type).count()
            if count > 0:
                by_type[case_type.value] = count

        # By status
        by_status = {}
        for status in CaseStatus:
            count = base_query.filter(Case.status == status).count()
            if count > 0:
                by_status[status.value] = count

        # By tier
        by_tier = {}
        for tier in CaseTier:
            count = base_query.filter(Case.tier == tier).count()
            by_tier[tier.value] = count

        # Daily trend
        daily_counts = (
            self.db.query(
                func.date(Case.created_at).label("date"),
                func.count(Case.id).label("count")
            )
            .filter(
                func.date(Case.created_at) >= start_date,
                func.date(Case.created_at) <= end_date
            )
            .group_by(func.date(Case.created_at))
            .order_by(func.date(Case.created_at))
            .all()
        )

        trend = [
            {"date": str(row[0]), "count": row[1]}
            for row in daily_counts
        ]

        return {
            "total": total,
            "byType": by_type,
            "byStatus": by_status,
            "byTier": by_tier,
            "trend": trend,
            "periodStart": str(start_date),
            "periodEnd": str(end_date),
            "generatedAt": datetime.utcnow().isoformat()
        }

    def get_sla_compliance_report(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        group_by: Optional[str] = None
    ) -> dict:
        """
        Get SLA compliance report.

        Args:
            start_date: Start of period
            end_date: End of period
            group_by: Optional grouping (caseType, tier)

        Returns:
            SLA compliance data
        """
        if not start_date:
            start_date = datetime.utcnow().date() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow().date()

        # Base query - closed cases in period
        base_query = self.db.query(Case).filter(
            Case.status == CaseStatus.CLOSED,
            func.date(Case.closed_at) >= start_date,
            func.date(Case.closed_at) <= end_date
        )

        total_cases = base_query.count()
        breached_cases = base_query.filter(Case.sla_breach == True).count()
        on_track = total_cases - breached_cases

        compliance_rate = (on_track / total_cases * 100) if total_cases > 0 else 100.0

        result = {
            "totalCases": total_cases,
            "onTrack": on_track,
            "breached": breached_cases,
            "complianceRate": round(compliance_rate, 2),
            "periodStart": str(start_date),
            "periodEnd": str(end_date),
            "generatedAt": datetime.utcnow().isoformat()
        }

        # Grouping
        if group_by == "caseType":
            by_group = {}
            for case_type in CaseType:
                type_total = base_query.filter(Case.case_type == case_type).count()
                type_breached = base_query.filter(
                    Case.case_type == case_type,
                    Case.sla_breach == True
                ).count()
                if type_total > 0:
                    by_group[case_type.value] = {
                        "total": type_total,
                        "breached": type_breached,
                        "complianceRate": round((type_total - type_breached) / type_total * 100, 2)
                    }
            result["byGroup"] = by_group

        elif group_by == "tier":
            by_group = {}
            for tier in CaseTier:
                tier_total = base_query.filter(Case.tier == tier).count()
                tier_breached = base_query.filter(
                    Case.tier == tier,
                    Case.sla_breach == True
                ).count()
                if tier_total > 0:
                    by_group[tier.value] = {
                        "total": tier_total,
                        "breached": tier_breached,
                        "complianceRate": round((tier_total - tier_breached) / tier_total * 100, 2)
                    }
            result["byGroup"] = by_group

        return result

    def get_smr_metrics_report(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> dict:
        """
        Get SMR metrics report.

        Args:
            start_date: Start of period
            end_date: End of period

        Returns:
            SMR metrics data
        """
        if not start_date:
            start_date = datetime.utcnow().date() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow().date()

        # Base query
        base_query = self.db.query(SMRRecommendation).filter(
            func.date(SMRRecommendation.created_at) >= start_date,
            func.date(SMRRecommendation.created_at) <= end_date
        )

        total_recommendations = base_query.count()
        total_approved = base_query.filter(
            SMRRecommendation.status == SMRStatus.APPROVED
        ).count()
        total_rejected = base_query.filter(
            SMRRecommendation.status == SMRStatus.REJECTED
        ).count()
        total_pending = base_query.filter(
            SMRRecommendation.status == SMRStatus.PENDING
        ).count()
        total_filed = base_query.filter(
            SMRRecommendation.status == SMRStatus.FILED
        ).count()

        # Average approval time (for approved SMRs)
        approved_smrs = base_query.filter(
            SMRRecommendation.status.in_([SMRStatus.APPROVED, SMRStatus.FILED]),
            SMRRecommendation.approved_at.isnot(None)
        ).all()

        avg_approval_hours = None
        if approved_smrs:
            total_hours = sum(
                (smr.approved_at - smr.created_at).total_seconds() / 3600
                for smr in approved_smrs
            )
            avg_approval_hours = round(total_hours / len(approved_smrs), 1)

        return {
            "totalRecommendations": total_recommendations,
            "totalApproved": total_approved,
            "totalRejected": total_rejected,
            "totalPending": total_pending,
            "totalFiled": total_filed,
            "averageApprovalTime": avg_approval_hours,
            "periodStart": str(start_date),
            "periodEnd": str(end_date),
            "generatedAt": datetime.utcnow().isoformat()
        }

    def get_aged_cases_report(
        self,
        tier: Optional[CaseTier] = None
    ) -> dict:
        """
        Get aged cases report with age buckets.

        Args:
            tier: Optional tier filter

        Returns:
            Aged cases data
        """
        # Open cases only
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

        cases = base_query.all()

        # Age buckets
        now = datetime.utcnow()
        buckets = {
            "0-7 days": 0,
            "7-14 days": 0,
            "14-30 days": 0,
            "30-60 days": 0,
            "60+ days": 0
        }

        for case in cases:
            age_days = (now - case.created_at).days
            if age_days <= 7:
                buckets["0-7 days"] += 1
            elif age_days <= 14:
                buckets["7-14 days"] += 1
            elif age_days <= 30:
                buckets["14-30 days"] += 1
            elif age_days <= 60:
                buckets["30-60 days"] += 1
            else:
                buckets["60+ days"] += 1

        bucket_list = [
            {"label": label, "count": count}
            for label, count in buckets.items()
        ]

        return {
            "totalOpenCases": len(cases),
            "buckets": bucket_list,
            "tier": tier.value if tier else None,
            "generatedAt": datetime.utcnow().isoformat()
        }

    def get_cases_for_export(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        case_type: Optional[CaseType] = None,
        status: Optional[CaseStatus] = None
    ) -> list[dict]:
        """
        Get cases for export.

        Args:
            start_date: Start of period
            end_date: End of period
            case_type: Optional case type filter
            status: Optional status filter

        Returns:
            List of case data for export
        """
        query = self.db.query(Case)

        if start_date:
            query = query.filter(func.date(Case.created_at) >= start_date)
        if end_date:
            query = query.filter(func.date(Case.created_at) <= end_date)
        if case_type:
            query = query.filter(Case.case_type == case_type)
        if status:
            query = query.filter(Case.status == status)

        cases = query.order_by(Case.created_at.desc()).all()

        return [
            {
                "case_reference": case.case_reference,
                "case_type": case.case_type.value,
                "status": case.status.value,
                "tier": case.tier.value,
                "customer_id": case.customer.external_customer_id if case.customer else "",
                "customer_name": case.customer.full_name if case.customer else "",
                "assigned_to": case.assigned_to.email if case.assigned_to else "",
                "sla_deadline": case.sla_deadline.isoformat() if case.sla_deadline else "",
                "sla_breached": "Yes" if case.sla_breach else "No",
                "created_at": case.created_at.isoformat(),
                "closed_at": case.closed_at.isoformat() if case.closed_at else "",
                "closure_reason": case.closure_reason or ""
            }
            for case in cases
        ]
