"""
Celery tasks for onboarding block synchronization.

References:
- D3: Circuit breaker for external API calls
- EC-009: Retry logic with exponential backoff
"""

import logging
from uuid import UUID

from celery import shared_task

from src.db.session import SessionLocal
from src.services.onboarding_block_service import OnboardingBlockService
from src.services.spriggy_client import SpriggyAPIError


logger = logging.getLogger(__name__)


# Exponential backoff: 1min, 2min, 4min, 8min, 16min
RETRY_DELAYS = [60, 120, 240, 480, 960]


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    autoretry_for=(SpriggyAPIError,),
    retry_backoff=True,
    retry_backoff_max=960,
    retry_jitter=True
)
def sync_onboarding_block(self, block_id: str) -> dict:
    """
    Sync an onboarding block to Spriggy API.

    This task is triggered when a block is created but sync fails.
    It retries with exponential backoff up to 5 times.

    Args:
        block_id: UUID of the OnboardingBlock to sync

    Returns:
        Dict with sync result
    """
    db = SessionLocal()
    try:
        service = OnboardingBlockService(db)
        from src.models.onboarding_block import OnboardingBlock

        block = db.query(OnboardingBlock).filter(
            OnboardingBlock.id == UUID(block_id)
        ).first()

        if not block:
            logger.error(f"Block {block_id} not found")
            return {"success": False, "error": "Block not found"}

        if not block.is_active:
            logger.info(f"Block {block_id} is no longer active, skipping sync")
            return {"success": True, "skipped": True}

        success = service.retry_sync(block)
        db.commit()

        if success:
            logger.info(f"Successfully synced block {block_id}")
            return {"success": True, "block_id": block_id}
        else:
            # Retry if not exceeded max retries
            retry_count = self.request.retries
            if retry_count < self.max_retries:
                raise SpriggyAPIError(f"Sync failed, attempt {retry_count + 1}")
            return {"success": False, "error": "Max retries exceeded"}

    except SpriggyAPIError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Unexpected error syncing block {block_id}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    autoretry_for=(SpriggyAPIError,),
    retry_backoff=True,
    retry_backoff_max=960,
    retry_jitter=True
)
def sync_block_clearance(self, block_id: str, user_id: str) -> dict:
    """
    Sync block clearance to Spriggy API.

    This task is triggered when a block is cleared locally but
    sync to Spriggy fails. It retries with exponential backoff.

    Args:
        block_id: UUID of the OnboardingBlock
        user_id: UUID of the user who cleared the block

    Returns:
        Dict with sync result
    """
    db = SessionLocal()
    try:
        from src.models.onboarding_block import OnboardingBlock, BlockSyncStatus
        from src.services.spriggy_client import SpriggyClient

        block = db.query(OnboardingBlock).filter(
            OnboardingBlock.id == UUID(block_id)
        ).first()

        if not block:
            logger.error(f"Block {block_id} not found")
            return {"success": False, "error": "Block not found"}

        if block.is_active:
            logger.info(f"Block {block_id} is still active, skipping clearance sync")
            return {"success": True, "skipped": True}

        client = SpriggyClient()
        try:
            client.clear_block(
                customer_id=block.customer_id,
                spriggy_block_id=block.spriggy_block_id
            )
            block.sync_status = BlockSyncStatus.CLEARED
            block.last_sync_error = None
            db.commit()
            logger.info(f"Successfully synced block clearance for {block_id}")
            return {"success": True, "block_id": block_id}
        except SpriggyAPIError as e:
            block.last_sync_error = f"Clearance sync failed: {e}"
            block.sync_attempts = str(int(block.sync_attempts) + 1)
            db.commit()
            raise

    except SpriggyAPIError:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Unexpected error syncing block clearance {block_id}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


@shared_task
def retry_failed_block_syncs() -> dict:
    """
    Periodic task to retry failed block syncs.

    This task runs periodically to pick up any blocks that failed
    to sync and haven't been retried via individual tasks.

    Returns:
        Dict with retry results
    """
    db = SessionLocal()
    try:
        service = OnboardingBlockService(db)
        pending_blocks = service.get_pending_sync_blocks(limit=50)

        results = {
            "total": len(pending_blocks),
            "succeeded": 0,
            "failed": 0,
            "skipped": 0
        }

        for block in pending_blocks:
            if not block.should_retry():
                results["skipped"] += 1
                continue

            if service.retry_sync(block):
                results["succeeded"] += 1
            else:
                results["failed"] += 1

        db.commit()
        logger.info(f"Retry failed syncs completed: {results}")
        return results

    except Exception as e:
        db.rollback()
        logger.exception("Error in retry_failed_block_syncs")
        return {"error": str(e)}
    finally:
        db.close()


@shared_task
def notify_block_sync_failures() -> dict:
    """
    Notify operations team about persistent block sync failures.

    This task runs periodically to alert about blocks that have
    exceeded retry limits and need manual intervention.

    Returns:
        Dict with notification results
    """
    db = SessionLocal()
    try:
        from src.models.onboarding_block import OnboardingBlock, BlockSyncStatus

        # Find blocks that have failed max retries
        failed_blocks = db.query(OnboardingBlock).filter(
            OnboardingBlock.sync_status == BlockSyncStatus.SYNC_FAILED,
            OnboardingBlock.is_active == True,
            OnboardingBlock.sync_attempts >= "5"  # String comparison
        ).all()

        if not failed_blocks:
            return {"notifications_sent": 0}

        # Send notification (would integrate with notification service)
        from src.services.notification_service import NotificationService
        from src.models.user import User, UserRole

        notification_service = NotificationService(db)

        # Notify AML managers
        managers = db.query(User).filter(
            User.role == UserRole.AML_MANAGER,
            User.is_active == True
        ).all()

        for manager in managers:
            notification_service.create_notification(
                user_id=manager.id,
                title="Onboarding Block Sync Failures",
                message=f"{len(failed_blocks)} onboarding blocks have failed to sync with Spriggy API and require manual intervention.",
                notification_type="ALERT",
                priority="HIGH"
            )

        db.commit()
        logger.warning(f"Notified {len(managers)} managers about {len(failed_blocks)} failed block syncs")
        return {"notifications_sent": len(managers), "failed_blocks": len(failed_blocks)}

    except Exception as e:
        db.rollback()
        logger.exception("Error in notify_block_sync_failures")
        return {"error": str(e)}
    finally:
        db.close()
