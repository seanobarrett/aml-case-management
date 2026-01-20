"""
WebhookReceipt model for duplicate webhook detection.

References:
- D3: Async queue with duplicate detection
- EC-005: Duplicate webhook handling
"""

import hashlib
import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from src.models.base import DatabaseAgnosticUUID
from sqlalchemy.orm import Mapped

from src.models.base import Base, UUIDPrimaryKeyMixin


class WebhookReceipt(Base, UUIDPrimaryKeyMixin):
    """
    Record of received webhooks for duplicate detection.

    Each webhook payload is hashed and stored to detect duplicates.
    This prevents the same webhook from creating multiple cases.
    """

    __tablename__ = "webhook_receipts"

    # Payload hash for duplicate detection
    payload_hash: Mapped[str] = Column(
        String(64),
        nullable=False,
        unique=True,
        index=True
    )

    # Source webhook type
    webhook_source: Mapped[str] = Column(String(50), nullable=False)

    # External reference ID from webhook
    external_id: Mapped[Optional[str]] = Column(String(255), nullable=True)

    # Associated case (if created)
    case_id: Mapped[Optional[UUID]] = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("cases.id"),
        nullable=True
    )

    # Timestamps
    received_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )

    # Processing status
    processed: Mapped[bool] = Column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return f"<WebhookReceipt {self.webhook_source} hash={self.payload_hash[:8]}...>"

    @staticmethod
    def compute_payload_hash(payload: dict) -> str:
        """
        Compute SHA-256 hash of webhook payload.

        The payload is sorted by keys to ensure consistent hashing
        regardless of JSON key ordering.

        Args:
            payload: Webhook payload dictionary

        Returns:
            SHA-256 hash string (64 characters)
        """
        # Sort keys for consistent hashing
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(normalized.encode()).hexdigest()

    @classmethod
    def create(
        cls,
        payload: dict,
        webhook_source: str,
        external_id: Optional[str] = None
    ) -> "WebhookReceipt":
        """
        Create a new webhook receipt.

        Args:
            payload: Webhook payload dictionary
            webhook_source: Source webhook type ('greenid' or 'indue')
            external_id: External reference ID from payload

        Returns:
            New WebhookReceipt instance
        """
        return cls(
            payload_hash=cls.compute_payload_hash(payload),
            webhook_source=webhook_source,
            external_id=external_id,
        )

    def mark_processed(self, case_id: Optional[UUID] = None) -> None:
        """
        Mark this webhook as processed.

        Args:
            case_id: ID of created case, if any
        """
        self.processed = True
        self.case_id = case_id
