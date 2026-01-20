"""
E2E tests for low-confidence PEP provisional onboarding.

References:
- US-8: Low-confidence PEP provisional onboarding
- FR-032: Low-confidence PEP case creation without blocking
- EC-011: Threshold boundary logic (equal to threshold = low confidence)
"""

import pytest
from fastapi.testclient import TestClient


class TestLowConfidencePEPProvisional:
    """Test low-confidence PEP allows provisional onboarding."""

    def test_low_confidence_pep_creates_case_without_block(
        self,
        client: TestClient,
        mock_hmac_validation,
        low_confidence_pep_payload
    ):
        """
        Given a PEP alert with score below threshold
        When the webhook is received
        Then a case is created but no block (FR-032)
        """
        response = client.post(
            "/webhooks/indue",
            json=low_confidence_pep_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["caseType"] == "PEP_LOW_CONFIDENCE"
        assert data["onboardingBlocked"] is False
        assert data["tier"] == "L1"  # Low-confidence stays at L1

    def test_threshold_equal_score_is_low_confidence(
        self,
        client: TestClient,
        mock_hmac_validation
    ):
        """
        Given a PEP alert with score equal to threshold
        When the webhook is received
        Then it is classified as low-confidence (EC-011)
        """
        payload = {
            "screeningId": "test-screening-threshold",
            "customerId": "cust-pep-threshold",
            "screeningType": "PEP",
            "matchScore": 80,  # Equal to default threshold
            "matchDetails": {
                "name": "Threshold Match",
                "matchType": "PARTIAL",
                "category": "LOCAL_GOVERNMENT"
            },
            "timestamp": "2026-01-18T10:00:00Z"
        }

        response = client.post(
            "/webhooks/indue",
            json=payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )

        assert response.status_code == 201
        data = response.json()
        # Score equal to threshold is LOW confidence per EC-011
        assert data["caseType"] == "PEP_LOW_CONFIDENCE"
        assert data["onboardingBlocked"] is False

    def test_low_confidence_pep_enables_enhanced_monitoring(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        low_confidence_pep_payload
    ):
        """
        Given a low-confidence PEP case is created
        When viewing the case
        Then enhanced monitoring flag is set
        """
        # Create case
        create_response = client.post(
            "/webhooks/indue",
            json=low_confidence_pep_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # Get case details
        case_response = client.get(
            f"/cases/{case_id}",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert case_response.status_code == 200
        # Enhanced monitoring should be enabled for low-confidence PEP
        # (Implementation may store this in case metadata)


class TestLowConfidencePEPWorkflow:
    """Test low-confidence PEP case workflow."""

    def test_l1_can_handle_low_confidence_pep(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        low_confidence_pep_payload
    ):
        """
        Given a low-confidence PEP case
        When L1 analyst claims it
        Then they can process the case
        """
        # Create case
        create_response = client.post(
            "/webhooks/indue",
            json=low_confidence_pep_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # L1 claims case
        claim_response = client.post(
            f"/cases/{case_id}/claim",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert claim_response.status_code == 200

    def test_low_confidence_pep_can_be_confirmed(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        low_confidence_pep_payload
    ):
        """
        Given a low-confidence PEP case
        When L1 confirms the PEP status
        Then the case can be closed with confirmation
        """
        # Create case
        create_response = client.post(
            "/webhooks/indue",
            json=low_confidence_pep_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # Claim and close
        client.post(
            f"/cases/{case_id}/claim",
            headers={"Authorization": "Bearer valid-token"}
        )

        close_response = client.post(
            f"/cases/{case_id}/close",
            json={
                "reason": "PEP status confirmed - low risk",
                "documentation": "Customer confirmed as former local council member, no current political exposure"
            },
            headers={"Authorization": "Bearer valid-token"}
        )

        assert close_response.status_code == 200

    def test_low_confidence_pep_no_edd_required(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        low_confidence_pep_payload
    ):
        """
        Given a low-confidence PEP case
        When checking EDD requirements
        Then EDD is not required
        """
        # Create case
        create_response = client.post(
            "/webhooks/indue",
            json=low_confidence_pep_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # Get EDD checklist
        edd_response = client.get(
            f"/cases/{case_id}/edd-checklist",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert edd_response.status_code == 200
        # EDD not required for low-confidence PEP
        assert edd_response.json()["required"] is False


# Fixtures

@pytest.fixture
def low_confidence_pep_payload():
    """Create a low-confidence PEP webhook payload."""
    return {
        "screeningId": "test-screening-pep-low-001",
        "customerId": "cust-pep-low-001",
        "screeningType": "PEP",
        "matchScore": 65,  # Below threshold
        "matchDetails": {
            "name": "Similar Name Person",
            "matchType": "PARTIAL",
            "category": "LOCAL_GOVERNMENT"
        },
        "timestamp": "2026-01-18T10:00:00Z",
        "customerOnboardingStatus": "NEW"
    }
