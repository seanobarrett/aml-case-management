"""
Case link service for managing relationships between cases.

References:
- FR-046: Case linking for related cases
- EC-014: New alerts for customers with open cases are linked
- FR-044, FR-045: Supplementary SMR cases
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.case import Case
from src.models.case_link import CaseLink, CaseLinkType
from src.models.notification import NotificationType
from src.services.notification_service import NotificationService


logger = logging.getLogger(__name__)


class CaseLinkService:
    """
    Service for managing case links.

    Handles creation and retrieval of links between related cases,
    including automatic linking for new alerts and supplementary SMRs.
    """

    def __init__(self, db: Session):
        self.db = db
        self.notification_service = NotificationService(db)

    def link_cases_for_new_alert(
        self,
        existing_case_id: UUID,
        new_case_id: UUID,
        description: str = None
    ) -> tuple[CaseLink, CaseLink]:
        """
        Link a new alert case to an existing open case (EC-014).

        Creates bidirectional links and notifies the assigned analyst.

        Args:
            existing_case_id: ID of the existing open case
            new_case_id: ID of the newly created case
            description: Optional description of the link

        Returns:
            Tuple of created CaseLink objects
        """
        # Check if link already exists
        existing_link = self.db.query(CaseLink).filter(
            CaseLink.source_case_id == existing_case_id,
            CaseLink.target_case_id == new_case_id,
            CaseLink.link_type == CaseLinkType.NEW_ALERT
        ).first()

        if existing_link:
            logger.info(f"Link already exists between {existing_case_id} and {new_case_id}")
            return existing_link, None

        # Create bidirectional links
        link_a, link_b = CaseLink.create_bidirectional_link(
            case_a_id=existing_case_id,
            case_b_id=new_case_id,
            link_type=CaseLinkType.NEW_ALERT,
            description=description or "New alert received for customer with existing open case"
        )

        self.db.add(link_a)
        self.db.add(link_b)
        self.db.flush()

        # Notify assigned analyst of existing case
        existing_case = self.db.query(Case).filter(Case.id == existing_case_id).first()
        new_case = self.db.query(Case).filter(Case.id == new_case_id).first()

        if existing_case and existing_case.assigned_to_id:
            self.notification_service.create_notification(
                user_id=existing_case.assigned_to_id,
                title="New Alert Linked to Your Case",
                message=f"A new alert ({new_case.case_reference}) has been received for the same customer and linked to case {existing_case.case_reference}.",
                notification_type=NotificationType.INFO,
                case_id=existing_case_id
            )

        logger.info(f"Created links between cases {existing_case_id} and {new_case_id}")
        return link_a, link_b

    def link_supplementary_case(
        self,
        original_case_id: UUID,
        supplementary_case_id: UUID,
        created_by_id: UUID = None
    ) -> tuple[CaseLink, CaseLink]:
        """
        Link a supplementary SMR case to the original case (FR-046).

        Args:
            original_case_id: ID of the original filed case
            supplementary_case_id: ID of the supplementary case
            created_by_id: User who created the supplementary case

        Returns:
            Tuple of created CaseLink objects
        """
        link_a, link_b = CaseLink.create_bidirectional_link(
            case_a_id=original_case_id,
            case_b_id=supplementary_case_id,
            link_type=CaseLinkType.SUPPLEMENTARY_TO_ORIGINAL,
            description="Supplementary SMR filing for original case",
            created_by_id=created_by_id,
            primary_case_id=original_case_id  # Original is primary
        )

        self.db.add(link_a)
        self.db.add(link_b)
        self.db.flush()

        logger.info(
            f"Created supplementary link: {supplementary_case_id} -> {original_case_id}"
        )
        return link_a, link_b

    def get_linked_cases(self, case_id: UUID) -> list[dict]:
        """
        Get all cases linked to a specific case.

        Args:
            case_id: ID of the case to get links for

        Returns:
            List of linked case info dicts
        """
        links = self.db.query(CaseLink).filter(
            CaseLink.source_case_id == case_id
        ).all()

        result = []
        for link in links:
            target_case = self.db.query(Case).filter(
                Case.id == link.target_case_id
            ).first()

            if target_case:
                result.append({
                    "linkId": str(link.id),
                    "caseId": str(target_case.id),
                    "caseReference": target_case.case_reference,
                    "caseType": target_case.case_type.value,
                    "status": target_case.status.value,
                    "linkType": link.link_type.value,
                    "description": link.description,
                    "isPrimary": link.is_primary == "true",
                    "createdAt": link.created_at.isoformat() if link.created_at else None,
                })

        return result

    def get_supplementary_cases(self, original_case_id: UUID) -> list[Case]:
        """
        Get all supplementary cases for an original case.

        Args:
            original_case_id: ID of the original case

        Returns:
            List of supplementary Case objects
        """
        links = self.db.query(CaseLink).filter(
            CaseLink.source_case_id == original_case_id,
            CaseLink.link_type == CaseLinkType.SUPPLEMENTARY_TO_ORIGINAL,
            CaseLink.is_primary == "true"  # Original case is primary
        ).all()

        supplementary_ids = [link.target_case_id for link in links]

        if not supplementary_ids:
            return []

        return self.db.query(Case).filter(
            Case.id.in_(supplementary_ids)
        ).all()

    def get_original_case(self, supplementary_case_id: UUID) -> Optional[Case]:
        """
        Get the original case for a supplementary case.

        Args:
            supplementary_case_id: ID of the supplementary case

        Returns:
            Original Case object or None
        """
        link = self.db.query(CaseLink).filter(
            CaseLink.source_case_id == supplementary_case_id,
            CaseLink.link_type == CaseLinkType.SUPPLEMENTARY_TO_ORIGINAL,
            CaseLink.is_primary == "false"  # Supplementary case is not primary
        ).first()

        if not link:
            return None

        return self.db.query(Case).filter(
            Case.id == link.target_case_id
        ).first()

    def unlink_cases(self, case_a_id: UUID, case_b_id: UUID) -> bool:
        """
        Remove links between two cases (both directions).

        Args:
            case_a_id: First case ID
            case_b_id: Second case ID

        Returns:
            True if links were removed
        """
        # Delete both directions
        deleted = self.db.query(CaseLink).filter(
            ((CaseLink.source_case_id == case_a_id) & (CaseLink.target_case_id == case_b_id)) |
            ((CaseLink.source_case_id == case_b_id) & (CaseLink.target_case_id == case_a_id))
        ).delete(synchronize_session='fetch')

        if deleted > 0:
            logger.info(f"Removed {deleted} links between {case_a_id} and {case_b_id}")
            return True

        return False
