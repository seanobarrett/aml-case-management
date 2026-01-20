"""
Notification service for creating and managing notifications.

References:
- D6: Celery async tasks + email provider; 30s polling for dashboard
- FR-066: SLA breach notifications
- FR-067: Escalation notifications
- FR-068: SMR submission notifications
- FR-069: Notification retrieval
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.notification import Notification, NotificationType
from src.models.user import User, UserRole


class NotificationService:
    """Service for notification management."""

    def __init__(self, db: Session):
        self.db = db

    def create_notification(
        self,
        user_id: UUID,
        notification_type: NotificationType | str,
        title: str,
        message: str,
        case_id: Optional[UUID] = None
    ) -> Notification:
        """
        Create a new notification.

        Args:
            user_id: Target user ID
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            case_id: Related case ID

        Returns:
            Created Notification instance
        """
        notification = Notification.create(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            case_id=case_id
        )
        self.db.add(notification)
        self.db.flush()
        return notification

    def get_user_notifications(
        self,
        user_id: UUID,
        unread_only: bool = False,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list[Notification], int, int]:
        """
        Get notifications for a user.

        Args:
            user_id: User ID
            unread_only: Only return unread notifications
            page: Page number
            page_size: Items per page

        Returns:
            Tuple of (notifications list, total count, unread count)
        """
        query = self.db.query(Notification).filter(Notification.user_id == user_id)

        # Get unread count before filtering
        unread_count = query.filter(Notification.is_read == False).count()

        # Reset query for actual results
        query = self.db.query(Notification).filter(Notification.user_id == user_id)

        if unread_only:
            query = query.filter(Notification.is_read == False)

        # Get total
        total = query.count()

        # Order by newest first, apply pagination
        notifications = (
            query
            .order_by(Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return notifications, total, unread_count

    def get_notification_count(self, user_id: UUID) -> tuple[int, int]:
        """
        Get notification counts for a user.

        Args:
            user_id: User ID

        Returns:
            Tuple of (total count, unread count)
        """
        query = self.db.query(Notification).filter(Notification.user_id == user_id)
        total = query.count()
        unread = query.filter(Notification.is_read == False).count()
        return total, unread

    def mark_as_read(self, notification_id: UUID, user_id: UUID) -> Optional[Notification]:
        """
        Mark a notification as read.

        Args:
            notification_id: Notification ID
            user_id: User ID (for verification)

        Returns:
            Updated Notification or None if not found
        """
        notification = (
            self.db.query(Notification)
            .filter(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
            .first()
        )

        if notification:
            notification.mark_as_read()
            self.db.flush()

        return notification

    def mark_all_as_read(self, user_id: UUID) -> int:
        """
        Mark all notifications as read for a user.

        Args:
            user_id: User ID

        Returns:
            Number of notifications marked as read
        """
        from datetime import datetime

        result = (
            self.db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.is_read == False
            )
            .update({
                Notification.is_read: True,
                Notification.read_at: datetime.utcnow()
            })
        )
        self.db.flush()
        return result

    # Specific notification creators

    def notify_sla_warning(
        self,
        user_id: UUID,
        case_id: UUID,
        case_reference: str,
        hours_remaining: int
    ) -> Notification:
        """Create SLA warning notification (FR-066)."""
        notification = Notification.for_sla_warning(
            user_id=user_id,
            case_id=case_id,
            case_reference=case_reference,
            hours_remaining=hours_remaining
        )
        self.db.add(notification)
        self.db.flush()
        return notification

    def notify_sla_breach(
        self,
        user_id: UUID,
        case_id: UUID,
        case_reference: str
    ) -> Notification:
        """Create SLA breach notification (FR-066)."""
        notification = Notification.for_sla_breach(
            user_id=user_id,
            case_id=case_id,
            case_reference=case_reference
        )
        self.db.add(notification)
        self.db.flush()
        return notification

    def notify_escalation(
        self,
        case_id: UUID,
        case_reference: str
    ) -> list[Notification]:
        """
        Notify L2 analysts of escalation (FR-067).

        Creates notifications for all active L2 analysts.
        """
        # Get all active L2 analysts
        l2_analysts = (
            self.db.query(User)
            .filter(
                User.role == UserRole.L2_ANALYST,
                User.is_active == True
            )
            .all()
        )

        notifications = []
        for analyst in l2_analysts:
            notification = Notification.for_escalation(
                user_id=analyst.id,
                case_id=case_id,
                case_reference=case_reference
            )
            self.db.add(notification)
            notifications.append(notification)

        self.db.flush()
        return notifications

    def notify_smr_submission(
        self,
        case_id: UUID,
        case_reference: str
    ) -> list[Notification]:
        """
        Notify managers of SMR submission (FR-068).

        Creates notifications for all active AML managers.
        """
        # Get all active managers
        managers = (
            self.db.query(User)
            .filter(
                User.role == UserRole.AML_MANAGER,
                User.is_active == True
            )
            .all()
        )

        notifications = []
        for manager in managers:
            notification = Notification.for_smr_submission(
                manager_id=manager.id,
                case_id=case_id,
                case_reference=case_reference
            )
            self.db.add(notification)
            notifications.append(notification)

        self.db.flush()
        return notifications

    def notify_case_assigned(
        self,
        user_id: UUID,
        case_id: UUID,
        case_reference: str
    ) -> Notification:
        """Create case assignment notification."""
        return self.create_notification(
            user_id=user_id,
            notification_type=NotificationType.CASE_ASSIGNED,
            title=f"Case Assigned: {case_reference}",
            message=f"You have been assigned to case {case_reference}.",
            case_id=case_id
        )

    def notify_l2_review_required(
        self,
        case_id: UUID,
        case_reference: str
    ) -> list[Notification]:
        """
        Notify L2 analysts of L1 closure requiring review.

        Creates notifications for all active L2 analysts.
        """
        l2_analysts = (
            self.db.query(User)
            .filter(
                User.role == UserRole.L2_ANALYST,
                User.is_active == True
            )
            .all()
        )

        notifications = []
        for analyst in l2_analysts:
            notification = self.create_notification(
                user_id=analyst.id,
                notification_type=NotificationType.L2_REVIEW_REQUIRED,
                title=f"L2 Review Required: {case_reference}",
                message=f"L1 closure of case {case_reference} requires L2 quality review.",
                case_id=case_id
            )
            notifications.append(notification)

        return notifications

    # SLA-specific notification methods for Celery tasks

    def send_sla_warning(self, case_id: UUID) -> Optional[Notification]:
        """
        Send SLA warning notification to assigned analyst (FR-050).

        Args:
            case_id: Case approaching SLA deadline

        Returns:
            Created notification, or None if no assignee
        """
        from src.models.case import Case

        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case or not case.assigned_to_id:
            return None

        # Calculate hours remaining
        from datetime import datetime
        hours_remaining = 0
        if case.sla_deadline:
            delta = case.sla_deadline - datetime.utcnow()
            hours_remaining = max(0, int(delta.total_seconds() / 3600))

        return self.notify_sla_warning(
            user_id=case.assigned_to_id,
            case_id=case_id,
            case_reference=case.case_reference,
            hours_remaining=hours_remaining
        )

    def send_sla_breach_to_managers(self, case_id: UUID) -> list[Notification]:
        """
        Send SLA breach notification to all managers (FR-052).

        Args:
            case_id: Case that breached SLA

        Returns:
            List of created notifications
        """
        from src.models.case import Case

        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return []

        # Get all managers
        managers = (
            self.db.query(User)
            .filter(
                User.role == UserRole.AML_MANAGER,
                User.is_active == True
            )
            .all()
        )

        notifications = []
        for manager in managers:
            notification = self.notify_sla_breach(
                user_id=manager.id,
                case_id=case_id,
                case_reference=case.case_reference
            )
            notifications.append(notification)

        # Also notify the assigned analyst if any
        if case.assigned_to_id:
            analyst_notification = self.notify_sla_breach(
                user_id=case.assigned_to_id,
                case_id=case_id,
                case_reference=case.case_reference
            )
            notifications.append(analyst_notification)

        return notifications
