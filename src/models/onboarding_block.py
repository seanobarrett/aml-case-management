"""
Onboarding block model for sanctions/PEP blocking.

References:
- US-6: Block high-risk onboarding during investigation
- FR-028: Block onboarding during sanctions investigation
- FR-029: Clear block upon case closure
- EC-009: Sync status tracking for Spriggy API
"""

import enum
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Text, Boolean
from src.models.base import DatabaseAgnosticUUID
from sqlalchemy.orm import relationship

from src.models.base import Base


class BlockSyncStatus(enum.Enum):
    """Status of block synchronization with Spriggy API."""
    PENDING_SYNC = "PENDING_SYNC"  # Block created locally, not yet synced
    SYNCED = "SYNCED"  # Successfully synced with Spriggy
    SYNC_FAILED = "SYNC_FAILED"  # Sync failed, will retry
    CLEARED = "CLEARED"  # Block has been cleared


class BlockReason(enum.Enum):
    """Reason for onboarding block."""
    SANCTIONS_HIT = "SANCTIONS_HIT"
    HIGH_CONFIDENCE_PEP = "HIGH_CONFIDENCE_PEP"
    COMBINED_ALERT = "COMBINED_ALERT"


class OnboardingBlock(Base):
    """
    Tracks onboarding blocks for customers under investigation.

    When a sanctions or high-confidence PEP alert is received, an onboarding
    block is created to prevent the customer from completing onboarding
    until the case is resolved.

    The block status is synced with the Spriggy API. If sync fails,
    the system retries with exponential backoff (EC-009).
    """
    __tablename__ = "onboarding_blocks"

    id = Column(DatabaseAgnosticUUID(), primary_key=True, default=uuid4)
    customer_id = Column(String(100), nullable=False, index=True)
    case_id = Column(DatabaseAgnosticUUID(), ForeignKey("cases.id"), nullable=False)
    reason = Column(Enum(BlockReason), nullable=False)
    sync_status = Column(
        Enum(BlockSyncStatus),
        nullable=False,
        default=BlockSyncStatus.PENDING_SYNC
    )

    # Block state
    is_active = Column(Boolean, nullable=False, default=True)
    blocked_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    cleared_at = Column(DateTime, nullable=True)
    cleared_by_id = Column(DatabaseAgnosticUUID(), ForeignKey("users.id"), nullable=True)

    # Sync tracking for EC-009
    last_sync_attempt = Column(DateTime, nullable=True)
    sync_attempts = Column(String(10), nullable=False, default="0")  # Count as string for simplicity
    last_sync_error = Column(Text, nullable=True)
    spriggy_block_id = Column(String(100), nullable=True)  # ID returned by Spriggy API

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    case = relationship("Case", back_populates="onboarding_block")
    cleared_by = relationship("User", foreign_keys=[cleared_by_id])

    def mark_synced(self, spriggy_block_id: str) -> None:
        """Mark block as successfully synced with Spriggy."""
        self.sync_status = BlockSyncStatus.SYNCED
        self.spriggy_block_id = spriggy_block_id
        self.last_sync_attempt = datetime.utcnow()
        self.last_sync_error = None

    def mark_sync_failed(self, error: str) -> None:
        """Mark sync as failed and increment retry counter."""
        self.sync_status = BlockSyncStatus.SYNC_FAILED
        self.last_sync_attempt = datetime.utcnow()
        self.last_sync_error = error
        self.sync_attempts = str(int(self.sync_attempts) + 1)

    def clear(self, user_id: UUID) -> None:
        """Clear the onboarding block."""
        self.is_active = False
        self.cleared_at = datetime.utcnow()
        self.cleared_by_id = user_id
        self.sync_status = BlockSyncStatus.CLEARED

    @property
    def retry_count(self) -> int:
        """Get the number of sync retry attempts."""
        return int(self.sync_attempts)

    def should_retry(self, max_retries: int = 5) -> bool:
        """Check if sync should be retried."""
        return (
            self.sync_status == BlockSyncStatus.SYNC_FAILED and
            self.retry_count < max_retries and
            self.is_active
        )

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "customerId": self.customer_id,
            "caseId": str(self.case_id),
            "reason": self.reason.value,
            "syncStatus": self.sync_status.value,
            "isBlocked": self.is_active,
            "blockedAt": self.blocked_at.isoformat() if self.blocked_at else None,
            "clearedAt": self.cleared_at.isoformat() if self.cleared_at else None,
            "clearedById": str(self.cleared_by_id) if self.cleared_by_id else None,
            "retryCount": self.retry_count,
            "lastSyncError": self.last_sync_error,
        }
