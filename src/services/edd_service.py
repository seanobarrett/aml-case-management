"""
Enhanced Due Diligence (EDD) service.

References:
- US-7: High-confidence PEP requires EDD
- FR-033: EDD checklist requirements
- FR-034: EDD completion workflow
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.case import Case, CaseType
from src.models.edd_checklist import EDDChecklist, EDDChecklistItem, EDDItemType
from src.models.timeline_entry import TimelineEntry


logger = logging.getLogger(__name__)


class EDDService:
    """
    Service for Enhanced Due Diligence operations.

    Manages EDD checklists for high-confidence PEP cases.
    """

    def __init__(self, db: Session):
        self.db = db

    def create_checklist_for_case(self, case_id: UUID) -> EDDChecklist:
        """
        Create an EDD checklist for a case.

        Args:
            case_id: Case ID to create checklist for

        Returns:
            Created EDDChecklist with default items
        """
        # Check if checklist already exists
        existing = self.db.query(EDDChecklist).filter(
            EDDChecklist.case_id == case_id
        ).first()

        if existing:
            logger.info(f"EDD checklist already exists for case {case_id}")
            return existing

        # Create checklist
        checklist = EDDChecklist.create_for_case(case_id)
        self.db.add(checklist)
        self.db.flush()

        # Create default items
        items = EDDChecklistItem.create_default_items(checklist.id)
        for item in items:
            self.db.add(item)

        self.db.flush()

        logger.info(f"Created EDD checklist with {len(items)} items for case {case_id}")

        return checklist

    def get_checklist_for_case(self, case_id: UUID) -> Optional[EDDChecklist]:
        """
        Get the EDD checklist for a case.

        Args:
            case_id: Case ID

        Returns:
            EDDChecklist or None
        """
        return self.db.query(EDDChecklist).filter(
            EDDChecklist.case_id == case_id
        ).first()

    def is_edd_required_for_case(self, case: Case) -> bool:
        """
        Determine if EDD is required for a case.

        Args:
            case: Case to check

        Returns:
            True if EDD is required
        """
        return case.case_type == CaseType.PEP_HIGH_CONFIDENCE

    def update_checklist_items(
        self,
        case_id: UUID,
        user_id: UUID,
        items: list[dict]
    ) -> EDDChecklist:
        """
        Update checklist items with completion status.

        Args:
            case_id: Case ID
            user_id: User updating the items
            items: List of item updates [{itemId, completed, notes}]

        Returns:
            Updated EDDChecklist

        Raises:
            ValueError: If checklist not found
        """
        checklist = self.get_checklist_for_case(case_id)
        if not checklist:
            raise ValueError(f"EDD checklist not found for case {case_id}")

        # Update each item
        for item_update in items:
            item_type = item_update.get("itemId")
            completed = item_update.get("completed", False)
            notes = item_update.get("notes")

            # Find the item
            checklist_item = self.db.query(EDDChecklistItem).filter(
                EDDChecklistItem.checklist_id == checklist.id,
                EDDChecklistItem.item_type == EDDItemType(item_type)
            ).first()

            if checklist_item:
                if completed:
                    checklist_item.complete(user_id, notes)
                else:
                    checklist_item.is_completed = False
                    checklist_item.completed_at = None
                    checklist_item.completed_by_id = None
                    if notes:
                        checklist_item.notes = notes

        # Check if all required items are completed
        if checklist.all_items_completed:
            checklist.mark_completed(user_id)

            # Create timeline entry
            self._create_timeline_entry(
                case_id=case_id,
                user_id=user_id,
                content="EDD checklist completed"
            )

            logger.info(f"EDD checklist completed for case {case_id}")

        self.db.flush()

        return checklist

    def verify_edd_complete_for_closure(self, case_id: UUID) -> tuple[bool, str]:
        """
        Verify EDD is complete before allowing case closure.

        Args:
            case_id: Case ID

        Returns:
            Tuple of (is_complete, message)
        """
        checklist = self.get_checklist_for_case(case_id)

        if not checklist:
            return True, "No EDD checklist required"

        if not checklist.is_required:
            return True, "EDD not required for this case"

        if checklist.is_completed:
            return True, "EDD completed"

        # Find incomplete required items
        incomplete_items = [
            item for item in checklist.items
            if item.is_required and not item.is_completed
        ]

        if incomplete_items:
            item_names = [item.title for item in incomplete_items]
            return False, f"EDD incomplete. Missing: {', '.join(item_names)}"

        return True, "EDD complete"

    def _create_timeline_entry(
        self,
        case_id: UUID,
        user_id: UUID,
        content: str
    ) -> None:
        """Create a timeline entry for EDD events."""
        entry = TimelineEntry(
            case_id=case_id,
            acting_user_id=user_id,
            entry_type="EDD_UPDATE",
            content=content
        )
        self.db.add(entry)
