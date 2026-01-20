"""
Onboarding block API endpoints.

References:
- US-6: Block high-risk onboarding during investigation
- FR-028: Block onboarding during sanctions investigation
- FR-029: Clear block upon case closure
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.middleware.auth import CurrentUser, get_current_user
from src.services.onboarding_block_service import OnboardingBlockService
from src.db.session import get_db


router = APIRouter(prefix="/onboarding-blocks", tags=["onboarding-blocks"])


# Response schemas

class BlockStatusResponse(BaseModel):
    """Onboarding block status response."""
    customerId: str
    isBlocked: bool
    caseId: str | None
    caseReference: str | None
    blockedAt: str | None
    reason: str | None
    syncStatus: str


@router.get(
    "/{customer_id}",
    response_model=BlockStatusResponse,
    summary="Get onboarding block status for customer"
)
async def get_customer_block_status(
    customer_id: str,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Get onboarding block status for a customer.

    Used by Spriggy to check if a customer can proceed with onboarding.
    Returns block details if blocked, or isBlocked=False if not.
    """
    block_service = OnboardingBlockService(db)

    block = block_service.get_block_for_customer(customer_id)

    if not block:
        return BlockStatusResponse(
            customerId=customer_id,
            isBlocked=False,
            caseId=None,
            caseReference=None,
            blockedAt=None,
            reason=None,
            syncStatus="NONE"
        )

    # Get case reference
    case_reference = None
    if block.case:
        case_reference = block.case.case_reference

    return BlockStatusResponse(
        customerId=customer_id,
        isBlocked=block.is_active,
        caseId=str(block.case_id) if block.case_id else None,
        caseReference=case_reference,
        blockedAt=block.blocked_at.isoformat() if block.blocked_at else None,
        reason=block.reason.value if block.reason else None,
        syncStatus=block.sync_status.value
    )
