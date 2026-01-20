"""
Queue management API endpoints.

References:
- D13: Manual claim from queue - cases enter unassigned queue; analysts self-select
- FR-024: Cases filtered by status
- FR-025: Cases ordered by SLA priority
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from src.middleware.auth import CurrentUser, get_current_user
from src.models.case import CaseStatus, CaseTier
from src.services.case_service import CaseService
from src.db.session import get_db


router = APIRouter(prefix="/queue", tags=["queue"])


# Response schemas

class QueueCaseItem(BaseModel):
    """Case item in queue response."""
    id: str
    caseReference: str
    caseType: str
    status: str
    tier: str
    customerId: str
    customerName: str | None
    slaDeadline: str | None
    slaBreached: bool
    createdAt: str
    ageInHours: float


class UnassignedQueueResponse(BaseModel):
    """Unassigned queue response."""
    items: list[QueueCaseItem]
    total: int
    page: int
    pageSize: int


class L2ReviewQueueResponse(BaseModel):
    """L2 review queue response."""
    items: list[QueueCaseItem]
    total: int


# Endpoints

@router.get(
    "/unassigned",
    response_model=UnassignedQueueResponse,
    summary="Get unassigned case queue"
)
async def get_unassigned_queue(
    tier: Optional[str] = Query(None, description="Filter by tier (L1/L2)"),
    caseType: Optional[str] = Query(None, description="Filter by case type"),
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(20, ge=1, le=100, description="Items per page"),
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Get unassigned cases ordered by SLA priority.

    Cases are sorted by SLA deadline (earliest first) per FR-025.
    Analysts use this queue to self-select cases (D13).
    """
    from datetime import datetime

    service = CaseService(db)

    # Parse tier filter
    tier_filter = None
    if tier:
        try:
            tier_filter = CaseTier(tier)
        except ValueError:
            pass

    # Get cases that are unassigned
    # Include OPEN cases and ESCALATED cases (escalated L2 cases are unassigned)
    statuses = [CaseStatus.OPEN, CaseStatus.ESCALATED]
    cases, total = service.list_cases(
        status_list=statuses,
        tier=tier_filter,
        unassigned_only=True,
        page=page,
        page_size=pageSize,
        sort_by="sla_deadline"
    )

    now = datetime.utcnow()

    return UnassignedQueueResponse(
        items=[
            QueueCaseItem(
                id=str(case.id),
                caseReference=case.case_reference,
                caseType=case.case_type.value,
                status=case.status.value,
                tier=case.tier.value,
                customerId=str(case.customer_id),
                customerName=case.customer.full_name if case.customer else None,
                slaDeadline=case.sla_deadline.isoformat() if case.sla_deadline else None,
                slaBreached=case.sla_breached,
                createdAt=case.created_at.isoformat(),
                ageInHours=(now - case.created_at).total_seconds() / 3600
            )
            for case in cases
        ],
        total=total,
        page=page,
        pageSize=pageSize
    )


@router.get(
    "/l2-review",
    response_model=L2ReviewQueueResponse,
    summary="Get L2 quality review queue"
)
async def get_l2_review_queue(
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Get cases pending L2 quality review.

    L1 closures flagged for review appear in this queue.
    L2 analysts can accept the closure or reopen the case.
    """
    from src.models.case import Case, L2ReviewStatus

    # Query cases pending L2 review
    query = db.query(Case).filter(
        Case.l2_review_status == L2ReviewStatus.PENDING_REVIEW
    ).order_by(Case.closed_at.asc())

    cases = query.all()

    from datetime import datetime
    now = datetime.utcnow()

    return L2ReviewQueueResponse(
        items=[
            QueueCaseItem(
                id=str(case.id),
                caseReference=case.case_reference,
                caseType=case.case_type.value,
                status=case.status.value,
                tier=case.tier.value,
                customerId=str(case.customer_id),
                customerName=case.customer.full_name if case.customer else None,
                slaDeadline=case.sla_deadline.isoformat() if case.sla_deadline else None,
                slaBreached=case.sla_breached,
                createdAt=case.created_at.isoformat(),
                ageInHours=(now - case.created_at).total_seconds() / 3600
            )
            for case in cases
        ],
        total=len(cases)
    )


class L2ReviewResponse(BaseModel):
    """Response after L2 review action."""
    caseId: str
    caseReference: str
    status: str
    l2ReviewStatus: str
    message: str


class ReopenRequest(BaseModel):
    """Request to reopen a case from L2 review."""
    reason: str


@router.post(
    "/l2-review/{case_id}/accept",
    response_model=L2ReviewResponse,
    summary="Accept L1 closure in L2 review"
)
async def accept_l2_review(
    case_id: str,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Accept an L1 closure during L2 quality review.

    Marks the closure as reviewed and accepted.
    """
    from uuid import UUID
    from src.services.case_queue_service import CaseQueueService
    from src.models.user import UserRole
    from fastapi import HTTPException, status

    # Check L2 or higher permission
    if user.role not in (UserRole.L2_ANALYST, UserRole.AML_MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only L2 analysts and managers can review L1 closures"
        )

    service = CaseQueueService(db)

    try:
        case = service.accept_l2_review(UUID(case_id), user.user_id)
        db.commit()

        return L2ReviewResponse(
            caseId=str(case.id),
            caseReference=case.case_reference,
            status=case.status.value,
            l2ReviewStatus=case.l2_review_status.value,
            message=f"L1 closure accepted for case {case.case_reference}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/l2-review/{case_id}/reopen",
    response_model=L2ReviewResponse,
    summary="Reopen case from L2 review"
)
async def reopen_from_l2_review(
    case_id: str,
    request: ReopenRequest,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Reopen a case from L2 quality review.

    Rejects the L1 closure and assigns the case to the L2 reviewer.
    """
    from uuid import UUID
    from src.services.case_queue_service import CaseQueueService
    from src.models.user import UserRole
    from fastapi import HTTPException, status

    # Check L2 or higher permission
    if user.role not in (UserRole.L2_ANALYST, UserRole.AML_MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only L2 analysts and managers can reopen cases from L2 review"
        )

    service = CaseQueueService(db)

    try:
        case = service.reopen_from_l2_review(
            UUID(case_id),
            user.user_id,
            request.reason
        )
        db.commit()

        return L2ReviewResponse(
            caseId=str(case.id),
            caseReference=case.case_reference,
            status=case.status.value,
            l2ReviewStatus=case.l2_review_status.value,
            message=f"Case {case.case_reference} reopened and assigned to you"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
