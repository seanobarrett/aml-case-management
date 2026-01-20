"""
Onboarding block service for managing customer blocks.

References:
- US-6: Block high-risk onboarding during investigation
- FR-028: Block onboarding during sanctions investigation
- FR-029: Clear block upon case closure
- EC-009: Sync status tracking with retry logic
- D3: Circuit breaker for external API calls
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.onboarding_block import (
    OnboardingBlock,
    BlockReason,
    BlockSyncStatus,
)
from src.models.case import Case
from src.services.spriggy_client import SpriggyClient, SpriggyAPIError


logger = logging.getLogger(__name__)


class OnboardingBlockService:
    """
    Service for managing onboarding blocks.

    Handles creation, clearance, and synchronization of blocks
    with the Spriggy API.
    """

    def __init__(self, db: Session, spriggy_client: Optional[SpriggyClient] = None):
        self.db = db
        self.spriggy_client = spriggy_client or SpriggyClient()

    def create_block(
        self,
        customer_id: str,
        case_id: UUID,
        reason: BlockReason
    ) -> OnboardingBlock:
        """
        Create an onboarding block for a customer.

        The block is created locally first, then synced to Spriggy API.
        If sync fails, the block remains active locally and will be
        retried via background task.

        Args:
            customer_id: External customer identifier
            case_id: Associated case ID
            reason: Reason for the block

        Returns:
            Created OnboardingBlock
        """
        # Check for existing active block
        existing = self.db.query(OnboardingBlock).filter(
            OnboardingBlock.customer_id == customer_id,
            OnboardingBlock.is_active == True
        ).first()

        if existing:
            logger.info(
                f"Customer {customer_id} already has active block for case {existing.case_id}"
            )
            return existing

        # Create local block
        block = OnboardingBlock(
            customer_id=customer_id,
            case_id=case_id,
            reason=reason,
            sync_status=BlockSyncStatus.PENDING_SYNC
        )
        self.db.add(block)
        self.db.flush()

        # Attempt sync with Spriggy
        try:
            spriggy_block_id = self.spriggy_client.create_block(
                customer_id=customer_id,
                reason=reason.value,
                case_reference=str(case_id)
            )
            block.mark_synced(spriggy_block_id)
            logger.info(f"Block synced to Spriggy: {spriggy_block_id}")
        except SpriggyAPIError as e:
            block.mark_sync_failed(str(e))
            logger.warning(
                f"Failed to sync block to Spriggy for customer {customer_id}: {e}"
            )
            # Block remains active locally, will be retried

        return block

    def clear_block(
        self,
        case_id: UUID,
        user_id: UUID
    ) -> Optional[OnboardingBlock]:
        """
        Clear onboarding block when case is closed.

        Args:
            case_id: Case ID whose block should be cleared
            user_id: User clearing the block

        Returns:
            Cleared OnboardingBlock or None if no block exists
        """
        block = self.db.query(OnboardingBlock).filter(
            OnboardingBlock.case_id == case_id,
            OnboardingBlock.is_active == True
        ).first()

        if not block:
            logger.debug(f"No active block found for case {case_id}")
            return None

        # Clear locally
        block.clear(user_id)

        # Sync clearance with Spriggy
        try:
            self.spriggy_client.clear_block(
                customer_id=block.customer_id,
                spriggy_block_id=block.spriggy_block_id
            )
            logger.info(f"Block clearance synced to Spriggy for customer {block.customer_id}")
        except SpriggyAPIError as e:
            # Block is cleared locally, but sync failed
            # Will be retried via background task
            block.last_sync_error = f"Clearance sync failed: {e}"
            logger.warning(
                f"Failed to sync block clearance to Spriggy for customer {block.customer_id}: {e}"
            )

        return block

    def get_block_for_customer(self, customer_id: str) -> Optional[OnboardingBlock]:
        """
        Get active onboarding block for a customer.

        Args:
            customer_id: External customer identifier

        Returns:
            Active OnboardingBlock or None
        """
        return self.db.query(OnboardingBlock).filter(
            OnboardingBlock.customer_id == customer_id,
            OnboardingBlock.is_active == True
        ).first()

    def get_block_for_case(self, case_id: UUID) -> Optional[OnboardingBlock]:
        """
        Get onboarding block for a case.

        Args:
            case_id: Case ID

        Returns:
            OnboardingBlock or None
        """
        return self.db.query(OnboardingBlock).filter(
            OnboardingBlock.case_id == case_id
        ).first()

    def get_pending_sync_blocks(self, limit: int = 100) -> list[OnboardingBlock]:
        """
        Get blocks that need sync retry.

        Args:
            limit: Maximum blocks to return

        Returns:
            List of blocks needing sync
        """
        return self.db.query(OnboardingBlock).filter(
            OnboardingBlock.sync_status == BlockSyncStatus.SYNC_FAILED,
            OnboardingBlock.is_active == True
        ).limit(limit).all()

    def retry_sync(self, block: OnboardingBlock) -> bool:
        """
        Retry syncing a failed block.

        Args:
            block: Block to retry

        Returns:
            True if sync succeeded, False otherwise
        """
        if not block.should_retry():
            logger.info(f"Block {block.id} should not be retried")
            return False

        try:
            if block.spriggy_block_id:
                # Already synced, this is a clearance retry
                self.spriggy_client.clear_block(
                    customer_id=block.customer_id,
                    spriggy_block_id=block.spriggy_block_id
                )
            else:
                # Initial sync retry
                spriggy_block_id = self.spriggy_client.create_block(
                    customer_id=block.customer_id,
                    reason=block.reason.value,
                    case_reference=str(block.case_id)
                )
                block.mark_synced(spriggy_block_id)

            logger.info(f"Retry sync succeeded for block {block.id}")
            return True
        except SpriggyAPIError as e:
            block.mark_sync_failed(str(e))
            logger.warning(f"Retry sync failed for block {block.id}: {e}")
            return False

    def is_customer_blocked(self, customer_id: str) -> bool:
        """
        Check if a customer has an active onboarding block.

        Args:
            customer_id: External customer identifier

        Returns:
            True if blocked, False otherwise
        """
        block = self.get_block_for_customer(customer_id)
        return block is not None and block.is_active
