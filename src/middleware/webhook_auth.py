"""
HMAC webhook authentication middleware.

References:
- D11: HMAC signature validation for GreenID/Indue webhooks
"""

import hashlib
import hmac
import os
from typing import Callable, Optional

from fastapi import HTTPException, Request, status


# Webhook secrets (loaded from environment)
GREENID_WEBHOOK_SECRET = os.getenv("GREENID_WEBHOOK_SECRET", "")
INDUE_WEBHOOK_SECRET = os.getenv("INDUE_WEBHOOK_SECRET", "")

# Header names for signatures
SIGNATURE_HEADER = "X-Webhook-Signature"
TIMESTAMP_HEADER = "X-Webhook-Timestamp"


class WebhookAuthError(HTTPException):
    """Raised when webhook authentication fails."""

    def __init__(self, detail: str = "Invalid webhook signature"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )


def validate_hmac_signature(
    payload: bytes,
    signature: str,
    secret: str,
    algorithm: str = "sha256"
) -> bool:
    """
    Validate HMAC signature of webhook payload.

    Args:
        payload: Raw request body bytes
        signature: Signature from header
        secret: Webhook secret key
        algorithm: Hash algorithm (default: sha256)

    Returns:
        True if signature is valid
    """
    if not secret:
        # If no secret configured, allow in development
        return os.getenv("ENVIRONMENT", "development") == "development"

    if not signature:
        return False

    # Compute expected signature
    expected = hmac.new(
        secret.encode(),
        payload,
        getattr(hashlib, algorithm)
    ).hexdigest()

    # Use constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected, signature)


def get_signature_from_header(
    header_value: str,
    prefix: Optional[str] = None
) -> str:
    """
    Extract signature from header value.

    Handles formats like:
    - 'sha256=abc123...'
    - 'v1,sha256=abc123...'
    - 'abc123...' (raw)

    Args:
        header_value: Raw header value
        prefix: Expected prefix to strip

    Returns:
        Extracted signature
    """
    if not header_value:
        return ""

    # Handle prefix formats
    if "=" in header_value:
        parts = header_value.split("=", 1)
        if len(parts) == 2:
            return parts[1]

    return header_value


async def verify_greenid_webhook(request: Request) -> bool:
    """
    Verify GreenID webhook signature.

    Args:
        request: FastAPI request

    Returns:
        True if signature is valid

    Raises:
        WebhookAuthError: If signature is invalid
    """
    signature = request.headers.get(SIGNATURE_HEADER, "")

    if not signature:
        raise WebhookAuthError("Missing webhook signature header")

    # Get raw body for signature verification
    body = await request.body()

    # Extract signature value
    sig_value = get_signature_from_header(signature)

    if not validate_hmac_signature(body, sig_value, GREENID_WEBHOOK_SECRET):
        raise WebhookAuthError("Invalid GreenID webhook signature")

    return True


async def verify_indue_webhook(request: Request) -> bool:
    """
    Verify Indue webhook signature.

    Args:
        request: FastAPI request

    Returns:
        True if signature is valid

    Raises:
        WebhookAuthError: If signature is invalid
    """
    signature = request.headers.get(SIGNATURE_HEADER, "")

    if not signature:
        raise WebhookAuthError("Missing webhook signature header")

    # Get raw body for signature verification
    body = await request.body()

    # Extract signature value
    sig_value = get_signature_from_header(signature)

    if not validate_hmac_signature(body, sig_value, INDUE_WEBHOOK_SECRET):
        raise WebhookAuthError("Invalid Indue webhook signature")

    return True


def create_webhook_signature(payload: bytes, secret: str) -> str:
    """
    Create HMAC signature for a payload.

    Useful for testing and webhook replay.

    Args:
        payload: Raw payload bytes
        secret: Webhook secret key

    Returns:
        HMAC signature string
    """
    return hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
