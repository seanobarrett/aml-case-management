"""
Case management API endpoints.

References:
- FR-024: Cases filtered by status
- FR-025: Cases ordered by SLA priority
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from fastapi import Request

from src.middleware.auth import CurrentUser, get_current_user, TierMismatchError
from src.models.case import Case, CaseStatus, CaseTier, CaseType
from src.services.case_service import CaseService, CaseNotFoundError
from src.services.audit_service import AuditService
from src.db.session import get_db


router = APIRouter(prefix="/cases", tags=["cases"])


# Response schemas

class CustomerResponse(BaseModel):
    """Customer data in case response."""
    id: str
    externalCustomerId: str
    firstName: str | None
    lastName: str | None
    email: str | None
    accountClosed: bool


class TimelineEntryResponse(BaseModel):
    """Timeline entry in case response."""
    id: str
    entryType: str
    content: str
    actingUserId: str | None
    createdAt: str


class CaseListItem(BaseModel):
    """Case item in list response."""
    id: str
    caseReference: str
    caseType: str
    status: str
    tier: str
    customerId: str
    customerName: str | None
    assignedToId: str | None
    slaDeadline: str | None
    slaBreach: bool
    createdAt: str


class CaseListResponse(BaseModel):
    """Paginated case list response."""
    items: list[CaseListItem]
    total: int
    page: int
    pageSize: int


class SLAStatusResponse(BaseModel):
    """SLA status details."""
    deadline: str | None
    isPaused: bool
    pausedAt: str | None
    isBreached: bool
    breachedAt: str | None
    warningsSent: bool
    warningsSentAt: str | None


class LinkedCaseInfo(BaseModel):
    """Linked case information for bidirectional navigation."""
    linkId: str
    caseId: str
    caseReference: str
    caseType: str
    status: str
    linkType: str
    description: str | None
    isPrimary: bool
    createdAt: str | None


class OriginalCaseLinkInfo(BaseModel):
    """Info about original case for supplementary cases."""
    originalCaseId: str


class CaseDetailResponse(BaseModel):
    """Detailed case response."""
    id: str
    caseReference: str
    caseType: str
    status: str
    tier: str
    l2ReviewStatus: str
    customer: CustomerResponse
    assignedToId: str | None
    slaDeadline: str | None
    slaBreach: bool
    slaStatus: SLAStatusResponse | None
    closureReason: str | None
    closureDocumentation: str | None
    closedAt: str | None
    createdAt: str
    updatedAt: str
    version: int
    timeline: list[TimelineEntryResponse]
    linkedCases: list[LinkedCaseInfo] | None = None
    linkedTo: OriginalCaseLinkInfo | None = None
    alertTypes: list[str] | None = None


class ClaimCaseRequest(BaseModel):
    """Request to claim a case."""
    pass  # No body required for claim


class CloseCaseRequest(BaseModel):
    """Request to close a case."""
    reason: str = Field(..., min_length=10, description="Closure reason")
    documentation: str = Field(..., min_length=20, description="Supporting documentation")


class CaseResponse(BaseModel):
    """Basic case response after mutation."""
    id: str
    caseReference: str
    status: str
    message: str


class RequestInformationRequest(BaseModel):
    """Request to send information request to customer."""
    templateId: str = Field(..., description="Communication template ID")
    customMessage: str = Field(..., min_length=10, description="Custom message content")
    method: str = Field("EMAIL", description="Communication method")


class RecordResponseRequest(BaseModel):
    """Request to record customer response."""
    responseMethod: str = Field(..., description="How response was received")
    responseSummary: str = Field(..., min_length=10, description="Summary of response")
    receivedAt: str = Field(..., description="When response was received")


class EscalateRequest(BaseModel):
    """Request to escalate case to L2."""
    reason: str = Field(..., min_length=10, description="Reason for escalation")
    findings: str = Field(..., min_length=10, description="Initial investigation findings")


# Endpoints

@router.get(
    "",
    response_model=CaseListResponse,
    summary="List cases with filtering and pagination"
)
async def list_cases(
    status: Optional[str] = Query(None, description="Filter by status"),
    tier: Optional[str] = Query(None, description="Filter by tier (L1/L2)"),
    sort: str = Query("slaDeadline", description="Sort field"),
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(20, ge=1, le=100, description="Items per page"),
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    List cases with optional filtering and pagination.

    Cases are ordered by SLA deadline by default (FR-025).
    Supports filtering by status and tier (FR-024).
    """
    service = CaseService(db)

    # Parse status filter
    status_filter = None
    if status:
        try:
            status_filter = CaseStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status}"
            )

    # Parse tier filter
    tier_filter = None
    if tier:
        try:
            tier_filter = CaseTier(tier)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier: {tier}"
            )

    cases, total = service.list_cases(
        status=status_filter,
        tier=tier_filter,
        page=page,
        page_size=pageSize,
        sort_by=sort
    )

    return CaseListResponse(
        items=[
            CaseListItem(
                id=str(case.id),
                caseReference=case.case_reference,
                caseType=case.case_type.value,
                status=case.status.value,
                tier=case.tier.value,
                customerId=str(case.customer_id),
                customerName=case.customer.full_name if case.customer else None,
                assignedToId=str(case.assigned_to_id) if case.assigned_to_id else None,
                slaDeadline=case.sla_deadline.isoformat() if case.sla_deadline else None,
                slaBreach=case.sla_breach,
                createdAt=case.created_at.isoformat()
            )
            for case in cases
        ],
        total=total,
        page=page,
        pageSize=pageSize
    )


@router.get(
    "/{case_id}",
    response_model=CaseDetailResponse,
    summary="Get case details by ID"
)
async def get_case(
    case_id: UUID,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Get detailed case information by ID.

    Includes customer snapshot and timeline entries.
    Logs case view event for audit (FR-059).
    """
    case_service = CaseService(db)
    audit_service = AuditService(db)

    case = case_service.get_case_by_id(case_id)

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case not found: {case_id}"
        )

    # Log case view event (FR-059)
    ip_address = request.headers.get("x-forwarded-for", request.client.host if request.client else None)
    user_agent = request.headers.get("user-agent")
    audit_service.log_case_viewed(
        case_id=case_id,
        user_id=user.user_id,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.commit()

    # Build customer response
    customer = CustomerResponse(
        id=str(case.customer.id),
        externalCustomerId=case.customer.external_customer_id,
        firstName=case.customer.first_name,
        lastName=case.customer.last_name,
        email=case.customer.email,
        accountClosed=case.customer.account_closed
    )

    # Get timeline entries
    timeline_entries = audit_service.get_case_timeline(case_id)
    timeline = [
        TimelineEntryResponse(
            id=str(entry.id),
            entryType=entry.entry_type,
            content=entry.content,
            actingUserId=str(entry.acting_user_id) if entry.acting_user_id else None,
            createdAt=entry.created_at.isoformat()
        )
        for entry in timeline_entries
    ]

    # Build SLA status response
    sla_status = SLAStatusResponse(
        deadline=case.sla_deadline.isoformat() if case.sla_deadline else None,
        isPaused=case.sla_paused,
        pausedAt=case.sla_pause_start.isoformat() if case.sla_pause_start else None,
        isBreached=case.sla_breach,
        breachedAt=case.sla_breach_at.isoformat() if case.sla_breach_at else None,
        warningsSent=case.sla_warning_sent,
        warningsSentAt=case.sla_warning_sent_at.isoformat() if case.sla_warning_sent_at else None
    )

    # Get linked cases for bidirectional navigation (FR-046)
    from src.services.case_link_service import CaseLinkService
    from src.models.case import CaseType

    link_service = CaseLinkService(db)
    linked_cases_data = link_service.get_linked_cases(case_id)

    linked_cases = [
        LinkedCaseInfo(
            linkId=lc["linkId"],
            caseId=lc["caseId"],
            caseReference=lc["caseReference"],
            caseType=lc["caseType"],
            status=lc["status"],
            linkType="SUPPLEMENTARY" if lc["linkType"] == "SUPPLEMENTARY_TO_ORIGINAL" else lc["linkType"],
            description=lc["description"],
            isPrimary=lc["isPrimary"],
            createdAt=lc["createdAt"]
        )
        for lc in linked_cases_data
    ] if linked_cases_data else None

    # For supplementary cases, include link to original
    linked_to = None
    if case.case_type == CaseType.SMR_SUPPLEMENTARY and case.original_case_id:
        linked_to = OriginalCaseLinkInfo(originalCaseId=str(case.original_case_id))

    return CaseDetailResponse(
        id=str(case.id),
        caseReference=case.case_reference,
        caseType=case.case_type.value,
        status=case.status.value,
        tier=case.tier.value,
        l2ReviewStatus=case.l2_review_status.value,
        customer=customer,
        assignedToId=str(case.assigned_to_id) if case.assigned_to_id else None,
        slaDeadline=case.sla_deadline.isoformat() if case.sla_deadline else None,
        slaBreach=case.sla_breach,
        slaStatus=sla_status,
        closureReason=case.closure_reason,
        closureDocumentation=case.closure_documentation,
        closedAt=case.closed_at.isoformat() if case.closed_at else None,
        createdAt=case.created_at.isoformat(),
        updatedAt=case.updated_at.isoformat(),
        version=case.version,
        timeline=timeline,
        linkedCases=linked_cases,
        linkedTo=linked_to,
        alertTypes=case.alert_types
    )


@router.post(
    "/{case_id}/claim",
    response_model=CaseResponse,
    summary="Claim a case"
)
async def claim_case(
    case_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Claim a case for the authenticated analyst.

    The case will be assigned to the user and status changed to ASSIGNED.
    """
    if not user.has_permission("can_claim_cases"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to claim cases"
        )

    service = CaseService(db)

    try:
        case = service.claim_case(case_id, user.user_id)
        return CaseResponse(
            id=str(case.id),
            caseReference=case.case_reference,
            status=case.status.value,
            message=f"Case {case.case_reference} claimed successfully"
        )
    except CaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case not found: {case_id}"
        )


@router.post(
    "/{case_id}/close",
    response_model=CaseResponse,
    summary="Close a case"
)
async def close_case(
    case_id: UUID,
    request: CloseCaseRequest,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Close a case with documented justification.

    L1 analysts can only close L1 tier cases.
    L2 and Managers can close any tier.
    Returns TIER_MISMATCH error (403) if L1 tries to close L2 case.
    Supplementary cases require completed SMR workflow (FR-045).
    """
    service = CaseService(db)

    # Check if supplementary case requires SMR (FR-045)
    case_to_close = service.get_case_by_id(case_id)
    if case_to_close and case_to_close.case_type == CaseType.SMR_SUPPLEMENTARY:
        from src.services.smr_service import SMRService
        smr_service = SMRService(db)
        smr_recommendations = smr_service.get_case_recommendations(case_id)
        # Check if any SMR is filed
        has_filed_smr = any(smr.status.value == "FILED" for smr in smr_recommendations)
        if not has_filed_smr:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supplementary SMR cases require completed SMR workflow before closure"
            )

    try:
        case = service.close_case(
            case_id=case_id,
            user_id=user.user_id,
            user_role=user.role.value,
            reason=request.reason,
            documentation=request.documentation
        )
        return CaseResponse(
            id=str(case.id),
            caseReference=case.case_reference,
            status=case.status.value,
            message=f"Case {case.case_reference} closed successfully"
        )
    except CaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case not found: {case_id}"
        )
    except TierMismatchError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.detail
        )


@router.post(
    "/{case_id}/request-information",
    response_model=CaseResponse,
    summary="Request information from customer"
)
async def request_information(
    case_id: UUID,
    request: RequestInformationRequest,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Send an information request to customer using a template.

    Updates case status to PENDING_INFORMATION (FR-053).
    SLA timer is paused while awaiting response (FR-055).
    """
    from src.services.communication_service import CommunicationService
    from src.services.sla_service import SLAService
    from src.models.customer_communication import CommunicationMethod

    service = CommunicationService(db)
    sla_service = SLAService(db)

    try:
        method = CommunicationMethod(request.method.upper())
    except ValueError:
        method = CommunicationMethod.EMAIL

    try:
        communication = service.request_information(
            case_id=case_id,
            user_id=user.user_id,
            template_id=request.templateId,
            custom_message=request.customMessage,
            method=method
        )

        # Get updated case for response
        case = db.query(Case).filter(Case.id == case_id).first()

        # Pause SLA timer (FR-055)
        sla_service.pause_sla(case, reason="Awaiting customer information")
        db.commit()

        return CaseResponse(
            id=str(case.id),
            caseReference=case.case_reference,
            status=case.status.value,
            message=f"Information request sent for case {case.case_reference}. SLA timer paused."
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{case_id}/record-response",
    response_model=CaseResponse,
    summary="Record customer response"
)
async def record_response(
    case_id: UUID,
    request: RecordResponseRequest,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Record a customer response to an information request.

    Updates case status back to ASSIGNED (FR-056).
    SLA timer resumes with adjusted deadline.
    """
    from datetime import datetime
    from src.services.communication_service import CommunicationService
    from src.services.sla_service import SLAService
    from src.models.customer_communication import CommunicationMethod

    service = CommunicationService(db)
    sla_service = SLAService(db)

    try:
        method = CommunicationMethod(request.responseMethod.upper())
    except ValueError:
        method = CommunicationMethod.OTHER

    try:
        received_at = datetime.fromisoformat(request.receivedAt.replace("Z", "+00:00"))
    except ValueError:
        received_at = datetime.utcnow()

    try:
        communication = service.record_response(
            case_id=case_id,
            user_id=user.user_id,
            response_method=method,
            response_summary=request.responseSummary,
            received_at=received_at
        )

        # Get updated case for response
        case = db.query(Case).filter(Case.id == case_id).first()

        # Resume SLA timer with adjusted deadline
        new_deadline = sla_service.resume_sla(case)
        db.commit()

        deadline_msg = ""
        if new_deadline:
            deadline_msg = f" SLA deadline adjusted to {new_deadline.isoformat()}."

        return CaseResponse(
            id=str(case.id),
            caseReference=case.case_reference,
            status=case.status.value,
            message=f"Customer response recorded for case {case.case_reference}.{deadline_msg}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{case_id}/escalate",
    response_model=CaseResponse,
    summary="Escalate case to L2"
)
async def escalate_case(
    case_id: UUID,
    request: EscalateRequest,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Escalate a case from L1 to L2.

    Changes case tier to L2 and status to ESCALATED (FR-013).
    Unassigns the case so it appears in the L2 queue.
    """
    service = CaseService(db)

    try:
        case = service.escalate_case(
            case_id=case_id,
            user_id=user.user_id,
            reason=request.reason,
            findings=request.findings
        )

        return CaseResponse(
            id=str(case.id),
            caseReference=case.case_reference,
            status=case.status.value,
            message=f"Case {case.case_reference} escalated to L2"
        )
    except CaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case not found: {case_id}"
        )


# Linked cases response schemas

class LinkedCaseItem(BaseModel):
    """Linked case item."""
    linkId: str
    caseId: str
    caseReference: str
    caseType: str
    status: str
    linkType: str
    description: str | None
    isPrimary: bool
    createdAt: str | None


class LinkedCasesResponse(BaseModel):
    """Response for linked cases."""
    caseId: str
    caseReference: str
    linkedCases: list[LinkedCaseItem]


class OnboardingBlockResponse(BaseModel):
    """Response for onboarding block status."""
    caseId: str
    customerId: str
    isBlocked: bool
    blockedAt: str | None
    clearedAt: str | None
    syncStatus: str
    reason: str | None


@router.get(
    "/{case_id}/linked-cases",
    response_model=LinkedCasesResponse,
    summary="Get linked cases"
)
async def get_linked_cases(
    case_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Get all cases linked to this case (EC-014, FR-046).

    Returns bidirectional links including:
    - New alerts for same customer
    - Supplementary SMR cases
    """
    from src.services.case_link_service import CaseLinkService

    case_service = CaseService(db)
    link_service = CaseLinkService(db)

    case = case_service.get_case_by_id(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case not found: {case_id}"
        )

    linked_cases = link_service.get_linked_cases(case_id)

    return LinkedCasesResponse(
        caseId=str(case.id),
        caseReference=case.case_reference,
        linkedCases=[
            LinkedCaseItem(
                linkId=lc["linkId"],
                caseId=lc["caseId"],
                caseReference=lc["caseReference"],
                caseType=lc["caseType"],
                status=lc["status"],
                linkType=lc["linkType"],
                description=lc["description"],
                isPrimary=lc["isPrimary"],
                createdAt=lc["createdAt"]
            )
            for lc in linked_cases
        ]
    )


@router.get(
    "/{case_id}/onboarding-block",
    response_model=OnboardingBlockResponse,
    summary="Get onboarding block status"
)
async def get_onboarding_block(
    case_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Get onboarding block status for a case (FR-028, FR-029).

    Returns block details including sync status with Spriggy.
    """
    from src.services.onboarding_block_service import OnboardingBlockService

    case_service = CaseService(db)
    block_service = OnboardingBlockService(db)

    case = case_service.get_case_by_id(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case not found: {case_id}"
        )

    block = block_service.get_block_for_case(case_id)

    if not block:
        return OnboardingBlockResponse(
            caseId=str(case.id),
            customerId=case.customer.external_customer_id if case.customer else "",
            isBlocked=False,
            blockedAt=None,
            clearedAt=None,
            syncStatus="NONE",
            reason=None
        )

    return OnboardingBlockResponse(
        caseId=str(case.id),
        customerId=block.customer_id,
        isBlocked=block.is_active,
        blockedAt=block.blocked_at.isoformat() if block.blocked_at else None,
        clearedAt=block.cleared_at.isoformat() if block.cleared_at else None,
        syncStatus=block.sync_status.value,
        reason=block.reason.value if block.reason else None
    )


# Account restriction recommendation schemas and endpoint

class RecommendRestrictionRequest(BaseModel):
    """Request to recommend account restriction."""
    restrictionType: str = Field(..., description="Type: FULL, PARTIAL, ENHANCED_MONITORING, NONE")
    reason: str = Field(..., min_length=10, description="Justification for restriction")
    effectiveImmediately: bool = Field(False, description="Whether to implement immediately")


class RestrictionResponse(BaseModel):
    """Response for restriction recommendation."""
    id: str
    caseId: str
    customerId: str
    restrictionType: str
    status: str
    reason: str
    effectiveImmediately: bool
    recommendedAt: str


@router.post(
    "/{case_id}/recommend-restriction",
    response_model=RestrictionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Recommend account restriction for existing customer"
)
async def recommend_restriction(
    case_id: UUID,
    request: RecommendRestrictionRequest,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Recommend account restriction for existing customer sanctions case (FR-038).

    Used when an existing customer has a sanctions match and the analyst
    recommends restricting their account access.
    """
    from src.models.account_restriction import AccountRestriction, RestrictionType
    from src.models.case import CaseType

    case_service = CaseService(db)
    case = case_service.get_case_by_id(case_id)

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case not found: {case_id}"
        )

    # Validate restriction type
    try:
        restriction_type = RestrictionType(request.restrictionType)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid restriction type: {request.restrictionType}"
        )

    # Create restriction recommendation
    restriction = AccountRestriction.create(
        case_id=case_id,
        customer_id=case.customer.external_customer_id if case.customer else "",
        restriction_type=restriction_type,
        reason=request.reason,
        recommended_by_id=user.user_id,
        effective_immediately=request.effectiveImmediately
    )

    db.add(restriction)
    db.commit()
    db.refresh(restriction)

    return RestrictionResponse(
        id=str(restriction.id),
        caseId=str(restriction.case_id),
        customerId=restriction.customer_id,
        restrictionType=restriction.restriction_type.value,
        status=restriction.status.value,
        reason=restriction.reason,
        effectiveImmediately=restriction.effective_immediately,
        recommendedAt=restriction.recommended_at.isoformat()
    )


# Supplementary SMR request/response schemas

class CreateSupplementaryRequest(BaseModel):
    """Request to create supplementary SMR case."""
    reason: str = Field(..., min_length=10, description="Reason for supplementary filing")
    newEvidence: str = Field(default="", description="New evidence discovered")


class LinkedCaseResponse(BaseModel):
    """Linked case information."""
    originalCaseId: str


class SupplementaryCaseResponse(BaseModel):
    """Response for supplementary case creation."""
    id: str
    caseReference: str
    caseType: str
    status: str
    tier: str
    customer: CustomerResponse
    linkedTo: LinkedCaseResponse
    createdAt: str


@router.post(
    "/{case_id}/create-supplementary",
    response_model=SupplementaryCaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create supplementary SMR case"
)
async def create_supplementary_case(
    case_id: UUID,
    request: CreateSupplementaryRequest,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Create a supplementary SMR case linked to an original case (FR-044).

    Supplementary cases:
    - Can only be created from closed cases with filed SMRs
    - Inherit customer information from original
    - Follow full SMR workflow (FR-045)
    - Support multiple supplementary filings per original (FR-047)

    Requires: L2 Analyst or Manager role.
    """
    from src.middleware.auth import require_permission

    # Require L2 or manager permission
    if user.tier not in ["L2", None] and user.role not in ["L2_ANALYST", "AML_MANAGER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only L2 analysts or managers can create supplementary cases"
        )

    case_service = CaseService(db)

    try:
        supplementary_case = case_service.create_supplementary_case(
            original_case_id=case_id,
            reason=request.reason,
            new_evidence=request.newEvidence,
            created_by_id=user.user_id
        )
    except CaseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case not found: {case_id}"
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return SupplementaryCaseResponse(
        id=str(supplementary_case.id),
        caseReference=supplementary_case.case_reference,
        caseType=supplementary_case.case_type.value,
        status=supplementary_case.status.value,
        tier=supplementary_case.tier.value,
        customer=CustomerResponse(
            id=str(supplementary_case.customer.id) if supplementary_case.customer else "",
            externalCustomerId=supplementary_case.customer.external_customer_id if supplementary_case.customer else "",
            firstName=supplementary_case.customer.first_name if supplementary_case.customer else None,
            lastName=supplementary_case.customer.last_name if supplementary_case.customer else None,
            email=supplementary_case.customer.email if supplementary_case.customer else None,
            accountClosed=supplementary_case.customer.account_closed if supplementary_case.customer else False
        ),
        linkedTo=LinkedCaseResponse(
            originalCaseId=str(case_id)
        ),
        createdAt=supplementary_case.created_at.isoformat()
    )
