"""
Enhanced Due Diligence (EDD) API endpoints.

References:
- US-7: High-confidence PEP requires EDD
- FR-033: EDD checklist requirements
- FR-034: EDD completion workflow
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.middleware.auth import CurrentUser, get_current_user
from src.models.user import UserRole
from src.services.edd_service import EDDService
from src.services.case_service import CaseService
from src.db.session import get_db


router = APIRouter(prefix="/cases", tags=["edd"])


# Request/Response schemas

class EDDItemUpdate(BaseModel):
    """EDD item update."""
    itemId: str
    completed: bool
    notes: str | None = None


class EDDChecklistUpdateRequest(BaseModel):
    """Request to update EDD checklist items."""
    items: list[EDDItemUpdate] = Field(..., min_length=1)


class EDDItemResponse(BaseModel):
    """EDD item in response."""
    id: str
    itemId: str
    title: str
    description: str | None
    required: bool
    completed: bool
    completedAt: str | None
    completedById: str | None
    notes: str | None


class EDDChecklistResponse(BaseModel):
    """EDD checklist response."""
    id: str
    caseId: str
    required: bool
    completed: bool
    completedAt: str | None
    completedById: str | None
    items: list[EDDItemResponse]


class EDDCompletionResponse(BaseModel):
    """Response after updating EDD checklist."""
    caseId: str
    completed: bool
    message: str


@router.get(
    "/{case_id}/edd-checklist",
    response_model=EDDChecklistResponse,
    summary="Get EDD checklist for case"
)
async def get_edd_checklist(
    case_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Get the EDD checklist for a case.

    Returns the checklist with all items and their completion status.
    Creates a new checklist if one doesn't exist for high-confidence PEP cases.
    """
    case_service = CaseService(db)
    edd_service = EDDService(db)

    case = case_service.get_case_by_id(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case not found: {case_id}"
        )

    # Check if EDD is required
    if not edd_service.is_edd_required_for_case(case):
        return EDDChecklistResponse(
            id="",
            caseId=str(case_id),
            required=False,
            completed=True,
            completedAt=None,
            completedById=None,
            items=[]
        )

    # Get or create checklist
    checklist = edd_service.get_checklist_for_case(case_id)
    if not checklist:
        checklist = edd_service.create_checklist_for_case(case_id)
        db.commit()

    return EDDChecklistResponse(
        id=str(checklist.id),
        caseId=str(checklist.case_id),
        required=checklist.is_required,
        completed=checklist.is_completed,
        completedAt=checklist.completed_at.isoformat() if checklist.completed_at else None,
        completedById=str(checklist.completed_by_id) if checklist.completed_by_id else None,
        items=[
            EDDItemResponse(
                id=str(item.id),
                itemId=item.item_type.value,
                title=item.title,
                description=item.description,
                required=item.is_required,
                completed=item.is_completed,
                completedAt=item.completed_at.isoformat() if item.completed_at else None,
                completedById=str(item.completed_by_id) if item.completed_by_id else None,
                notes=item.notes
            )
            for item in checklist.items
        ]
    )


@router.post(
    "/{case_id}/edd-checklist",
    response_model=EDDCompletionResponse,
    summary="Update EDD checklist items"
)
async def update_edd_checklist(
    case_id: UUID,
    request: EDDChecklistUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Update EDD checklist items with completion status.

    Only L2 analysts and managers can complete EDD items.
    Automatically marks checklist as complete when all required items are done.
    """
    # Check permissions - only L2+ can complete EDD
    if user.role not in (UserRole.L2_ANALYST, UserRole.AML_MANAGER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only L2 analysts and managers can complete EDD items"
        )

    case_service = CaseService(db)
    edd_service = EDDService(db)

    case = case_service.get_case_by_id(case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case not found: {case_id}"
        )

    # Check if EDD is required
    if not edd_service.is_edd_required_for_case(case):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="EDD is not required for this case"
        )

    # Auto-create checklist if it doesn't exist
    checklist = edd_service.get_checklist_for_case(case_id)
    if not checklist:
        checklist = edd_service.create_checklist_for_case(case_id)
        db.commit()

    try:
        # Update items
        items_data = [
            {
                "itemId": item.itemId,
                "completed": item.completed,
                "notes": item.notes
            }
            for item in request.items
        ]

        checklist = edd_service.update_checklist_items(
            case_id=case_id,
            user_id=user.user_id,
            items=items_data
        )
        db.commit()

        if checklist.is_completed:
            message = "EDD checklist completed successfully"
        else:
            incomplete_count = sum(
                1 for item in checklist.items
                if item.is_required and not item.is_completed
            )
            message = f"EDD checklist updated. {incomplete_count} required items remaining"

        return EDDCompletionResponse(
            caseId=str(case_id),
            completed=checklist.is_completed,
            message=message
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
