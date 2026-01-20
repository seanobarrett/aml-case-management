"""
Dashboard API endpoints for case prioritization and queue metrics.

References:
- US-12: Dashboard with prioritized work queue
- FR-024: Cases filtered by status
- FR-025: Cases ordered by SLA priority
- D6: 30-second polling support
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response, status
from pydantic import BaseModel

from src.db.session import get_db
from src.middleware.auth import CurrentUser, get_current_user
from src.models.case import CaseStatus, CaseType, CaseTier
from src.services.dashboard_service import DashboardService


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# Response schemas

class DashboardCaseItem(BaseModel):
    """Case item for dashboard display."""
    id: str
    caseReference: str
    caseType: str
    status: str
    tier: str
    customerId: str
    customerName: str | None
    assignedToId: str | None
    slaDeadline: str | None
    slaIndicator: str
    slaBreach: bool
    slaPaused: bool
    createdAt: str


class MyCasesResponse(BaseModel):
    """Response for my-cases endpoint."""
    items: list[DashboardCaseItem]
    total: int
    page: int
    pageSize: int


class SLAStats(BaseModel):
    """SLA statistics."""
    onTrack: int
    warning: int
    breached: int
    paused: int


class TierCounts(BaseModel):
    """Counts by tier."""
    L1: int
    L2: int


class QueueMetricsResponse(BaseModel):
    """Response for queue-metrics endpoint."""
    totalOpen: int
    totalUnassigned: int
    totalAssigned: int
    totalPendingInfo: int
    byTier: dict
    byType: dict
    slaStats: SLAStats
    asOf: str


# Endpoints

@router.get(
    "/my-cases",
    response_model=MyCasesResponse,
    summary="Get analyst's assigned cases with SLA indicators"
)
async def get_my_cases(
    request: Request,
    response: Response,
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    case_type: Optional[str] = Query(None, alias="caseType", description="Filter by case type"),
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(20, ge=1, le=100, description="Items per page"),
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Get cases assigned to the authenticated analyst.

    Cases are ordered by SLA priority (FR-025):
    - Breached cases appear first
    - Then sorted by SLA deadline ascending

    Supports 30-second polling with ETag (D6):
    - Response includes ETag header
    - Send If-None-Match header to check for changes
    - Returns 304 if unchanged
    """
    service = DashboardService(db)

    # Check for ETag-based caching (D6)
    etag = service.compute_etag(user.user_id)
    if_none_match = request.headers.get("If-None-Match")

    if if_none_match and if_none_match == etag:
        response.status_code = status.HTTP_304_NOT_MODIFIED
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)

    # Parse filters
    parsed_status = None
    if status_filter:
        try:
            parsed_status = CaseStatus(status_filter)
        except ValueError:
            pass

    parsed_type = None
    if case_type:
        try:
            parsed_type = CaseType(case_type)
        except ValueError:
            pass

    cases, total = service.get_my_cases(
        user_id=user.user_id,
        status=parsed_status,
        case_type=parsed_type,
        page=page,
        page_size=pageSize
    )

    # Set caching headers for polling support (D6)
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "private, max-age=30, must-revalidate"

    return MyCasesResponse(
        items=[
            DashboardCaseItem(
                id=c["id"],
                caseReference=c["caseReference"],
                caseType=c["caseType"],
                status=c["status"],
                tier=c["tier"],
                customerId=c["customerId"],
                customerName=c["customerName"],
                assignedToId=c["assignedToId"],
                slaDeadline=c["slaDeadline"],
                slaIndicator=c["slaIndicator"],
                slaBreach=c["slaBreach"],
                slaPaused=c["slaPaused"],
                createdAt=c["createdAt"]
            )
            for c in cases
        ],
        total=total,
        page=page,
        pageSize=pageSize
    )


@router.get(
    "/queue-metrics",
    response_model=QueueMetricsResponse,
    summary="Get queue metrics and SLA statistics"
)
async def get_queue_metrics(
    response: Response,
    tier: Optional[str] = Query(None, description="Filter by tier (L1/L2)"),
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Get queue metrics including:
    - Total counts by status
    - Breakdown by tier and case type
    - SLA statistics (on-track, warning, breached)

    Useful for team leads and managers to monitor workload.
    """
    service = DashboardService(db)

    # Parse tier filter
    parsed_tier = None
    if tier:
        try:
            parsed_tier = CaseTier(tier)
        except ValueError:
            pass

    metrics = service.get_queue_metrics(tier=parsed_tier)

    # Set caching headers for polling support (D6)
    response.headers["Cache-Control"] = "private, max-age=30, must-revalidate"

    return QueueMetricsResponse(
        totalOpen=metrics["totalOpen"],
        totalUnassigned=metrics["totalUnassigned"],
        totalAssigned=metrics["totalAssigned"],
        totalPendingInfo=metrics["totalPendingInfo"],
        byTier=metrics["byTier"],
        byType=metrics["byType"],
        slaStats=SLAStats(
            onTrack=metrics["slaStats"]["onTrack"],
            warning=metrics["slaStats"]["warning"],
            breached=metrics["slaStats"]["breached"],
            paused=metrics["slaStats"]["paused"]
        ),
        asOf=metrics["asOf"]
    )


@router.get(
    "/team-overview",
    summary="Get team workload overview for managers"
)
async def get_team_overview(
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Get team workload overview.

    Shows distribution of cases across team members.
    Restricted to managers and team leads.
    """
    from sqlalchemy import func
    from src.models.case import Case, CaseStatus
    from src.models.user import User

    # Get case counts by analyst
    open_statuses = [
        CaseStatus.OPEN,
        CaseStatus.ASSIGNED,
        CaseStatus.PENDING_INFORMATION,
        CaseStatus.ESCALATED,
        CaseStatus.PENDING_APPROVAL
    ]

    analyst_cases = (
        db.query(
            User.id,
            User.email,
            func.count(Case.id).label("case_count")
        )
        .join(Case, Case.assigned_to_id == User.id)
        .filter(Case.status.in_(open_statuses))
        .group_by(User.id, User.email)
        .all()
    )

    team_data = [
        {
            "userId": str(row[0]),
            "email": row[1],
            "caseCount": row[2]
        }
        for row in analyst_cases
    ]

    # Set caching headers
    response.headers["Cache-Control"] = "private, max-age=30, must-revalidate"

    return {
        "analysts": team_data,
        "totalAnalysts": len(team_data),
        "asOf": db.query(func.now()).scalar().isoformat()
    }
