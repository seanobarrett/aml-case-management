"""
Webhook endpoints for GreenID and Indue integrations.

References:
- FR-001: System receives GreenID/Indue webhooks
- FR-002: System validates webhook payload schema
- D11: HMAC signature validation
- EC-005: Duplicate webhook handling
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from src.middleware.webhook_auth import verify_greenid_webhook, verify_indue_webhook
from src.services.case_service import CaseService, DuplicateWebhookError
from src.services.onboarding_block_service import OnboardingBlockService
from src.services.case_link_service import CaseLinkService
from src.db.session import get_db


router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# Request/Response schemas

class GreenIDCustomer(BaseModel):
    """Customer data from GreenID webhook."""
    firstName: str | None = None
    lastName: str | None = None
    email: str | None = None
    dateOfBirth: str | None = None


class GreenIDWebhookPayload(BaseModel):
    """GreenID webhook payload schema."""
    verificationId: str = Field(..., description="Unique verification ID")
    customerId: str = Field(..., description="Customer ID in Spriggy system")
    verificationType: str = Field(..., description="Type of verification")
    outcome: str = Field(..., description="Verification outcome")
    timestamp: str = Field(..., description="Event timestamp")
    customer: GreenIDCustomer | None = None


class IndueMatchDetails(BaseModel):
    """Match details from Indue screening."""
    name: str | None = None
    matchType: str | None = None
    category: str | None = None


class IndueWebhookPayload(BaseModel):
    """Indue webhook payload schema."""
    screeningId: str = Field(..., description="Unique screening ID")
    customerId: str = Field(..., description="Customer ID in Spriggy system")
    screeningType: str = Field(..., description="Type of screening (PEP/SANCTIONS)")
    matchScore: int | None = Field(None, description="Match confidence score")
    matchDetails: IndueMatchDetails | None = None
    timestamp: str = Field(..., description="Event timestamp")
    customerOnboardingStatus: str | None = Field(None, description="Current onboarding status")


class CaseCreatedResponse(BaseModel):
    """Response for case creation."""
    id: str
    caseReference: str
    caseType: str
    status: str
    tier: str
    customerId: str
    createdAt: str
    onboardingBlocked: bool = False
    alertTypes: list[str] | None = None
    linkedCaseIds: list[str] | None = None


class ErrorResponse(BaseModel):
    """Error response schema."""
    detail: str


class AccountClosureWebhookPayload(BaseModel):
    """Account closure webhook payload schema (EC-008)."""
    customerId: str
    closureDate: str
    reason: str | None = None


class AccountClosureResponse(BaseModel):
    """Response for account closure processing."""
    customerId: str
    affectedCases: int
    message: str


# Endpoints

@router.post(
    "/greenid",
    response_model=CaseCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid webhook signature"},
        409: {"model": ErrorResponse, "description": "Duplicate webhook"},
        422: {"model": ErrorResponse, "description": "Invalid payload"},
    }
)
async def receive_greenid_webhook(
    request: Request,
    payload: GreenIDWebhookPayload,
    db=Depends(get_db),
    _auth: bool = Depends(verify_greenid_webhook)
):
    """
    Receive and process GreenID webhook for KYC remediation.

    Creates a new AML case based on the webhook payload.
    Validates HMAC signature and rejects duplicates.

    For sanctions alerts:
    - Creates onboarding block (FR-028)
    - Links to existing open cases for same customer (EC-014)
    """
    case_service = CaseService(db)
    block_service = OnboardingBlockService(db)
    link_service = CaseLinkService(db)

    try:
        # Extract customer data
        customer_data = payload.customer.model_dump() if payload.customer else {}

        # Check for existing open cases for this customer (EC-014)
        existing_cases = case_service.get_open_cases_for_customer(payload.customerId)

        # Create case
        case = case_service.create_case_from_greenid_webhook(
            payload=payload.model_dump(),
            customer_data=customer_data
        )

        # Determine if this is a sanctions/blocking case
        from src.models.case import CaseType
        from src.models.onboarding_block import BlockReason

        onboarding_blocked = False
        linked_case_ids = []

        # Create onboarding block for sanctions cases (FR-028)
        if case.case_type in (
            CaseType.SANCTIONS_ONBOARDING,
            CaseType.SANCTIONS_PEP_COMBINED
        ):
            block = block_service.create_block(
                customer_id=payload.customerId,
                case_id=case.id,
                reason=BlockReason.SANCTIONS_HIT
            )
            onboarding_blocked = block.is_active
            db.commit()

        # Link to existing open cases (EC-014)
        if existing_cases:
            for existing_case in existing_cases:
                link_service.link_cases_for_new_alert(
                    existing_case_id=existing_case.id,
                    new_case_id=case.id
                )
                linked_case_ids.append(str(existing_case.id))
            db.commit()

        return CaseCreatedResponse(
            id=str(case.id),
            caseReference=case.case_reference,
            caseType=case.case_type.value,
            status=case.status.value,
            tier=case.tier.value,
            customerId=case.customer.external_customer_id,
            createdAt=case.created_at.isoformat(),
            onboardingBlocked=onboarding_blocked,
            alertTypes=case.alert_types,
            linkedCaseIds=linked_case_ids if linked_case_ids else None
        )

    except DuplicateWebhookError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate webhook: {e.message}"
        )


@router.post(
    "/indue",
    response_model=CaseCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid webhook signature"},
        409: {"model": ErrorResponse, "description": "Duplicate webhook"},
        422: {"model": ErrorResponse, "description": "Invalid payload"},
    }
)
async def receive_indue_webhook(
    request: Request,
    payload: IndueWebhookPayload,
    db=Depends(get_db),
    _auth: bool = Depends(verify_indue_webhook)
):
    """
    Receive and process Indue webhook for PEP/Sanctions screening.

    Creates a new AML case based on the screening results.
    Validates HMAC signature and rejects duplicates.

    For sanctions alerts:
    - Creates onboarding block (FR-028)
    - Links to existing open cases for same customer (EC-014)
    """
    case_service = CaseService(db)
    block_service = OnboardingBlockService(db)
    link_service = CaseLinkService(db)

    try:
        # Check for existing open cases for this customer (EC-014)
        existing_cases = case_service.get_open_cases_for_customer(payload.customerId)

        # Create case
        case = case_service.create_case_from_indue_webhook(
            payload=payload.model_dump(),
            customer_id=payload.customerId
        )

        # Determine if this is a blocking case
        from src.models.case import CaseType, CaseTier
        from src.models.onboarding_block import BlockReason

        onboarding_blocked = False
        linked_case_ids = []

        # Create onboarding block for sanctions cases (FR-028)
        if case.case_type in (
            CaseType.SANCTIONS_ONBOARDING,
            CaseType.SANCTIONS_PEP_COMBINED
        ):
            block = block_service.create_block(
                customer_id=payload.customerId,
                case_id=case.id,
                reason=BlockReason.SANCTIONS_HIT
            )
            onboarding_blocked = block.is_active
            db.commit()

        # Create onboarding block for high-confidence PEP (FR-031)
        elif case.case_type == CaseType.PEP_HIGH_CONFIDENCE:
            block = block_service.create_block(
                customer_id=payload.customerId,
                case_id=case.id,
                reason=BlockReason.HIGH_CONFIDENCE_PEP
            )
            onboarding_blocked = block.is_active
            # High-confidence PEP goes to L2
            case.tier = CaseTier.L2
            db.commit()

        # Existing customer sanctions - NO block, but goes to L2 (FR-036, FR-037)
        elif case.case_type == CaseType.SANCTIONS_EXISTING_CUSTOMER:
            # No onboarding block - they're already a customer
            onboarding_blocked = False
            # Goes to L2 due to higher risk
            case.tier = CaseTier.L2
            db.commit()

        # Link to existing open cases (EC-014)
        if existing_cases:
            for existing_case in existing_cases:
                link_service.link_cases_for_new_alert(
                    existing_case_id=existing_case.id,
                    new_case_id=case.id
                )
                linked_case_ids.append(str(existing_case.id))
            db.commit()

        return CaseCreatedResponse(
            id=str(case.id),
            caseReference=case.case_reference,
            caseType=case.case_type.value,
            status=case.status.value,
            tier=case.tier.value,
            customerId=case.customer.external_customer_id,
            createdAt=case.created_at.isoformat(),
            onboardingBlocked=onboarding_blocked,
            alertTypes=case.alert_types,
            linkedCaseIds=linked_case_ids if linked_case_ids else None
        )

    except DuplicateWebhookError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate webhook: {e.message}"
        )


@router.post(
    "/account-closure",
    response_model=AccountClosureResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid webhook signature"},
        422: {"model": ErrorResponse, "description": "Invalid payload"},
    }
)
async def receive_account_closure_webhook(
    request: Request,
    payload: AccountClosureWebhookPayload,
    db=Depends(get_db),
    _auth: bool = Depends(verify_indue_webhook)
):
    """
    Receive and process customer account closure webhook (EC-008).

    Updates all active cases for the customer to show account closed indicator.
    """
    service = CaseService(db)

    affected_count = service.mark_customer_account_closed(
        customer_id=payload.customerId,
        closure_date=payload.closureDate,
        reason=payload.reason
    )

    return AccountClosureResponse(
        customerId=payload.customerId,
        affectedCases=affected_count,
        message=f"Account closure processed. {affected_count} active cases updated."
    )
