"""
Celery tasks for notification delivery.

References:
- D6: Celery async tasks + email provider
"""

import os
from typing import Optional
from uuid import UUID

from celery import Celery

# Celery configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "aml_case_management",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_notification_email(
    self,
    notification_id: str,
    user_email: str,
    subject: str,
    body: str,
    case_reference: Optional[str] = None
):
    """
    Send notification email asynchronously.

    Args:
        notification_id: Notification ID to mark as sent
        user_email: Recipient email
        subject: Email subject
        body: Email body
        case_reference: Optional case reference for tracking
    """
    try:
        # Import here to avoid circular dependencies
        from src.db.session import SessionLocal
        from src.models.notification import Notification

        # Send email (placeholder for actual email service)
        email_sent = _send_email(user_email, subject, body)

        if email_sent:
            # Update notification status
            db = SessionLocal()
            try:
                notification = db.query(Notification).filter(
                    Notification.id == notification_id
                ).first()

                if notification:
                    notification.mark_email_sent()
                    db.commit()
            finally:
                db.close()

        return {"status": "sent", "notification_id": notification_id}

    except Exception as exc:
        # Retry on failure
        raise self.retry(exc=exc)


@celery_app.task
def send_bulk_notification_emails(notification_ids: list[str]):
    """
    Send multiple notification emails in bulk.

    Args:
        notification_ids: List of notification IDs to process
    """
    from src.db.session import SessionLocal
    from src.models.notification import Notification
    from src.models.user import User

    db = SessionLocal()
    try:
        for notification_id in notification_ids:
            notification = db.query(Notification).filter(
                Notification.id == notification_id,
                Notification.email_sent == False
            ).first()

            if notification:
                # Get user email
                user = db.query(User).filter(User.id == notification.user_id).first()
                if user:
                    # Queue individual email task
                    send_notification_email.delay(
                        notification_id=str(notification.id),
                        user_email=user.email,
                        subject=notification.title,
                        body=notification.message
                    )
    finally:
        db.close()


@celery_app.task
def process_pending_notifications():
    """
    Process all pending notifications and send emails.

    This task is designed to be run periodically to catch any
    notifications that weren't sent immediately.
    """
    from src.db.session import SessionLocal
    from src.models.notification import Notification

    db = SessionLocal()
    try:
        # Find unsent notifications (older than 1 minute)
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(minutes=1)

        pending = db.query(Notification).filter(
            Notification.email_sent == False,
            Notification.created_at < cutoff
        ).limit(100).all()

        if pending:
            notification_ids = [str(n.id) for n in pending]
            send_bulk_notification_emails.delay(notification_ids)

        return {"processed": len(pending)}
    finally:
        db.close()


def _send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Send an email via the configured email provider.

    This is a placeholder for the actual email service integration.
    In production, this would use SendGrid, AWS SES, or similar.

    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Email body text

    Returns:
        True if email was sent successfully
    """
    # Email provider configuration
    email_provider = os.getenv("EMAIL_PROVIDER", "console")

    if email_provider == "console":
        # Development: just print to console
        print(f"[EMAIL] To: {to_email}")
        print(f"[EMAIL] Subject: {subject}")
        print(f"[EMAIL] Body: {body}")
        return True

    elif email_provider == "sendgrid":
        # SendGrid integration (placeholder)
        # from sendgrid import SendGridAPIClient
        # sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        # ...
        pass

    elif email_provider == "ses":
        # AWS SES integration (placeholder)
        # import boto3
        # client = boto3.client("ses")
        # ...
        pass

    return False


# Celery beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "process-pending-notifications": {
        "task": "src.tasks.notification_tasks.process_pending_notifications",
        "schedule": 60.0,  # Every minute
    },
}
