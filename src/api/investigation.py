"""
Investigation API endpoints.

References:
- US-4: L2 Analyst investigates case and recommends SMR
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.middleware.auth import CurrentUser, get_current_user
from src.services.investigation_service import InvestigationService
from src.db.session import get_db


router = APIRouter(prefix="/cases", tags=["investigation"])


class InvestigationFindingsRequest(BaseModel):
    """Request to document investigation findings."""
    summary: str = Field(..., min_length=20, description="Investigation summary")
    methodology: str = Field(..., min_length=10, description="Investigation methodology")
    keyFindings: list[str] = Field(..., min_items=1, description="Key findings list")
    riskAssessment: str = Field(..., description="Risk level (LOW/MEDIUM/HIGH/CRITICAL)")
    recommendation: str = Field(..., description="Investigation recommendation")
    additionalNotes: Optional[str] = Field(None, description="Additional notes")


class InvestigationFindingsResponse(BaseModel):
    """Investigation findings response."""
    id: str
    caseId: str
    summary: str
    riskAssessment: str
    recommendation: str
    hasFindings: bool
    createdAt: str


@router.post(
    "/{case_id}/investigation-findings",
    response_model=InvestigationFindingsResponse,
    summary="Document investigation findings"
)
async def create_investigation_findings(
    case_id: UUID,
    request: InvestigationFindingsRequest,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Document investigation findings for a case.

    Only L2 analysts and managers can create investigation findings.
    """
    # Check role permission
    if not user.has_permission("can_investigate"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only L2 analysts and managers can document investigation findings"
        )

    service = InvestigationService(db)

    try:
        findings = service.create_findings(
            case_id=case_id,
            investigator_id=user.user_id,
            summary=request.summary,
            methodology=request.methodology,
            key_findings=request.keyFindings,
            risk_assessment=request.riskAssessment,
            recommendation=request.recommendation,
            additional_notes=request.additionalNotes
        )

        return InvestigationFindingsResponse(
            id=str(findings.id),
            caseId=str(findings.case_id),
            summary=findings.summary,
            riskAssessment=findings.risk_assessment.value,
            recommendation=findings.recommendation.value,
            hasFindings=True,
            createdAt=findings.created_at.isoformat()
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/{case_id}/investigation-findings",
    summary="Get investigation findings for a case"
)
async def get_investigation_findings(
    case_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Get all investigation findings for a case.
    """
    service = InvestigationService(db)
    findings_list = service.get_case_findings(case_id)

    return {
        "items": [
            {
                "id": str(f.id),
                "caseId": str(f.case_id),
                "summary": f.summary,
                "methodology": f.methodology,
                "keyFindings": f.key_findings,
                "riskAssessment": f.risk_assessment.value,
                "recommendation": f.recommendation.value,
                "investigatorId": str(f.investigator_id),
                "createdAt": f.created_at.isoformat()
            }
            for f in findings_list
        ],
        "total": len(findings_list)
    }
