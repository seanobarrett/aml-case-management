"""
SMR (Suspicious Matter Report) API endpoints.

References:
- FR-014: Only L2 or higher can create SMR recommendations
- FR-039: SMR recommendation must include justification
- FR-040: SMR draft document generation
- FR-041: AUSTRAC reference recording
- FR-043: Prevent SMR withdrawal after approval
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.middleware.auth import CurrentUser, get_current_user
from src.models.user import UserRole
from src.services.smr_service import SMRService
from src.db.session import get_db


router = APIRouter(prefix="/cases", tags=["smr"])


class SMRRecommendRequest(BaseModel):
    """Request to create SMR recommendation."""
    recommendation: str = Field(..., description="SUBMIT or DO_NOT_SUBMIT")
    justification: str = Field(..., min_length=20, description="Detailed justification")
    suspiciousActivity: str = Field(..., min_length=20, description="Suspicious activity description")
    supportingDocuments: list[str] = Field(default=[], description="Supporting document names")


class SMRApproveRequest(BaseModel):
    """Request to approve SMR."""
    pass  # No additional data needed


class SMRRejectRequest(BaseModel):
    """Request to reject SMR."""
    reason: str = Field(..., min_length=20, description="Rejection reason")


class SMRRecordReferenceRequest(BaseModel):
    """Request to record AUSTRAC reference."""
    austracReference: str = Field(..., min_length=5, description="AUSTRAC reference number")


class SMRResponse(BaseModel):
    """SMR recommendation response."""
    id: str
    caseId: str
    recommendationType: str
    status: str
    recommendedById: str
    recommendedAt: str
    approvedById: Optional[str] = None
    approvedAt: Optional[str] = None
    austracReference: Optional[str] = None
    filedAt: Optional[str] = None


@router.post(
    "/{case_id}/smr/recommend",
    response_model=SMRResponse,
    summary="Create SMR recommendation"
)
async def create_smr_recommendation(
    case_id: UUID,
    request: SMRRecommendRequest,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Create an SMR recommendation.

    Only L2 analysts and managers can create SMR recommendations (BR-SMR-001).
    """
    # Check role permission (FR-014, BR-SMR-001)
    if user.role not in (UserRole.L2_ANALYST, UserRole.AML_MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only L2 analysts and managers can create SMR recommendations"
        )

    service = SMRService(db)

    try:
        smr = service.create_recommendation(
            case_id=case_id,
            user_id=user.user_id,
            recommendation_type=request.recommendation,
            justification=request.justification,
            suspicious_activity=request.suspiciousActivity,
            supporting_documents=request.supportingDocuments
        )

        return SMRResponse(
            id=str(smr.id),
            caseId=str(smr.case_id),
            recommendationType=smr.recommendation_type.value,
            status=smr.status.value,
            recommendedById=str(smr.recommended_by_id),
            recommendedAt=smr.recommended_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{case_id}/smr/approve",
    response_model=SMRResponse,
    summary="Approve SMR recommendation"
)
async def approve_smr(
    case_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Approve an SMR recommendation.

    Only managers can approve SMRs. The approver must be different from the recommender (BR-SMR-002).
    """
    # Check role permission
    if user.role != UserRole.AML_MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only AML managers can approve SMR recommendations"
        )

    service = SMRService(db)

    # Get the pending recommendation for this case
    recommendations = service.get_case_recommendations(case_id)
    pending = [r for r in recommendations if r.status.value == "PENDING_APPROVAL"]

    if not pending:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending SMR recommendation found for this case"
        )

    try:
        smr = service.approve(pending[0].id, user.user_id)

        return SMRResponse(
            id=str(smr.id),
            caseId=str(smr.case_id),
            recommendationType=smr.recommendation_type.value,
            status=smr.status.value,
            recommendedById=str(smr.recommended_by_id),
            recommendedAt=smr.recommended_at.isoformat(),
            approvedById=str(smr.approved_by_id) if smr.approved_by_id else None,
            approvedAt=smr.approved_at.isoformat() if smr.approved_at else None
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{case_id}/smr/reject",
    response_model=SMRResponse,
    summary="Reject SMR recommendation"
)
async def reject_smr(
    case_id: UUID,
    request: SMRRejectRequest,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Reject an SMR recommendation.

    Only managers can reject SMRs (EC-010).
    """
    # Check role permission
    if user.role != UserRole.AML_MANAGER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only AML managers can reject SMR recommendations"
        )

    service = SMRService(db)

    # Get the pending recommendation for this case
    recommendations = service.get_case_recommendations(case_id)
    pending = [r for r in recommendations if r.status.value == "PENDING_APPROVAL"]

    if not pending:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pending SMR recommendation found for this case"
        )

    try:
        smr = service.reject(pending[0].id, user.user_id, request.reason)

        return SMRResponse(
            id=str(smr.id),
            caseId=str(smr.case_id),
            recommendationType=smr.recommendation_type.value,
            status=smr.status.value,
            recommendedById=str(smr.recommended_by_id),
            recommendedAt=smr.recommended_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{case_id}/smr/record-reference",
    response_model=SMRResponse,
    summary="Record AUSTRAC reference"
)
async def record_austrac_reference(
    case_id: UUID,
    request: SMRRecordReferenceRequest,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Record AUSTRAC filing reference for an approved SMR.

    Can only be done for approved SMRs (FR-041).
    """
    service = SMRService(db)

    # Get the approved recommendation for this case
    recommendations = service.get_case_recommendations(case_id)
    approved = [r for r in recommendations if r.status.value == "APPROVED"]

    if not approved:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No approved SMR found for this case"
        )

    try:
        smr = service.record_filing(
            approved[0].id,
            user.user_id,
            request.austracReference
        )

        return SMRResponse(
            id=str(smr.id),
            caseId=str(smr.case_id),
            recommendationType=smr.recommendation_type.value,
            status=smr.status.value,
            recommendedById=str(smr.recommended_by_id),
            recommendedAt=smr.recommended_at.isoformat(),
            approvedById=str(smr.approved_by_id) if smr.approved_by_id else None,
            approvedAt=smr.approved_at.isoformat() if smr.approved_at else None,
            austracReference=smr.austrac_reference,
            filedAt=smr.filed_at.isoformat() if smr.filed_at else None
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/{case_id}/smr",
    summary="Get SMR recommendations for a case"
)
async def get_smr_recommendations(
    case_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Get all SMR recommendations for a case.
    """
    service = SMRService(db)
    recommendations = service.get_case_recommendations(case_id)

    return {
        "items": [
            {
                "id": str(r.id),
                "caseId": str(r.case_id),
                "recommendationType": r.recommendation_type.value,
                "status": r.status.value,
                "justification": r.justification,
                "suspiciousActivity": r.suspicious_activity,
                "recommendedById": str(r.recommended_by_id),
                "recommendedAt": r.recommended_at.isoformat(),
                "approvedById": str(r.approved_by_id) if r.approved_by_id else None,
                "approvedAt": r.approved_at.isoformat() if r.approved_at else None,
                "rejectionReason": r.rejection_reason,
                "austracReference": r.austrac_reference,
                "filedAt": r.filed_at.isoformat() if r.filed_at else None
            }
            for r in recommendations
        ],
        "total": len(recommendations)
    }
