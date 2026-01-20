"""
User model with RBAC roles.

References:
- FR-063: Four RBAC roles (L1, L2, Manager, ReadOnly)
- D5: OIDC SSO integration + local RBAC enforcement
- Principle II: Role-Based Access Control with Segregation of Duties
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Column, DateTime, String, Enum as SQLEnum
from sqlalchemy.orm import Mapped, relationship

from src.models.base import Base, UUIDPrimaryKeyMixin, VersionedMixin

if TYPE_CHECKING:
    from src.models.case import Case
    from src.models.assignment import Assignment


class UserRole(str, Enum):
    """
    User role enumeration for RBAC.

    Roles are hierarchical with strict segregation of duties:
    - L1_ANALYST: Initial triage, cannot approve SMRs
    - L2_ANALYST: Investigation, cannot approve own recommendations
    - AML_MANAGER: Approval authority
    - READ_ONLY: Viewing and reporting only
    """

    L1_ANALYST = "L1_ANALYST"
    L2_ANALYST = "L2_ANALYST"
    AML_MANAGER = "AML_MANAGER"
    READ_ONLY = "READ_ONLY"


# Role permissions mapping
ROLE_PERMISSIONS = {
    UserRole.L1_ANALYST: {
        "can_view_cases": True,
        "can_claim_cases": True,
        "can_close_l1_cases": True,
        "can_close_l2_cases": False,
        "can_escalate": True,
        "can_investigate": False,
        "can_recommend_smr": False,
        "can_approve_smr": False,
        "can_manage_users": False,
        "can_view_reports": False,
    },
    UserRole.L2_ANALYST: {
        "can_view_cases": True,
        "can_claim_cases": True,
        "can_close_l1_cases": True,
        "can_close_l2_cases": True,
        "can_escalate": False,
        "can_investigate": True,
        "can_recommend_smr": True,
        "can_approve_smr": False,
        "can_manage_users": False,
        "can_view_reports": True,
    },
    UserRole.AML_MANAGER: {
        "can_view_cases": True,
        "can_claim_cases": True,
        "can_close_l1_cases": True,
        "can_close_l2_cases": True,
        "can_escalate": True,
        "can_investigate": True,
        "can_recommend_smr": True,
        "can_approve_smr": True,
        "can_manage_users": True,
        "can_view_reports": True,
    },
    UserRole.READ_ONLY: {
        "can_view_cases": True,
        "can_claim_cases": False,
        "can_close_l1_cases": False,
        "can_close_l2_cases": False,
        "can_escalate": False,
        "can_investigate": False,
        "can_recommend_smr": False,
        "can_approve_smr": False,
        "can_manage_users": False,
        "can_view_reports": True,
    },
}


class User(Base, UUIDPrimaryKeyMixin, VersionedMixin):
    """
    System user with RBAC role.

    Users authenticate via OIDC SSO (D5) and are assigned one of four
    roles that determine their permissions within the system.
    """

    __tablename__ = "users"

    # Identity
    email: Mapped[str] = Column(String(255), nullable=False, unique=True, index=True)

    # RBAC role
    role: Mapped[UserRole] = Column(
        SQLEnum(UserRole, name="user_role", create_type=False),
        nullable=False
    )

    # Status
    is_active: Mapped[bool] = Column(Boolean, nullable=False, default=True)

    # Tier (L1 or L2 for analysts, null for managers/readonly)
    tier: Mapped[Optional[str]] = Column(String(10), nullable=True)

    # Relationships
    assigned_cases: Mapped[list["Case"]] = relationship(
        "Case",
        back_populates="assigned_to",
        foreign_keys="[Case.assigned_to_id]"
    )
    assignments: Mapped[list["Assignment"]] = relationship("Assignment", back_populates="user")

    def __repr__(self) -> str:
        return f"<User {self.email} [{self.role.value}]>"

    @property
    def permissions(self) -> dict[str, bool]:
        """Get permissions for this user's role."""
        return ROLE_PERMISSIONS.get(self.role, {})

    def has_permission(self, permission: str) -> bool:
        """
        Check if user has a specific permission.

        Args:
            permission: Permission name (e.g., 'can_approve_smr')

        Returns:
            True if user has the permission
        """
        if not self.is_active:
            return False
        return self.permissions.get(permission, False)

    def can_claim_tier(self, tier: str) -> bool:
        """
        Check if user can claim cases of a specific tier.

        Args:
            tier: Case tier ('L1' or 'L2')

        Returns:
            True if user can claim cases of this tier
        """
        if not self.is_active:
            return False

        if tier == "L1":
            return self.role in (UserRole.L1_ANALYST, UserRole.L2_ANALYST, UserRole.AML_MANAGER)
        elif tier == "L2":
            return self.role in (UserRole.L2_ANALYST, UserRole.AML_MANAGER)
        return False

    def can_close_tier(self, tier: str) -> bool:
        """
        Check if user can close cases of a specific tier.

        Returns TIER_MISMATCH error context if L1 tries to close L2 case.

        Args:
            tier: Case tier ('L1' or 'L2')

        Returns:
            True if user can close cases of this tier
        """
        if not self.is_active:
            return False

        if tier == "L1":
            return self.has_permission("can_close_l1_cases")
        elif tier == "L2":
            return self.has_permission("can_close_l2_cases")
        return False

    @property
    def is_l1_analyst(self) -> bool:
        """Check if user is L1 Analyst."""
        return self.role == UserRole.L1_ANALYST

    @property
    def is_l2_analyst(self) -> bool:
        """Check if user is L2 Analyst."""
        return self.role == UserRole.L2_ANALYST

    @property
    def is_manager(self) -> bool:
        """Check if user is AML Manager."""
        return self.role == UserRole.AML_MANAGER

    @property
    def is_read_only(self) -> bool:
        """Check if user is Read Only."""
        return self.role == UserRole.READ_ONLY
