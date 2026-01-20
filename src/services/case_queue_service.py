"""
Case queue service for queue management and case claiming.

References:
- D13: Manual claim from queue - cases enter unassigned queue; analysts self-select
- FR-018: L2 review queue filtering
- FR-024: Cases filtered by status
- FR-025: Cases ordered by SLA priority
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.case import Case, CaseStatus, CaseTier, L2ReviewStatus
from src.models.assignment import Assignment, AssignmentReason
from src.models.user import User, UserRole


class CaseQueueService:
    """Service for queue management and case claiming."""

    def __init__(self, db: Session):
        self.db = db

    def get_unassigned_queue(
        self,
        tier: Optional[CaseTier] = None,
        case_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list[Case], int]:
        """
        Get unassigned cases ordered by SLA priority.

        Args:
            tier: Filter by tier
            case_type: Filter by case type
            page: Page number
            page_size: Items per page

        Returns:
            Tuple of (cases list, total count)
        """
        query = self.db.query(Case).filter(
            Case.status == CaseStatus.OPEN,
            Case.assigned_to_id.is_(None)
        )

        if tier:
            query = query.filter(Case.tier == tier)

        if case_type:
            query = query.filter(Case.case_type == case_type)

        # Get total count
        total = query.count()

        # Order by SLA deadline (earliest first)
        cases = (
            query
            .order_by(Case.sla_deadline.asc().nullslast())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return cases, total

    def get_l2_review_queue(self) -> list[Case]:
        """
        Get cases pending L2 quality review.

        Returns:
            List of cases with PENDING_REVIEW status
        """
        return (
            self.db.query(Case)
            .filter(Case.l2_review_status == L2ReviewStatus.PENDING_REVIEW)
            .order_by(Case.closed_at.asc())
            .all()
        )

    def claim_case(
        self,
        case_id: UUID,
        user_id: UUID,
        user_role: UserRole
    ) -> Case:
        """
        Claim a case for an analyst.

        Args:
            case_id: Case to claim
            user_id: User claiming the case
            user_role: Role of the claiming user

        Returns:
            Updated Case instance

        Raises:
            ValueError: If case is already assigned or user cannot claim this tier
        """
        case = self.db.query(Case).filter(Case.id == case_id).first()

        if not case:
            raise ValueError(f"Case not found: {case_id}")

        # Check if already assigned
        if case.assigned_to_id is not None:
            raise ValueError(f"Case is already assigned: {case.case_reference}")

        # Check tier access
        if not self._can_claim_tier(user_role, case.tier):
            raise ValueError(
                f"Role {user_role.value} cannot claim {case.tier.value} tier cases"
            )

        # Deactivate any existing assignments
        self.db.query(Assignment).filter(
            Assignment.case_id == case_id,
            Assignment.is_active == True
        ).update({Assignment.is_active: False})

        # Create new assignment
        assignment = Assignment.create_claim(case_id, user_id)
        self.db.add(assignment)

        # Update case
        case.assigned_to_id = user_id
        case.status = CaseStatus.ASSIGNED

        self.db.flush()
        return case

    def unassign_case(
        self,
        case_id: UUID,
        reason: AssignmentReason = AssignmentReason.ROLE_CHANGE
    ) -> Case:
        """
        Unassign a case, returning it to the queue.

        Args:
            case_id: Case to unassign
            reason: Reason for unassignment

        Returns:
            Updated Case instance
        """
        case = self.db.query(Case).filter(Case.id == case_id).first()

        if not case:
            raise ValueError(f"Case not found: {case_id}")

        # Deactivate current assignment
        current_assignment = (
            self.db.query(Assignment)
            .filter(
                Assignment.case_id == case_id,
                Assignment.is_active == True
            )
            .first()
        )

        if current_assignment:
            current_assignment.unassign()

        # Update case
        case.assigned_to_id = None
        if case.status == CaseStatus.ASSIGNED:
            case.status = CaseStatus.OPEN

        self.db.flush()
        return case

    def unassign_all_user_cases(
        self,
        user_id: UUID,
        reason: AssignmentReason = AssignmentReason.ROLE_CHANGE
    ) -> list[UUID]:
        """
        Unassign all cases from a user (e.g., on role change).

        Args:
            user_id: User whose cases to unassign
            reason: Reason for unassignment

        Returns:
            List of affected case IDs
        """
        # Find all active cases assigned to user
        cases = self.db.query(Case).filter(
            Case.assigned_to_id == user_id,
            Case.status.in_([CaseStatus.OPEN, CaseStatus.ASSIGNED])
        ).all()

        affected_ids = []
        for case in cases:
            self.unassign_case(case.id, reason)
            affected_ids.append(case.id)

        return affected_ids

    def accept_l2_review(
        self,
        case_id: UUID,
        reviewer_id: UUID
    ) -> Case:
        """
        Accept an L1 closure during L2 review.

        Args:
            case_id: Case to accept
            reviewer_id: L2 analyst accepting

        Returns:
            Updated Case instance
        """
        case = self.db.query(Case).filter(Case.id == case_id).first()

        if not case:
            raise ValueError(f"Case not found: {case_id}")

        if case.l2_review_status != L2ReviewStatus.PENDING_REVIEW:
            raise ValueError("Case is not pending L2 review")

        case.l2_review_status = L2ReviewStatus.REVIEWED_ACCEPTED
        self.db.flush()

        return case

    def reopen_from_l2_review(
        self,
        case_id: UUID,
        reviewer_id: UUID,
        reason: str
    ) -> Case:
        """
        Reopen a case from L2 review (reject L1 closure).

        Args:
            case_id: Case to reopen
            reviewer_id: L2 analyst reopening
            reason: Reason for reopening

        Returns:
            Updated Case instance
        """
        case = self.db.query(Case).filter(Case.id == case_id).first()

        if not case:
            raise ValueError(f"Case not found: {case_id}")

        if case.l2_review_status != L2ReviewStatus.PENDING_REVIEW:
            raise ValueError("Case is not pending L2 review")

        # Reopen the case
        case.reopen()

        # Assign to the L2 reviewer
        assignment = Assignment.create_reopen(case_id, reviewer_id)
        self.db.add(assignment)

        case.assigned_to_id = reviewer_id
        case.status = CaseStatus.ASSIGNED
        case.tier = CaseTier.L2  # Escalate to L2 tier

        self.db.flush()
        return case

    def _can_claim_tier(self, role: UserRole, tier: CaseTier) -> bool:
        """Check if a role can claim cases of a given tier."""
        if tier == CaseTier.L1:
            return role in (UserRole.L1_ANALYST, UserRole.L2_ANALYST, UserRole.AML_MANAGER)
        elif tier == CaseTier.L2:
            return role in (UserRole.L2_ANALYST, UserRole.AML_MANAGER)
        return False
