"""
PEP threshold configuration model.

References:
- FR-030: PEP confidence threshold classification
- EC-011: Threshold boundary logic (equal to threshold = low confidence)
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, String, DateTime, Integer, Boolean, ForeignKey, Text
from src.models.base import DatabaseAgnosticUUID
from sqlalchemy.orm import relationship

from src.models.base import Base


class PEPThresholdConfig(Base):
    """
    Configuration for PEP confidence score thresholds.

    Determines whether a PEP match is classified as high or low confidence.
    Score > threshold = high confidence (blocks onboarding)
    Score <= threshold = low confidence (provisional onboarding allowed)
    """
    __tablename__ = "pep_threshold_configs"

    id = Column(DatabaseAgnosticUUID(), primary_key=True, default=uuid4)

    # Threshold value (0-100)
    threshold_value = Column(Integer, nullable=False, default=80)

    # Active configuration
    is_active = Column(Boolean, nullable=False, default=True)

    # Audit fields
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by_id = Column(DatabaseAgnosticUUID(), ForeignKey("users.id"), nullable=True)
    effective_from = Column(DateTime, nullable=False, default=datetime.utcnow)
    effective_to = Column(DateTime, nullable=True)

    # Change reason
    change_reason = Column(Text, nullable=True)

    # Previous config reference (for audit trail)
    previous_config_id = Column(DatabaseAgnosticUUID(), ForeignKey("pep_threshold_configs.id"), nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    previous_config = relationship("PEPThresholdConfig", remote_side=[id])

    @classmethod
    def get_active_threshold(cls, db) -> int:
        """
        Get the current active threshold value.

        Returns default of 80 if no configuration exists.
        """
        config = db.query(cls).filter(
            cls.is_active == True,
            cls.effective_from <= datetime.utcnow()
        ).order_by(cls.effective_from.desc()).first()

        if config:
            return config.threshold_value

        return 80  # Default threshold

    @classmethod
    def create_new_threshold(
        cls,
        db,
        threshold_value: int,
        created_by_id: UUID,
        change_reason: str = None
    ) -> "PEPThresholdConfig":
        """
        Create a new threshold configuration.

        Deactivates the current active config and creates a new one.
        """
        # Get current active config
        current_config = db.query(cls).filter(
            cls.is_active == True
        ).first()

        # Deactivate current config
        if current_config:
            current_config.is_active = False
            current_config.effective_to = datetime.utcnow()

        # Create new config
        new_config = cls(
            threshold_value=threshold_value,
            is_active=True,
            created_by_id=created_by_id,
            change_reason=change_reason,
            previous_config_id=current_config.id if current_config else None
        )

        db.add(new_config)
        return new_config

    def is_high_confidence(self, score: int) -> bool:
        """
        Determine if a score indicates high confidence.

        Per EC-011, score must be GREATER THAN threshold
        to be classified as high confidence.
        """
        return score > self.threshold_value

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "thresholdValue": self.threshold_value,
            "isActive": self.is_active,
            "effectiveFrom": self.effective_from.isoformat() if self.effective_from else None,
            "effectiveTo": self.effective_to.isoformat() if self.effective_to else None,
            "changeReason": self.change_reason,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "createdById": str(self.created_by_id) if self.created_by_id else None,
        }
