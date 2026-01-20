"""
Celery tasks for SLA monitoring and breach handling.

References:
- FR-050: SLA warning notifications
- FR-051: Automatic escalation on breach
- FR-052: Manager notification for breaches
"""

from celery import shared_task

from src.db.session import SessionLocal
from src.services.sla_service import SLAService
from src.services.notification_service import NotificationService


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 3},
    name="sla.monitor_approaching"
)
def monitor_approaching_sla(self):
    """
    Monitor cases approaching SLA deadline and send warnings (FR-050).

    This task should run frequently (e.g., every 15 minutes) to detect
    cases approaching their SLA deadline and send warning notifications.
    """
    db = SessionLocal()
    try:
        sla_service = SLAService(db)
        notification_service = NotificationService(db)

        warned_case_ids = sla_service.process_sla_warnings()

        # Send notifications for each warned case
        for case_id in warned_case_ids:
            notification_service.send_sla_warning(case_id)
            db.commit()

        return {
            "status": "success",
            "warnings_sent": len(warned_case_ids),
            "case_ids": [str(cid) for cid in warned_case_ids]
        }

    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_kwargs={"max_retries": 3},
    name="sla.process_breaches"
)
def process_sla_breaches(self):
    """
    Process SLA breaches: record breach and escalate cases (FR-051).

    This task should run frequently (e.g., every 15 minutes) to detect
    cases that have breached their SLA deadline.
    """
    db = SessionLocal()
    try:
        sla_service = SLAService(db)
        notification_service = NotificationService(db)

        results = sla_service.process_sla_breaches()

        # Send manager notifications for breached cases (FR-052)
        for result in results:
            notification_service.send_sla_breach_to_managers(result["case_id"])
            db.commit()

        return {
            "status": "success",
            "breaches_processed": len(results),
            "escalated_count": sum(1 for r in results if r["escalated"]),
            "results": [
                {
                    "case_id": str(r["case_id"]),
                    "case_reference": r["case_reference"],
                    "escalated": r["escalated"]
                }
                for r in results
            ]
        }

    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(
    bind=True,
    name="sla.check_all"
)
def check_all_sla_statuses(self):
    """
    Combined task to check both warnings and breaches.

    This is a convenience task that runs both warning and breach checks.
    Can be scheduled as a single periodic task.
    """
    # Run both tasks in sequence
    warning_result = monitor_approaching_sla.delay()
    breach_result = process_sla_breaches.delay()

    return {
        "status": "submitted",
        "warning_task_id": str(warning_result.id),
        "breach_task_id": str(breach_result.id)
    }
