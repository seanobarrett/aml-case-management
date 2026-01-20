"""
Users API endpoints for user management.

References:
- US-14: Role change case reassignment
- FR-026: Role change detection and case reassignment
- FR-027: Audit entry for each affected case
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.db.session import get_db
from src.middleware.auth import CurrentUser, get_current_user
from src.models.user import UserRole
from src.services.user_service import UserService


def check_permission(user: CurrentUser, permission: str) -> None:
    """Check if user has permission and raise 403 if not."""
    if not user.has_permission(permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission '{permission}' required"
        )


router = APIRouter(prefix="/users", tags=["users"])


# Request/Response schemas

class UpdateUserRequest(BaseModel):
    """Request to update user details."""
    role: Optional[str] = None
    tier: Optional[str] = None


class UserResponse(BaseModel):
    """User response schema."""
    id: str
    email: str
    role: str
    tier: Optional[str]
    isActive: bool


class UpdateUserResponse(BaseModel):
    """Response after updating user."""
    user: UserResponse
    casesReassigned: int


class UserListResponse(BaseModel):
    """List of users response."""
    users: list[UserResponse]
    total: int


# Endpoints

@router.get(
    "",
    response_model=UserListResponse,
    summary="List users"
)
async def list_users(
    role: Optional[str] = None,
    tier: Optional[str] = None,
    isActive: bool = True,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    List users with optional filtering.

    Requires: Manager or Admin role.
    """
    check_permission(user, "can_view_users")

    service = UserService(db)

    parsed_role = None
    if role:
        try:
            parsed_role = UserRole(role)
        except ValueError:
            pass

    users = service.list_users(
        role=parsed_role,
        tier=tier,
        is_active=isActive
    )

    return UserListResponse(
        users=[
            UserResponse(
                id=str(u.id),
                email=u.email,
                role=u.role.value,
                tier=u.tier,
                isActive=u.is_active
            )
            for u in users
        ],
        total=len(users)
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID"
)
async def get_user(
    user_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Get user details by ID.

    Requires: Manager or Admin role, or own user.
    """
    # Allow users to view their own profile
    if str(user.user_id) != str(user_id):
        check_permission(user, "can_view_users")

    service = UserService(db)
    target_user = service.get_user_by_id(user_id)

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse(
        id=str(target_user.id),
        email=target_user.email,
        role=target_user.role.value,
        tier=target_user.tier,
        isActive=target_user.is_active
    )


@router.patch(
    "/{user_id}",
    response_model=UpdateUserResponse,
    summary="Update user"
)
async def update_user(
    user_id: UUID,
    request: UpdateUserRequest,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Update user role or tier (FR-026).

    When role/tier changes affect case access, assigned cases are
    automatically unassigned and returned to the queue.

    Audit entries are created for each affected case (FR-027).

    Requires: Manager role with can_manage_users permission.
    """
    check_permission(user, "can_manage_users")

    service = UserService(db)
    target_user = service.get_user_by_id(user_id)

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    total_reassigned = 0

    # Handle role change
    if request.role:
        try:
            new_role = UserRole(request.role)
            target_user, reassigned = service.update_user_role(
                user_id=user_id,
                new_role=new_role,
                updated_by_id=user.user_id
            )
            total_reassigned += reassigned
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {request.role}"
            )

    # Handle tier change
    if request.tier:
        if request.tier not in ["L1", "L2"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier: {request.tier}. Must be L1 or L2."
            )

        target_user, reassigned = service.update_user_tier(
            user_id=user_id,
            new_tier=request.tier,
            updated_by_id=user.user_id
        )
        total_reassigned += reassigned

    return UpdateUserResponse(
        user=UserResponse(
            id=str(target_user.id),
            email=target_user.email,
            role=target_user.role.value,
            tier=target_user.tier,
            isActive=target_user.is_active
        ),
        casesReassigned=total_reassigned
    )
