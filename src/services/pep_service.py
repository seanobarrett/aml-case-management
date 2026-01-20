"""
PEP (Politically Exposed Person) service.

References:
- FR-030: PEP confidence threshold classification
- FR-031: High-confidence PEP blocks onboarding
- FR-032: Low-confidence PEP provisional onboarding
- EC-011: Threshold boundary logic
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.case import Case, CaseType, CaseTier
from src.models.pep_threshold_config import PEPThresholdConfig
from src.models.onboarding_block import OnboardingBlock, BlockReason
from src.services.onboarding_block_service import OnboardingBlockService


logger = logging.getLogger(__name__)


class PEPClassification:
    """Result of PEP classification."""

    def __init__(
        self,
        is_high_confidence: bool,
        score: int,
        threshold: int,
        case_type: CaseType,
        requires_block: bool,
        tier: CaseTier
    ):
        self.is_high_confidence = is_high_confidence
        self.score = score
        self.threshold = threshold
        self.case_type = case_type
        self.requires_block = requires_block
        self.tier = tier


class PEPService:
    """
    Service for PEP-related operations.

    Handles classification of PEP matches and determination
    of required actions (blocking, EDD, etc.).
    """

    def __init__(self, db: Session):
        self.db = db

    def classify_pep_match(self, match_score: int) -> PEPClassification:
        """
        Classify a PEP match based on confidence score.

        Per EC-011:
        - Score > threshold = HIGH confidence (blocks, requires EDD)
        - Score <= threshold = LOW confidence (provisional, monitoring)

        Args:
            match_score: PEP match score (0-100)

        Returns:
            PEPClassification with details
        """
        threshold = self._get_active_threshold()

        # EC-011: Score equal to threshold is LOW confidence
        is_high_confidence = match_score > threshold

        if is_high_confidence:
            return PEPClassification(
                is_high_confidence=True,
                score=match_score,
                threshold=threshold,
                case_type=CaseType.PEP_HIGH_CONFIDENCE,
                requires_block=True,
                tier=CaseTier.L2  # High-confidence goes to L2
            )
        else:
            return PEPClassification(
                is_high_confidence=False,
                score=match_score,
                threshold=threshold,
                case_type=CaseType.PEP_LOW_CONFIDENCE,
                requires_block=False,
                tier=CaseTier.L1  # Low-confidence stays at L1
            )

    def create_block_for_high_confidence_pep(
        self,
        customer_id: str,
        case_id: UUID
    ) -> Optional[OnboardingBlock]:
        """
        Create onboarding block for high-confidence PEP.

        Args:
            customer_id: External customer identifier
            case_id: Associated case ID

        Returns:
            Created OnboardingBlock or None if not required
        """
        block_service = OnboardingBlockService(self.db)

        block = block_service.create_block(
            customer_id=customer_id,
            case_id=case_id,
            reason=BlockReason.HIGH_CONFIDENCE_PEP
        )

        logger.info(
            f"Created onboarding block for high-confidence PEP: "
            f"customer={customer_id}, case={case_id}"
        )

        return block

    def update_case_for_pep_classification(
        self,
        case: Case,
        classification: PEPClassification
    ) -> Case:
        """
        Update case based on PEP classification.

        Args:
            case: Case to update
            classification: PEP classification result

        Returns:
            Updated Case
        """
        case.case_type = classification.case_type
        case.tier = classification.tier

        # Set enhanced monitoring for low-confidence PEP
        if not classification.is_high_confidence:
            case.enhanced_monitoring = True

        logger.info(
            f"Updated case {case.case_reference} for PEP classification: "
            f"type={classification.case_type.value}, tier={classification.tier.value}"
        )

        return case

    def process_pep_alert(
        self,
        case: Case,
        customer_id: str,
        match_score: int
    ) -> tuple[Case, Optional[OnboardingBlock]]:
        """
        Process a PEP alert for a case.

        Classifies the PEP match, updates the case, and creates
        a block if required.

        Args:
            case: Case to process
            customer_id: External customer identifier
            match_score: PEP match score

        Returns:
            Tuple of (updated Case, OnboardingBlock or None)
        """
        # Classify the match
        classification = self.classify_pep_match(match_score)

        # Update case
        case = self.update_case_for_pep_classification(case, classification)

        # Create block if required
        block = None
        if classification.requires_block:
            block = self.create_block_for_high_confidence_pep(
                customer_id=customer_id,
                case_id=case.id
            )

        return case, block

    def _get_active_threshold(self) -> int:
        """Get the active PEP threshold value."""
        return PEPThresholdConfig.get_active_threshold(self.db)

    def get_threshold_config(self) -> dict:
        """Get current threshold configuration."""
        threshold = self._get_active_threshold()
        return {
            "thresholdValue": threshold,
            "highConfidenceDescription": f"Score > {threshold}",
            "lowConfidenceDescription": f"Score <= {threshold}"
        }

    def update_threshold(
        self,
        new_threshold: int,
        user_id: UUID,
        reason: str
    ) -> PEPThresholdConfig:
        """
        Update the PEP confidence threshold.

        Args:
            new_threshold: New threshold value (0-100)
            user_id: User making the change
            reason: Reason for the change

        Returns:
            New PEPThresholdConfig

        Raises:
            ValueError: If threshold is invalid
        """
        if new_threshold < 0 or new_threshold > 100:
            raise ValueError("Threshold must be between 0 and 100")

        config = PEPThresholdConfig.create_new_threshold(
            db=self.db,
            threshold_value=new_threshold,
            created_by_id=user_id,
            change_reason=reason
        )

        logger.info(
            f"PEP threshold updated to {new_threshold} by user {user_id}: {reason}"
        )

        return config
