"""
Reports API endpoints for analytics and data export.

References:
- US-10: Read-only reports access
- FR-064: Read-only role enforcement
- FR-070: Case volume reports
- FR-071: SMR metrics reports
- FR-072: Data export capability
- FR-073: Aged cases report
"""

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.db.session import get_db
from src.middleware.auth import CurrentUser, get_current_user
from src.models.case import CaseType, CaseStatus, CaseTier
from src.services.report_service import ReportService
from src.services.export_service import ExportService


router = APIRouter(prefix="/reports", tags=["reports"])


# Response schemas

class TrendItem(BaseModel):
    """Daily trend data point."""
    date: str
    count: int


class VolumeReportResponse(BaseModel):
    """Case volume report response."""
    total: int
    byType: dict
    byStatus: dict
    byTier: dict
    trend: list[TrendItem]
    periodStart: str
    periodEnd: str
    generatedAt: str


class GroupStats(BaseModel):
    """Statistics for a group."""
    total: int
    breached: int
    complianceRate: float


class SLAComplianceResponse(BaseModel):
    """SLA compliance report response."""
    totalCases: int
    onTrack: int
    breached: int
    complianceRate: float
    periodStart: str
    periodEnd: str
    generatedAt: str
    byGroup: Optional[dict] = None


class SMRMetricsResponse(BaseModel):
    """SMR metrics report response."""
    totalRecommendations: int
    totalApproved: int
    totalRejected: int
    totalPending: int
    totalFiled: int
    averageApprovalTime: Optional[float]
    periodStart: str
    periodEnd: str
    generatedAt: str


class AgeBucket(BaseModel):
    """Age bucket data."""
    label: str
    count: int


class AgedCasesResponse(BaseModel):
    """Aged cases report response."""
    totalOpenCases: int
    buckets: list[AgeBucket]
    tier: Optional[str]
    generatedAt: str


# Endpoints

@router.get(
    "/volumes",
    response_model=VolumeReportResponse,
    summary="Get case volume report"
)
async def get_volume_report(
    startDate: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    endDate: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Get case volume report with breakdown by type, status, and tier (FR-070).

    Accessible by all authenticated users.
    """
    service = ReportService(db)

    start = _parse_date(startDate)
    end = _parse_date(endDate)

    data = service.get_volume_report(start_date=start, end_date=end)

    return VolumeReportResponse(
        total=data["total"],
        byType=data["byType"],
        byStatus=data["byStatus"],
        byTier=data["byTier"],
        trend=[TrendItem(date=t["date"], count=t["count"]) for t in data["trend"]],
        periodStart=data["periodStart"],
        periodEnd=data["periodEnd"],
        generatedAt=data["generatedAt"]
    )


@router.get(
    "/sla-compliance",
    response_model=SLAComplianceResponse,
    summary="Get SLA compliance report"
)
async def get_sla_compliance_report(
    startDate: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    endDate: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    groupBy: Optional[str] = Query(None, description="Group by: caseType, tier"),
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Get SLA compliance report showing breach rates (FR-070).

    Can be grouped by case type or tier for detailed analysis.
    """
    service = ReportService(db)

    start = _parse_date(startDate)
    end = _parse_date(endDate)

    data = service.get_sla_compliance_report(
        start_date=start,
        end_date=end,
        group_by=groupBy
    )

    return SLAComplianceResponse(
        totalCases=data["totalCases"],
        onTrack=data["onTrack"],
        breached=data["breached"],
        complianceRate=data["complianceRate"],
        periodStart=data["periodStart"],
        periodEnd=data["periodEnd"],
        generatedAt=data["generatedAt"],
        byGroup=data.get("byGroup")
    )


@router.get(
    "/smr-metrics",
    response_model=SMRMetricsResponse,
    summary="Get SMR metrics report"
)
async def get_smr_metrics_report(
    startDate: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    endDate: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Get SMR metrics report showing recommendation and approval statistics (FR-071).
    """
    service = ReportService(db)

    start = _parse_date(startDate)
    end = _parse_date(endDate)

    data = service.get_smr_metrics_report(start_date=start, end_date=end)

    return SMRMetricsResponse(
        totalRecommendations=data["totalRecommendations"],
        totalApproved=data["totalApproved"],
        totalRejected=data["totalRejected"],
        totalPending=data["totalPending"],
        totalFiled=data["totalFiled"],
        averageApprovalTime=data["averageApprovalTime"],
        periodStart=data["periodStart"],
        periodEnd=data["periodEnd"],
        generatedAt=data["generatedAt"]
    )


@router.get(
    "/aged-cases",
    response_model=AgedCasesResponse,
    summary="Get aged cases report"
)
async def get_aged_cases_report(
    tier: Optional[str] = Query(None, description="Filter by tier (L1/L2)"),
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Get aged cases report showing open cases grouped by age buckets (FR-073).

    Helps identify cases that have been open for extended periods.
    """
    service = ReportService(db)

    parsed_tier = None
    if tier:
        try:
            parsed_tier = CaseTier(tier)
        except ValueError:
            pass

    data = service.get_aged_cases_report(tier=parsed_tier)

    return AgedCasesResponse(
        totalOpenCases=data["totalOpenCases"],
        buckets=[AgeBucket(label=b["label"], count=b["count"]) for b in data["buckets"]],
        tier=data["tier"],
        generatedAt=data["generatedAt"]
    )


@router.get(
    "/export",
    summary="Export case data"
)
async def export_data(
    format: str = Query("csv", description="Export format: csv, xlsx"),
    startDate: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    endDate: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    caseType: Optional[str] = Query(None, description="Filter by case type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Export case data to CSV or Excel format (FR-072).

    Returns a downloadable file with case information.
    """
    service = ExportService(db)

    start = _parse_date(startDate)
    end = _parse_date(endDate)

    parsed_type = None
    if caseType:
        try:
            parsed_type = CaseType(caseType)
        except ValueError:
            pass

    parsed_status = None
    if status:
        try:
            parsed_status = CaseStatus(status)
        except ValueError:
            pass

    if format.lower() == "xlsx":
        content = service.export_cases_excel(
            start_date=start,
            end_date=end,
            case_type=parsed_type,
            status=parsed_status
        )
        filename = service.get_export_filename("xlsx")
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content = service.export_cases_csv(
            start_date=start,
            end_date=end,
            case_type=parsed_type,
            status=parsed_status
        )
        filename = service.get_export_filename("csv")
        media_type = "text/csv"

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


# Helper functions

def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse date string to date object."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None
