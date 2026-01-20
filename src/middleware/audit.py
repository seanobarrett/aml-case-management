"""
Audit middleware for automatic action logging.

Provides request/response interception to automatically log
actions to the audit trail.

References:
- FR-058: All case actions logged immutably
- FR-059: Case view events logged
- FR-060: User attribution on all entries
"""

import re
from typing import Callable, Optional
from uuid import UUID

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.db.session import SessionLocal
from src.services.audit_service import AuditService
from src.models.audit_log import AuditActionType


# Patterns for endpoints that should trigger audit logging
AUDIT_PATTERNS = {
    # Case views - GET /cases/{uuid}
    (r"^/cases/([0-9a-f-]{36})$", "GET"): AuditActionType.CASE_VIEWED,
}

# Patterns for endpoints where auditing is handled by the service layer
SERVICE_AUDITED = {
    "POST /webhooks/greenid",
    "POST /webhooks/indue",
    "POST /cases/{case_id}/claim",
    "POST /cases/{case_id}/close",
    "POST /cases/{case_id}/escalate",
}


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware that automatically logs certain actions to the audit trail.

    For case view events, this middleware intercepts the request and
    creates an audit entry. For mutations, auditing is typically handled
    in the service layer for more context.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Process request and log audit events.

        Args:
            request: Incoming request
            call_next: Next handler in chain

        Returns:
            Response from downstream handler
        """
        # Process the request
        response = await call_next(request)

        # Only audit successful responses
        if response.status_code >= 200 and response.status_code < 300:
            await self._maybe_audit(request)

        return response

    async def _maybe_audit(self, request: Request) -> None:
        """
        Check if request should be audited and create entry if so.

        Args:
            request: The request to potentially audit
        """
        path = request.url.path
        method = request.method

        # Check if this is a case view (FR-059)
        if method == "GET" and path.startswith("/cases/"):
            case_id = self._extract_case_id(path)
            if case_id:
                await self._log_case_view(request, case_id)

    def _extract_case_id(self, path: str) -> Optional[UUID]:
        """
        Extract case ID from path.

        Args:
            path: Request path

        Returns:
            Case UUID if found
        """
        # Match /cases/{uuid}
        match = re.match(r"^/cases/([0-9a-f-]{36})$", path)
        if match:
            try:
                return UUID(match.group(1))
            except ValueError:
                return None
        return None

    async def _log_case_view(self, request: Request, case_id: UUID) -> None:
        """
        Log a case view event.

        Args:
            request: The view request
            case_id: ID of viewed case
        """
        # Get user ID from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        if not user_id:
            # Try to extract from token in header
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                # In a real implementation, decode the token
                # For now, skip if we can't identify the user
                return

        # Get client info
        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent")

        # Create audit entry
        db = SessionLocal()
        try:
            service = AuditService(db)
            service.log_case_viewed(
                case_id=case_id,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            db.commit()
        except Exception:
            db.rollback()
            # Don't fail the request if audit fails
            # But log the error in production
            pass
        finally:
            db.close()

    def _get_client_ip(self, request: Request) -> Optional[str]:
        """
        Get client IP address, handling proxies.

        Args:
            request: The request

        Returns:
            Client IP address
        """
        # Check X-Forwarded-For header (load balancer/proxy)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            # Take the first IP (original client)
            return forwarded.split(",")[0].strip()

        # Fall back to direct client
        if request.client:
            return request.client.host

        return None


def get_request_context(request: Request) -> dict:
    """
    Extract audit context from a request.

    Useful for service-layer auditing that needs request metadata.

    Args:
        request: FastAPI request

    Returns:
        Dict with ip_address and user_agent
    """
    middleware = AuditMiddleware(app=None)  # type: ignore
    return {
        "ip_address": middleware._get_client_ip(request),
        "user_agent": request.headers.get("user-agent"),
    }
