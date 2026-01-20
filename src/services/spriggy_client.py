"""
Spriggy API client with circuit breaker.

References:
- D3: Circuit breaker for external API calls
- EC-009: Retry logic for failed syncs
"""

import logging
import os
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

import httpx


logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"  # Failing, rejecting calls
    HALF_OPEN = "HALF_OPEN"  # Testing if service recovered


class SpriggyAPIError(Exception):
    """Error from Spriggy API."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class CircuitBreaker:
    """
    Circuit breaker for external API calls.

    Prevents cascading failures by stopping calls to a failing service
    and allowing it time to recover.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0

    def can_execute(self) -> bool:
        """Check if a call can be executed."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    logger.info("Circuit breaker entering HALF_OPEN state")
                    return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls

        return False

    def record_success(self) -> None:
        """Record a successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker CLOSED after successful recovery")
        else:
            self.failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker OPEN after half-open failure")
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker OPEN after {self.failure_count} failures"
            )


class SpriggyClient:
    """
    Client for Spriggy API with circuit breaker protection.

    Handles onboarding block creation and clearance with
    automatic retry and circuit breaker for resilience.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0
    ):
        self.base_url = base_url or os.getenv("SPRIGGY_API_URL", "https://api.spriggy.com.au")
        self.api_key = api_key or os.getenv("SPRIGGY_API_KEY", "")
        self.timeout = timeout
        self.circuit_breaker = CircuitBreaker()

    def _get_headers(self) -> dict:
        """Get request headers with authentication."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Client-Name": "aml-case-management",
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[dict] = None
    ) -> dict:
        """
        Make an API request with circuit breaker protection.

        Args:
            method: HTTP method
            endpoint: API endpoint
            json_data: Request body

        Returns:
            Response data

        Raises:
            SpriggyAPIError: On API error or circuit open
        """
        if not self.circuit_breaker.can_execute():
            raise SpriggyAPIError(
                "Circuit breaker is OPEN - Spriggy API temporarily unavailable",
                status_code=503
            )

        url = f"{self.base_url}{endpoint}"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(
                    method=method,
                    url=url,
                    json=json_data,
                    headers=self._get_headers()
                )

                if response.status_code >= 500:
                    self.circuit_breaker.record_failure()
                    raise SpriggyAPIError(
                        f"Spriggy API server error: {response.status_code}",
                        status_code=response.status_code
                    )

                if response.status_code >= 400:
                    raise SpriggyAPIError(
                        f"Spriggy API client error: {response.text}",
                        status_code=response.status_code
                    )

                self.circuit_breaker.record_success()
                return response.json()

        except httpx.TimeoutException:
            self.circuit_breaker.record_failure()
            raise SpriggyAPIError("Spriggy API timeout", status_code=504)
        except httpx.RequestError as e:
            self.circuit_breaker.record_failure()
            raise SpriggyAPIError(f"Spriggy API connection error: {e}")

    def create_block(
        self,
        customer_id: str,
        reason: str,
        case_reference: str
    ) -> str:
        """
        Create an onboarding block in Spriggy.

        Args:
            customer_id: Customer identifier
            reason: Reason for block
            case_reference: AML case reference

        Returns:
            Spriggy block ID

        Raises:
            SpriggyAPIError: On failure
        """
        response = self._make_request(
            method="POST",
            endpoint="/v1/onboarding/blocks",
            json_data={
                "customerId": customer_id,
                "reason": reason,
                "caseReference": case_reference,
                "source": "AML_COMPLIANCE"
            }
        )
        return response.get("blockId", "")

    def clear_block(
        self,
        customer_id: str,
        spriggy_block_id: Optional[str] = None
    ) -> bool:
        """
        Clear an onboarding block in Spriggy.

        Args:
            customer_id: Customer identifier
            spriggy_block_id: Spriggy's block ID (optional)

        Returns:
            True if cleared successfully

        Raises:
            SpriggyAPIError: On failure
        """
        endpoint = f"/v1/onboarding/blocks/{customer_id}"
        if spriggy_block_id:
            endpoint = f"/v1/onboarding/blocks/{spriggy_block_id}"

        self._make_request(
            method="DELETE",
            endpoint=endpoint,
            json_data={
                "action": "CLEAR_BLOCK",
                "customerId": customer_id,
                "source": "AML_COMPLIANCE"
            }
        )
        return True

    def get_block_status(self, customer_id: str) -> Optional[dict]:
        """
        Get current block status for a customer.

        Args:
            customer_id: Customer identifier

        Returns:
            Block status dict or None if not blocked
        """
        try:
            response = self._make_request(
                method="GET",
                endpoint=f"/v1/onboarding/blocks/customer/{customer_id}"
            )
            return response
        except SpriggyAPIError as e:
            if e.status_code == 404:
                return None
            raise
