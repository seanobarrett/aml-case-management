"""
User service for user management operations.

References:
- US-14: Role change case reassignment
- FR-026: Role change detection and case reassignment
- FR-027: Audit entry for each affected case
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.user import User, UserRole
from src.models.case import Case, CaseStatus, CaseTier
from src.models.assignment import Assignment, AssignmentReason
from src.services.audit_service import AuditService


class UserService:
    """Service for user management operations."""

    def __init__(self, db: Session):
        """
        Initialize user service.

        Args:
            db: Database session
        """
        self.db = db
        self.audit_service = AuditService(db)

    def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Get user by ID.

        Args:
            user_id: User UUID

        Returns:
            User instance or None
        """
        return self.db.query(User).filter(User.id == user_id).first()

    def update_user_role(
        self,
        user_id: UUID,
        new_role: UserRole,
        updated_by_id: UUID
    ) -> tuple[User, int]:
        """
        Update user role and handle case reassignment (FR-026).

        When a user's role changes, all their assigned cases are
        unassigned and returned to the queue.

        Args:
            user_id: User to update
            new_role: New role to assign
            updated_by_id: User making the change

        Returns:
            Tuple of (updated user, number of cases reassigned)
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        old_role = user.role
        user.role = new_role
        user.updated_at = datetime.utcnow()

        # Handle case reassignment if role changes affect case access
        reassigned_count = 0
        if self._role_change_requires_reassignment(old_role, new_role):
            reassigned_count = self._reassign_user_cases(
                user_id=user_id,
                reason=f"Role changed from {old_role.value} to {new_role.value}",
                changed_by_id=updated_by_id
            )

        self.db.commit()
        return user, reassigned_count

    def update_user_tier(
        self,
        user_id: UUID,
        new_tier: str,
        updated_by_id: UUID
    ) -> tuple[User, int]:
        """
        Update user tier and handle case reassignment.

        When a user's tier changes, cases of the old tier are unassigned.

        Args:
            user_id: User to update
            new_tier: New tier to assign (L1/L2)
            updated_by_id: User making the change

        Returns:
            Tuple of (updated user, number of cases reassigned)
        """
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User not found: {user_id}")

        old_tier = user.tier
        user.tier = new_tier
        user.updated_at = datetime.utcnow()

        # Handle case reassignment for tier mismatch
        reassigned_count = 0
        if old_tier != new_tier:
            reassigned_count = self._reassign_user_cases_for_tier_change(
                user_id=user_id,
                old_tier=old_tier,
                new_tier=new_tier,
                changed_by_id=updated_by_id
            )

        self.db.commit()
        return user, reassigned_count

    def _role_change_requires_reassignment(
        self,
        old_role: UserRole,
        new_role: UserRole
    ) -> bool:
        """
        Determine if role change requires case reassignment.

        Args:
            old_role: Previous role
            new_role: New role

        Returns:
            True if reassignment is needed
        """
        # Analyst roles can have cases
        analyst_roles = {UserRole.L1_ANALYST, UserRole.L2_ANALYST}

        # If changing FROM an analyst role to non-analyst, reassign
        if old_role in analyst_roles and new_role not in analyst_roles:
            return True

        return False

    def _reassign_user_cases(
        self,
        user_id: UUID,
        reason: str,
        changed_by_id: UUID
    ) -> int:
        """
        Reassign all cases from a user back to the queue.

        Creates audit entries for each affected case (FR-027).

        Args:
            user_id: User whose cases should be reassigned
            reason: Reason for reassignment
            changed_by_id: User who triggered the reassignment

        Returns:
            Number of cases reassigned
        """
        # Find all assigned cases for this user
        assigned_cases = self.db.query(Case).filter(
            Case.assigned_to_id == user_id,
            Case.status.in_([CaseStatus.ASSIGNED, CaseStatus.PENDING_INFORMATION])
        ).all()

        for case in assigned_cases:
            # Create assignment record with ROLE_CHANGE reason
            assignment = Assignment(
                case_id=case.id,
                user_id=user_id,
                reason=AssignmentReason.ROLE_CHANGE,
                unassigned_at=datetime.utcnow(),
                is_active=False  # Immediately unassigned
            )
            self.db.add(assignment)

            # Update case
            case.assigned_to_id = None
            case.status = CaseStatus.OPEN

            # Create audit entry (FR-027)
            self.audit_service.log_case_reassigned(
                case_id=case.id,
                old_assignee_id=user_id,
                reason=reason,
                changed_by_id=changed_by_id
            )

        return len(assigned_cases)

    def _reassign_user_cases_for_tier_change(
        self,
        user_id: UUID,
        old_tier: str,
        new_tier: str,
        changed_by_id: UUID
    ) -> int:
        """
        Reassign cases when user tier changes.

        When going from L1 to L2, L1 cases are unassigned.
        When going from L2 to L1, L2 cases are unassigned.

        Args:
            user_id: User whose tier changed
            old_tier: Previous tier
            new_tier: New tier
            changed_by_id: User who triggered the change

        Returns:
            Number of cases reassigned
        """
        # Map tier string to CaseTier enum
        tier_to_case_tier = {
            "L1": CaseTier.L1,
            "L2": CaseTier.L2
        }

        old_case_tier = tier_to_case_tier.get(old_tier)
        if not old_case_tier:
            return 0

        # Find assigned cases of the OLD tier (they can no longer work on these)
        assigned_cases = self.db.query(Case).filter(
            Case.assigned_to_id == user_id,
            Case.tier == old_case_tier,
            Case.status.in_([CaseStatus.ASSIGNED, CaseStatus.PENDING_INFORMATION])
        ).all()

        reason = f"Tier changed from {old_tier} to {new_tier}"

        for case in assigned_cases:
            # Create assignment record
            assignment = Assignment(
                case_id=case.id,
                user_id=user_id,
                reason=AssignmentReason.ROLE_CHANGE,  # Reuse for tier changes
                unassigned_at=datetime.utcnow(),
                is_active=False  # Immediately unassigned
            )
            self.db.add(assignment)

            # Update case
            case.assigned_to_id = None
            case.status = CaseStatus.OPEN

            # Create audit entry
            self.audit_service.log_case_reassigned(
                case_id=case.id,
                old_assignee_id=user_id,
                reason=reason,
                changed_by_id=changed_by_id
            )

        return len(assigned_cases)

    def list_users(
        self,
        role: Optional[UserRole] = None,
        tier: Optional[str] = None,
        is_active: bool = True
    ) -> list[User]:
        """
        List users with optional filtering.

        Args:
            role: Filter by role
            tier: Filter by tier
            is_active: Filter by active status

        Returns:
            List of matching users
        """
        query = self.db.query(User).filter(User.is_active == is_active)

        if role:
            query = query.filter(User.role == role)
        if tier:
            query = query.filter(User.tier == tier)

        return query.order_by(User.email).all()
