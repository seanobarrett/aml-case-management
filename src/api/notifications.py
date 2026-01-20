"""
Notification API endpoints.

References:
- FR-069: Notification retrieval
- D6: 30s polling for dashboard
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from src.middleware.auth import CurrentUser, get_current_user
from src.services.notification_service import NotificationService
from src.db.session import get_db


router = APIRouter(prefix="/notifications", tags=["notifications"])


# Response schemas

class NotificationItem(BaseModel):
    """Notification item in response."""
    id: str
    notificationType: str
    title: str
    message: str
    caseId: str | None
    isRead: bool
    createdAt: str


class NotificationListResponse(BaseModel):
    """Paginated notification list response."""
    items: list[NotificationItem]
    total: int
    unreadCount: int
    page: int
    pageSize: int


class NotificationCountResponse(BaseModel):
    """Notification count response."""
    total: int
    unread: int


class NotificationReadResponse(BaseModel):
    """Response after marking notification as read."""
    id: str
    isRead: bool
    readAt: str | None


# Endpoints

@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List notifications for current user"
)
async def list_notifications(
    unreadOnly: bool = Query(False, description="Only return unread notifications"),
    page: int = Query(1, ge=1, description="Page number"),
    pageSize: int = Query(20, ge=1, le=100, description="Items per page"),
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Get notifications for the authenticated user.

    Returns paginated list with unread count for badge display.
    Supports 30-second polling for dashboard updates (D6).
    """
    service = NotificationService(db)

    notifications, total, unread_count = service.get_user_notifications(
        user_id=user.user_id,
        unread_only=unreadOnly,
        page=page,
        page_size=pageSize
    )

    return NotificationListResponse(
        items=[
            NotificationItem(
                id=str(n.id),
                notificationType=n.notification_type,
                title=n.title,
                message=n.message,
                caseId=str(n.case_id) if n.case_id else None,
                isRead=n.is_read,
                createdAt=n.created_at.isoformat()
            )
            for n in notifications
        ],
        total=total,
        unreadCount=unread_count,
        page=page,
        pageSize=pageSize
    )


@router.get(
    "/count",
    response_model=NotificationCountResponse,
    summary="Get notification counts"
)
async def get_notification_count(
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Get notification counts for the authenticated user.

    Lightweight endpoint for polling notification badge updates.
    """
    service = NotificationService(db)
    total, unread = service.get_notification_count(user.user_id)

    return NotificationCountResponse(
        total=total,
        unread=unread
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationReadResponse,
    summary="Mark notification as read"
)
async def mark_notification_read(
    notification_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Mark a specific notification as read.

    Only the notification owner can mark it as read.
    """
    service = NotificationService(db)
    notification = service.mark_as_read(notification_id, user.user_id)

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification not found: {notification_id}"
        )

    db.commit()

    return NotificationReadResponse(
        id=str(notification.id),
        isRead=notification.is_read,
        readAt=notification.read_at.isoformat() if notification.read_at else None
    )


@router.post(
    "/read-all",
    summary="Mark all notifications as read"
)
async def mark_all_notifications_read(
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Mark all notifications as read for the authenticated user.
    """
    service = NotificationService(db)
    count = service.mark_all_as_read(user.user_id)
    db.commit()

    return {"markedAsRead": count}
