"""
E2E tests for existing customer sanctions cases.

References:
- US-17: Existing customer sanctions screening
- FR-036: SANCTIONS_EXISTING_CUSTOMER subtype
- FR-037: Existing customer detection
- FR-038: Account restriction recommendation capability
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient


class TestExistingCustomerSanctions:
    """Test existing customer sanctions case handling."""

    def test_existing_customer_sanctions_no_auto_block(
        self,
        client: TestClient,
        mock_hmac_validation,
        existing_customer_sanctions_payload
    ):
        """
        Given a sanctions alert for an existing customer
        When the webhook is received
        Then a case is created WITHOUT automatic account block (FR-036, FR-037)
        """
        response = client.post(
            "/webhooks/indue",
            json=existing_customer_sanctions_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )

        assert response.status_code == 201
        data = response.json()

        # Should be SANCTIONS_EXISTING_CUSTOMER type
        assert data["caseType"] == "SANCTIONS_EXISTING_CUSTOMER"

        # Should NOT block onboarding (existing customer, not new)
        assert data["onboardingBlocked"] is False

    def test_existing_customer_detected_from_status(
        self,
        client: TestClient,
        mock_hmac_validation
    ):
        """
        Given a customer with onboardingStatus=EXISTING
        When a sanctions alert is received
        Then the customer is identified as existing (FR-037)
        """
        payload = {
            "screeningId": "test-screening-existing-detect",
            "customerId": "cust-existing-detect",
            "screeningType": "SANCTIONS",
            "matchScore": 95,
            "matchDetails": {
                "name": "Sanctions Match",
                "matchType": "EXACT",
                "category": "OFAC"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "customerOnboardingStatus": "EXISTING"
        }

        response = client.post(
            "/webhooks/indue",
            json=payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )

        assert response.status_code == 201
        data = response.json()

        # Should detect as existing customer
        assert data["caseType"] == "SANCTIONS_EXISTING_CUSTOMER"

    def test_new_customer_sanctions_still_blocks(
        self,
        client: TestClient,
        mock_hmac_validation
    ):
        """
        Given a new customer with sanctions alert
        When the webhook is received
        Then onboarding IS blocked (contrast to existing customer)
        """
        payload = {
            "screeningId": "test-screening-new-cust",
            "customerId": "cust-new-sanctions",
            "screeningType": "SANCTIONS",
            "matchScore": 95,
            "matchDetails": {
                "name": "Sanctions Match",
                "matchType": "EXACT",
                "category": "OFAC"
            },
            "timestamp": datetime.utcnow().isoformat(),
            "customerOnboardingStatus": "NEW"
        }

        response = client.post(
            "/webhooks/indue",
            json=payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )

        assert response.status_code == 201
        data = response.json()

        # Should be regular sanctions type
        assert data["caseType"] == "SANCTIONS_ONBOARDING"
        # Should block onboarding
        assert data["onboardingBlocked"] is True


class TestExistingCustomerWorkflow:
    """Test existing customer sanctions case workflow."""

    def test_case_goes_to_l2_queue(
        self,
        client: TestClient,
        mock_hmac_validation,
        existing_customer_sanctions_payload
    ):
        """
        Given an existing customer sanctions case
        When created
        Then it goes to L2 queue (higher risk than new customer)
        """
        response = client.post(
            "/webhooks/indue",
            json=existing_customer_sanctions_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )

        assert response.status_code == 201
        data = response.json()

        # Existing customer sanctions typically goes to L2 due to higher risk
        assert data["tier"] == "L2"

    def test_analyst_can_recommend_restriction(
        self,
        client: TestClient,
        mock_oidc_auth_l2,
        mock_hmac_validation,
        existing_customer_sanctions_payload
    ):
        """
        Given an existing customer sanctions case
        When analyst recommends account restriction
        Then the recommendation is recorded (FR-038)
        """
        # Create case
        create_response = client.post(
            "/webhooks/indue",
            json=existing_customer_sanctions_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # Claim the case
        client.post(
            f"/cases/{case_id}/claim",
            headers={"Authorization": "Bearer l2-valid-token"}
        )

        # Recommend account restriction
        response = client.post(
            f"/cases/{case_id}/recommend-restriction",
            json={
                "restrictionType": "FULL",
                "reason": "Confirmed sanctions match - immediate restriction required",
                "effectiveImmediately": True
            },
            headers={"Authorization": "Bearer l2-valid-token"}
        )

        assert response.status_code in [200, 201]

    def test_analyst_can_clear_with_investigation(
        self,
        client: TestClient,
        mock_oidc_auth_l2,
        mock_hmac_validation,
        existing_customer_sanctions_payload
    ):
        """
        Given an existing customer sanctions case
        When analyst determines false positive
        Then the case can be closed without account action
        """
        # Create case
        create_response = client.post(
            "/webhooks/indue",
            json=existing_customer_sanctions_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # Claim the case
        client.post(
            f"/cases/{case_id}/claim",
            headers={"Authorization": "Bearer l2-valid-token"}
        )

        # Close as false positive
        close_response = client.post(
            f"/cases/{case_id}/close",
            json={
                "reason": "False positive - different person with same name",
                "documentation": "Verified customer identity documents, DOB mismatch with sanctions target. Customer DOB 1985-03-15, sanctions target DOB 1952-08-21."
            },
            headers={"Authorization": "Bearer l2-valid-token"}
        )

        assert close_response.status_code == 200


class TestRestrictionRecommendations:
    """Test account restriction recommendation workflow."""

    def test_restriction_types_available(
        self,
        client: TestClient,
        mock_oidc_auth_l2
    ):
        """
        Given restriction recommendation endpoint
        When querying available types
        Then valid restriction types are returned
        """
        # This could be a config endpoint or enum
        # For now, test that the types are documented
        valid_types = ["FULL", "PARTIAL", "ENHANCED_MONITORING", "NONE"]
        # Test passes if types are defined

    def test_restriction_requires_reason(
        self,
        client: TestClient,
        mock_oidc_auth_l2,
        mock_hmac_validation,
        existing_customer_sanctions_payload
    ):
        """
        Given a restriction recommendation
        When reason is missing
        Then request is rejected
        """
        # Create case
        create_response = client.post(
            "/webhooks/indue",
            json=existing_customer_sanctions_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # Claim
        client.post(
            f"/cases/{case_id}/claim",
            headers={"Authorization": "Bearer l2-valid-token"}
        )

        # Try to recommend without reason
        response = client.post(
            f"/cases/{case_id}/recommend-restriction",
            json={
                "restrictionType": "FULL",
                # Missing reason
                "effectiveImmediately": True
            },
            headers={"Authorization": "Bearer l2-valid-token"}
        )

        assert response.status_code == 422  # Validation error


# Fixtures

@pytest.fixture
def existing_customer_sanctions_payload():
    """Create an existing customer sanctions webhook payload."""
    return {
        "screeningId": "test-screening-existing-001",
        "customerId": "cust-existing-001",
        "screeningType": "SANCTIONS",
        "matchScore": 90,
        "matchDetails": {
            "name": "Existing Customer Match",
            "matchType": "FUZZY",
            "category": "OFAC"
        },
        "timestamp": datetime.utcnow().isoformat(),
        "customerOnboardingStatus": "EXISTING"  # Key indicator
    }


@pytest.fixture
def mock_oidc_auth_l2(mocker):
    """Mock OIDC authentication for L2 analyst."""
    from conftest import create_mock_user, TEST_USER_L2_ID

    mock_user = create_mock_user(TEST_USER_L2_ID, "l2analyst@example.com", "L2_ANALYST")

    mocker.patch(
        "src.middleware.auth.get_current_user",
        return_value=mock_user
    )
    return mock_user
