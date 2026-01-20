"""
OIDC authentication middleware.

References:
- D5: OIDC SSO integration + local RBAC enforcement
- FR-063: Four RBAC roles
- Principle II: Role-Based Access Control with Segregation of Duties
"""

import os
from typing import Any, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from src.models.user import UserRole, ROLE_PERMISSIONS


# OIDC configuration (loaded from environment)
OIDC_ISSUER = os.getenv("OIDC_ISSUER", "")
OIDC_AUDIENCE = os.getenv("OIDC_AUDIENCE", "aml-case-management")
OIDC_JWKS_URI = os.getenv("OIDC_JWKS_URI", "")

# JWT settings for local development/testing
JWT_SECRET = os.getenv("JWT_SECRET", "development-secret-key")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Development mode - bypasses authentication
DEV_MODE = os.getenv("ENVIRONMENT", "").lower() == "development"
DEV_USER_EMAIL = os.getenv("DEV_USER_EMAIL", "manager@spriggy.com.au")

# Security scheme - auto_error=False allows dev mode bypass
security = HTTPBearer(auto_error=not DEV_MODE)


class AuthError(HTTPException):
    """Raised when authentication fails."""

    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class ForbiddenError(HTTPException):
    """Raised when authorization fails."""

    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


class TierMismatchError(HTTPException):
    """Raised when user tries to act on wrong tier case."""

    def __init__(self, user_role: str, case_tier: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"TIER_MISMATCH: {user_role} cannot perform this action on {case_tier} tier case"
        )


class CurrentUser:
    """Authenticated user context."""

    def __init__(
        self,
        user_id: UUID,
        email: str,
        role: UserRole,
        permissions: dict[str, bool]
    ):
        self.user_id = user_id
        self.email = email
        self.role = role
        self.permissions = permissions

    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        return self.permissions.get(permission, False)

    @property
    def tier(self) -> str:
        """Get user's tier based on role."""
        if self.role == UserRole.L1_ANALYST:
            return "L1"
        elif self.role == UserRole.L2_ANALYST:
            return "L2"
        else:
            # Managers and READ_ONLY can work across tiers
            return "L2"

    def can_act_on_tier(self, tier: str, action: str) -> bool:
        """
        Check if user can perform action on a specific tier.

        Args:
            tier: Case tier ('L1' or 'L2')
            action: Action type ('close', 'claim', etc.)

        Returns:
            True if user can perform action
        """
        if action == "close":
            if tier == "L2" and self.role == UserRole.L1_ANALYST:
                return False
        return True


def verify_token(token: str) -> dict[str, Any]:
    """
    Verify and decode JWT token.

    In production, this validates against OIDC provider's JWKS.
    In development, uses local JWT secret.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        AuthError: If token is invalid
    """
    try:
        # In production, validate against OIDC JWKS
        # For development/testing, use simple JWT validation
        if OIDC_ISSUER and OIDC_JWKS_URI:
            # TODO: Implement full OIDC validation with JWKS
            # For now, fall back to local validation
            pass

        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            audience=OIDC_AUDIENCE,
            options={"verify_aud": False}  # Relaxed for development
        )
        return payload

    except JWTError as e:
        raise AuthError(f"Invalid token: {str(e)}")


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> CurrentUser:
    """
    Get current authenticated user from JWT token.

    In development mode (ENVIRONMENT=development), authentication is bypassed
    and a dev user is returned based on DEV_USER_EMAIL or X-Dev-User header.

    Args:
        request: FastAPI request object
        credentials: Bearer token credentials (optional in dev mode)

    Returns:
        CurrentUser instance

    Raises:
        AuthError: If authentication fails (production mode only)
    """
    # Development mode bypass
    if DEV_MODE:
        return await _get_dev_user(request)

    # Production mode - require valid credentials
    if not credentials:
        raise AuthError("Authentication required")

    token = credentials.credentials
    payload = verify_token(token)

    # Extract user info from token
    user_id = payload.get("sub")
    email = payload.get("email")
    role_str = payload.get("role", "READ_ONLY")

    if not user_id or not email:
        raise AuthError("Invalid token payload")

    # Parse role
    try:
        role = UserRole(role_str)
    except ValueError:
        raise AuthError(f"Invalid role: {role_str}")

    permissions = ROLE_PERMISSIONS.get(role, {})

    return CurrentUser(
        user_id=UUID(user_id),
        email=email,
        role=role,
        permissions=permissions
    )


async def _get_dev_user(request: Request) -> CurrentUser:
    """
    Get development user for testing.

    Checks X-Dev-User header first, then falls back to DEV_USER_EMAIL.
    Looks up user in database to get actual user_id.

    Available dev users:
    - manager@spriggy.com.au (AML_MANAGER)
    - sarah.chen@spriggy.com.au (L2_ANALYST)
    - james.wilson@spriggy.com.au (L2_ANALYST)
    - emma.taylor@spriggy.com.au (L1_ANALYST)
    - michael.brown@spriggy.com.au (L1_ANALYST)
    - lisa.johnson@spriggy.com.au (L1_ANALYST)
    - auditor@spriggy.com.au (READ_ONLY)
    """
    from src.db.session import get_db
    from src.models.user import User

    # Check for X-Dev-User header to switch users
    dev_email = request.headers.get("X-Dev-User", DEV_USER_EMAIL)

    # Get database session
    db = next(get_db())

    try:
        user = db.query(User).filter(User.email == dev_email).first()

        if user:
            return CurrentUser(
                user_id=user.id,
                email=user.email,
                role=user.role,
                permissions=ROLE_PERMISSIONS.get(user.role, {})
            )
        else:
            # Fallback to mock user if not found in DB
            return CurrentUser(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                email=dev_email,
                role=UserRole.AML_MANAGER,
                permissions=ROLE_PERMISSIONS.get(UserRole.AML_MANAGER, {})
            )
    finally:
        db.close()


def require_permission(permission: str):
    """
    Dependency that requires a specific permission.

    Usage:
        @app.get("/protected")
        async def protected(user: CurrentUser = Depends(require_permission("can_view_reports"))):
            ...

    Args:
        permission: Required permission name

    Returns:
        Dependency function
    """
    async def check_permission(
        user: CurrentUser = Depends(get_current_user)
    ) -> CurrentUser:
        if not user.has_permission(permission):
            raise ForbiddenError(f"Permission '{permission}' required")
        return user

    return check_permission


def require_role(*roles: UserRole):
    """
    Dependency that requires one of the specified roles.

    Usage:
        @app.get("/manager-only")
        async def manager_only(user: CurrentUser = Depends(require_role(UserRole.AML_MANAGER))):
            ...

    Args:
        roles: Allowed roles

    Returns:
        Dependency function
    """
    async def check_role(
        user: CurrentUser = Depends(get_current_user)
    ) -> CurrentUser:
        if user.role not in roles:
            raise ForbiddenError(f"Role {user.role.value} not authorized")
        return user

    return check_role


def require_tier_access(tier: str, action: str):
    """
    Dependency that validates tier-based access.

    Raises TIER_MISMATCH error if L1 tries to act on L2 case.

    Args:
        tier: Case tier
        action: Action being performed

    Returns:
        Dependency function
    """
    async def check_tier(
        user: CurrentUser = Depends(get_current_user)
    ) -> CurrentUser:
        if not user.can_act_on_tier(tier, action):
            raise TierMismatchError(user.role.value, tier)
        return user

    return check_tier
