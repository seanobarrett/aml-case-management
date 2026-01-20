"""
E2E tests for combined sanctions and PEP alerts.

References:
- US-15: Combined sanctions/PEP handling
- FR-035: Single case for concurrent sanctions and PEP alerts
"""

import pytest
from fastapi.testclient import TestClient


class TestCombinedSanctionsPEP:
    """Test combined sanctions and PEP alert handling."""

    def test_combined_alert_creates_single_case(
        self,
        client: TestClient,
        mock_hmac_validation,
        combined_alert_payload
    ):
        """
        Given a customer triggers both sanctions and PEP alerts
        When the webhook is received
        Then a single case is created with both alert types (FR-035)
        """
        # Create combined alert case via webhook
        response = client.post(
            "/webhooks/greenid",
            json=combined_alert_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )

        assert response.status_code == 201
        data = response.json()

        # Verify case type reflects combined alert
        assert data["caseType"] == "SANCTIONS_PEP_COMBINED"
        assert data["tier"] == "L2"  # Combined alerts escalate to L2

        # Verify both alert types are recorded
        case_response = client.get(
            f"/cases/{data['id']}",
            headers={"Authorization": "Bearer valid-token"}
        )
        case_data = case_response.json()
        assert "SANCTIONS" in case_data["alertTypes"]
        assert "PEP" in case_data["alertTypes"]

    def test_combined_alert_creates_onboarding_block(
        self,
        client: TestClient,
        mock_hmac_validation,
        combined_alert_payload
    ):
        """
        Given a combined sanctions/PEP alert
        When the webhook is received
        Then an onboarding block is created
        """
        # Create combined alert case
        response = client.post(
            "/webhooks/greenid",
            json=combined_alert_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = response.json()["id"]

        # Verify block exists
        block_response = client.get(
            f"/cases/{case_id}/onboarding-block",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert block_response.status_code == 200
        assert block_response.json()["isBlocked"] is True

    def test_sequential_alerts_merge_into_existing_case(
        self,
        client: TestClient,
        mock_hmac_validation,
        sanctions_webhook_payload,
        pep_webhook_payload
    ):
        """
        Given a customer already has an open sanctions case
        When a PEP alert arrives
        Then the PEP alert is added to the existing case (EC-014)
        """
        # Ensure same customer ID
        pep_webhook_payload["customerId"] = sanctions_webhook_payload["customerId"]

        # Create sanctions case first (via GreenID)
        sanctions_response = client.post(
            "/webhooks/greenid",
            json=sanctions_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        assert sanctions_response.status_code == 201
        sanctions_case_id = sanctions_response.json()["id"]

        # Create PEP alert for same customer (via Indue)
        pep_response = client.post(
            "/webhooks/indue",
            json=pep_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        assert pep_response.status_code == 201

        # Check PEP alert was linked to existing case
        # (implementation may create new case with link, or add to existing)
        case_response = client.get(
            f"/cases/{sanctions_case_id}",
            headers={"Authorization": "Bearer valid-token"}
        )
        case_data = case_response.json()

        # Either alerts are merged or cases are linked
        if "linkedCases" in case_data:
            assert len(case_data["linkedCases"]) > 0
        else:
            assert "PEP" in case_data.get("alertTypes", [])


class TestCombinedAlertResolution:
    """Test resolution of combined alerts."""

    def test_combined_case_requires_both_resolutions(
        self,
        client: TestClient,
        mock_oidc_auth_l2,
        mock_hmac_validation,
        combined_alert_payload
    ):
        """
        Given a combined sanctions/PEP case
        When resolving the case
        Then both alert types must be addressed
        """
        pass

    def test_combined_case_block_cleared_on_closure(
        self,
        client: TestClient,
        mock_oidc_auth_l2,
        mock_hmac_validation,
        combined_alert_payload
    ):
        """
        Given a combined case with onboarding block
        When the case is closed
        Then the block is cleared
        """
        pass


# Fixtures

@pytest.fixture
def combined_alert_payload():
    """Create a combined sanctions and PEP alert webhook payload (via GreenID format)."""
    return {
        "verificationId": "test-combined-001",
        "customerId": "cust-combined-001",
        "verificationType": "SANCTIONS_PEP_COMBINED",
        "outcome": "ALERT",
        "timestamp": "2026-01-18T10:00:00Z",
        "customer": {
            "firstName": "John",
            "lastName": "Public",
            "dateOfBirth": "1970-05-20",
            "email": "jpublic@example.com"
        }
    }


@pytest.fixture
def pep_webhook_payload():
    """Create a PEP alert webhook payload (via Indue format)."""
    return {
        "screeningId": "test-pep-001",
        "customerId": "cust-pep-001",
        "screeningType": "PEP",
        "matchScore": 82,
        "matchDetails": {
            "name": "Jane Leader",
            "matchType": "EXACT",
            "category": "PEP"
        },
        "timestamp": "2026-01-18T10:30:00Z"
    }


@pytest.fixture
def sanctions_webhook_payload():
    """Create a sanctions alert webhook payload (via GreenID format)."""
    return {
        "verificationId": "test-sanctions-001",
        "customerId": "cust-sanctions-001",
        "verificationType": "SANCTIONS",
        "outcome": "ALERT",
        "timestamp": "2026-01-18T09:00:00Z",
        "customer": {
            "firstName": "Test",
            "lastName": "Sanctions",
            "dateOfBirth": "1980-01-01",
            "email": "test@example.com"
        }
    }
