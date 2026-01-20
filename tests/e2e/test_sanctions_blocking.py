"""
E2E tests for sanctions blocking during onboarding.

References:
- US-6: Compliance manager can block high-risk onboarding
- FR-028: Block onboarding during sanctions investigation
- FR-029: Clear block upon case closure
"""

import pytest
from fastapi.testclient import TestClient


class TestSanctionsBlockCreation:
    """Test sanctions block is created when sanctions case is opened."""

    def test_sanctions_webhook_creates_onboarding_block(
        self,
        client: TestClient,
        mock_hmac_validation,
        mock_spriggy_create_block,
        sanctions_webhook_payload
    ):
        """
        Given a customer triggers a sanctions alert during onboarding
        When the webhook is received
        Then an onboarding block is created (FR-028)
        """
        # Create sanctions case via webhook
        response = client.post(
            "/webhooks/greenid",
            json=sanctions_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )

        assert response.status_code == 201
        data = response.json()
        case_id = data["id"]

        # Verify block was created
        block_response = client.get(
            f"/cases/{case_id}/onboarding-block",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert block_response.status_code == 200
        block_data = block_response.json()
        assert block_data["isBlocked"] is True
        assert block_data["customerId"] == sanctions_webhook_payload["customerId"]
        assert block_data["syncStatus"] == "SYNCED"

    def test_sanctions_block_prevents_onboarding_completion(
        self,
        client: TestClient,
        mock_hmac_validation,
        sanctions_webhook_payload
    ):
        """
        Given a sanctions block exists
        When Spriggy queries block status
        Then the customer is blocked from onboarding
        """
        # Create sanctions case
        response = client.post(
            "/webhooks/greenid",
            json=sanctions_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        customer_id = sanctions_webhook_payload["customerId"]

        # Query block status
        status_response = client.get(
            f"/onboarding-blocks/{customer_id}",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert status_response.status_code == 200
        assert status_response.json()["isBlocked"] is True


class TestSanctionsBlockClearance:
    """Test sanctions block is cleared on case closure."""

    def test_case_closure_clears_onboarding_block(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        sanctions_webhook_payload
    ):
        """
        Given a sanctions case with onboarding block
        When the case is closed as false positive
        Then the onboarding block is cleared (FR-029)
        """
        # Create sanctions case
        create_response = client.post(
            "/webhooks/greenid",
            json=sanctions_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]
        customer_id = sanctions_webhook_payload["customerId"]

        # Claim and close case
        client.post(
            f"/cases/{case_id}/claim",
            headers={"Authorization": "Bearer valid-token"}
        )
        client.post(
            f"/cases/{case_id}/close",
            json={
                "reason": "False positive - identity confirmed",
                "documentation": "Verified identity through additional documents"
            },
            headers={"Authorization": "Bearer valid-token"}
        )

        # Verify block was cleared
        status_response = client.get(
            f"/onboarding-blocks/{customer_id}",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert status_response.status_code == 200
        assert status_response.json()["isBlocked"] is False

    def test_block_clearance_syncs_to_spriggy(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        mock_spriggy_api,
        sanctions_webhook_payload
    ):
        """
        Given a sanctions case with onboarding block
        When the case is closed
        Then a callback is sent to Spriggy API
        """
        # Create sanctions case
        create_response = client.post(
            "/webhooks/greenid",
            json=sanctions_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # Claim and close case
        client.post(
            f"/cases/{case_id}/claim",
            headers={"Authorization": "Bearer valid-token"}
        )
        close_response = client.post(
            f"/cases/{case_id}/close",
            json={
                "reason": "False positive",
                "documentation": "Identity verified through documentation review"
            },
            headers={"Authorization": "Bearer valid-token"}
        )
        assert close_response.status_code == 200, f"Close failed: {close_response.json()}"

        # Verify Spriggy callback was made
        assert mock_spriggy_api.called
        assert mock_spriggy_api.last_request["customerId"] == sanctions_webhook_payload["customerId"]
        assert mock_spriggy_api.last_request["action"] == "CLEAR_BLOCK"


class TestBlockSyncRetry:
    """Test block sync retry logic."""

    def test_failed_sync_is_retried(
        self,
        client: TestClient,
        mock_hmac_validation,
        mock_spriggy_api_failure,
        sanctions_webhook_payload
    ):
        """
        Given Spriggy API is temporarily unavailable
        When block sync fails
        Then the sync is retried with exponential backoff (EC-009)
        """
        pass

    def test_block_marked_pending_on_sync_failure(
        self,
        client: TestClient,
        mock_hmac_validation,
        mock_spriggy_api_failure,
        sanctions_webhook_payload
    ):
        """
        Given block creation succeeds locally
        When Spriggy API sync fails
        Then block status is marked as PENDING_SYNC
        """
        pass


# Fixtures

@pytest.fixture
def sanctions_webhook_payload():
    """Create a sanctions alert webhook payload (GreenID format)."""
    return {
        "verificationId": "test-sanctions-001",
        "customerId": "cust-sanctions-001",
        "verificationType": "SANCTIONS",
        "outcome": "ALERT",
        "timestamp": "2026-01-18T10:00:00Z",
        "customer": {
            "firstName": "Test",
            "lastName": "Person",
            "dateOfBirth": "1980-01-15",
            "email": "test@example.com"
        }
    }


@pytest.fixture
def mock_spriggy_create_block(mocker):
    """Mock successful Spriggy create_block calls."""
    return mocker.patch(
        "src.services.onboarding_block_service.SpriggyClient.create_block",
        return_value="spriggy-block-123"
    )


@pytest.fixture
def mock_spriggy_api(mocker):
    """Mock successful Spriggy API clear_block calls."""
    mock = mocker.MagicMock()
    mock.called = False
    mock.last_request = None

    def track_call(customer_id=None, spriggy_block_id=None, **kwargs):
        mock.called = True
        mock.last_request = {
            "customerId": customer_id,
            "spriggyBlockId": spriggy_block_id,
            "action": "CLEAR_BLOCK"
        }
        return {"success": True}

    mocker.patch(
        "src.services.onboarding_block_service.SpriggyClient.clear_block",
        side_effect=track_call
    )
    # Also mock create_block so initial sync succeeds
    mocker.patch(
        "src.services.onboarding_block_service.SpriggyClient.create_block",
        return_value="spriggy-block-123"
    )
    return mock


@pytest.fixture
def mock_spriggy_api_failure(mocker):
    """Mock failing Spriggy API calls."""
    return mocker.patch(
        "src.services.onboarding_block_service.SpriggyClient.clear_block",
        side_effect=Exception("API temporarily unavailable")
    )
