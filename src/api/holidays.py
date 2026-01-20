"""
Holiday configuration API endpoints.

References:
- FR-048: SLA calculation with business days
"""

from datetime import date as DateType
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.db.session import get_db
from src.middleware.auth import get_current_user, require_role
from src.models.holiday_override import HolidayOverride, HolidayScope
from src.models.user import User, UserRole


router = APIRouter(prefix="/config/holidays", tags=["configuration"])


# Request/Response schemas

class HolidayCreate(BaseModel):
    """Request schema for creating a holiday."""
    holiday_date: DateType = Field(..., alias="date", description="Date of the holiday")
    name: str = Field(..., min_length=1, max_length=255, description="Name of the holiday")
    state: str = Field(default="ALL", description="State code or ALL for national")
    description: Optional[str] = Field(None, description="Optional description")


class HolidayResponse(BaseModel):
    """Response schema for a holiday."""
    id: str
    date: DateType
    name: str
    state: str
    description: Optional[str]

    class Config:
        from_attributes = True


class HolidayListResponse(BaseModel):
    """Response schema for holiday list."""
    items: list[HolidayResponse]
    total: int


class ErrorResponse(BaseModel):
    """Error response schema."""
    detail: str


# Endpoints

@router.get(
    "",
    response_model=HolidayListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
    }
)
async def list_holidays(
    year: Optional[int] = None,
    state: Optional[str] = None,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List configured holidays.

    Optionally filter by year and/or state.
    """
    query = db.query(HolidayOverride)

    if year:
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        query = query.filter(
            HolidayOverride.holiday_date >= start_date,
            HolidayOverride.holiday_date <= end_date
        )

    if state:
        # Include both ALL (national) and specific state
        if state.upper() == "ALL":
            query = query.filter(HolidayOverride.scope == HolidayScope.ALL)
        else:
            query = query.filter(
                (HolidayOverride.scope == HolidayScope.ALL) |
                (HolidayOverride.scope == state.upper())
            )

    holidays = query.order_by(HolidayOverride.holiday_date).all()

    return HolidayListResponse(
        items=[
            HolidayResponse(
                id=str(h.id),
                date=h.holiday_date,
                name=h.name,
                state=h.scope.value,
                description=h.description
            )
            for h in holidays
        ],
        total=len(holidays)
    )


@router.post(
    "",
    response_model=HolidayResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden - Manager role required"},
        409: {"model": ErrorResponse, "description": "Holiday already exists"},
    }
)
async def create_holiday(
    holiday: HolidayCreate,
    db=Depends(get_db),
    current_user: User = Depends(require_role(UserRole.AML_MANAGER))
):
    """
    Add a new public holiday.

    Requires Manager or Compliance Officer role.
    """
    # Validate state code
    try:
        scope = HolidayScope(holiday.state.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid state code: {holiday.state}. Valid values: {[s.value for s in HolidayScope]}"
        )

    # Check for duplicate
    existing = db.query(HolidayOverride).filter(
        HolidayOverride.holiday_date == holiday.holiday_date,
        HolidayOverride.scope == scope
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Holiday already exists for {holiday.holiday_date} with scope {scope.value}"
        )

    # Create holiday
    new_holiday = HolidayOverride.create(
        holiday_date=holiday.holiday_date,
        name=holiday.name,
        scope=scope,
        description=holiday.description,
        created_by=current_user.user_id
    )

    db.add(new_holiday)
    db.commit()
    db.refresh(new_holiday)

    return HolidayResponse(
        id=str(new_holiday.id),
        date=new_holiday.holiday_date,
        name=new_holiday.name,
        state=new_holiday.scope.value,
        description=new_holiday.description
    )


@router.delete(
    "/{holiday_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden - Manager role required"},
        404: {"model": ErrorResponse, "description": "Holiday not found"},
    }
)
async def delete_holiday(
    holiday_id: str,
    db=Depends(get_db),
    current_user: User = Depends(require_role(UserRole.AML_MANAGER))
):
    """
    Delete a holiday.

    Requires Manager or Compliance Officer role.
    """
    holiday = db.query(HolidayOverride).filter(
        HolidayOverride.id == holiday_id
    ).first()

    if not holiday:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Holiday not found"
        )

    db.delete(holiday)
    db.commit()


@router.post(
    "/seed-2026",
    response_model=HolidayListResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden - Manager role required"},
    }
)
async def seed_2026_holidays(
    db=Depends(get_db),
    current_user: User = Depends(require_role(UserRole.AML_MANAGER))
):
    """
    Seed standard Australian public holidays for 2026.

    This is a convenience endpoint to populate the database with
    standard national public holidays. State-specific holidays
    should be added manually.
    """
    holidays = HolidayOverride.get_australian_public_holidays_2026()
    created = []

    for h_data in holidays:
        # Check if already exists
        existing = db.query(HolidayOverride).filter(
            HolidayOverride.holiday_date == h_data["date"],
            HolidayOverride.scope == h_data["scope"]
        ).first()

        if not existing:
            holiday = HolidayOverride.create(
                holiday_date=h_data["date"],
                name=h_data["name"],
                scope=h_data["scope"],
                created_by=current_user.user_id
            )
            db.add(holiday)
            created.append(holiday)

    db.commit()

    return HolidayListResponse(
        items=[
            HolidayResponse(
                id=str(h.id),
                date=h.holiday_date,
                name=h.name,
                state=h.scope.value,
                description=h.description
            )
            for h in created
        ],
        total=len(created)
    )
