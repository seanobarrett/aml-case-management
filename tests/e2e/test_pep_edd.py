"""
E2E tests for high-confidence PEP with Enhanced Due Diligence (EDD).

References:
- US-7: High-confidence PEP blocking with EDD
- FR-030: PEP confidence threshold classification
- FR-031: High-confidence PEP blocks onboarding
- FR-033: EDD checklist requirements
- FR-034: EDD completion workflow
"""

import pytest
from fastapi.testclient import TestClient


class TestHighConfidencePEPBlocking:
    """Test high-confidence PEP triggers onboarding block."""

    def test_high_confidence_pep_creates_block(
        self,
        client: TestClient,
        mock_hmac_validation,
        high_confidence_pep_payload
    ):
        """
        Given a PEP alert with score above threshold
        When the webhook is received
        Then an onboarding block is created (FR-031)
        """
        response = client.post(
            "/webhooks/indue",
            json=high_confidence_pep_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["caseType"] == "PEP_HIGH_CONFIDENCE"
        assert data["onboardingBlocked"] is True
        assert data["tier"] == "L2"  # High-confidence PEP goes to L2

    def test_high_confidence_pep_requires_edd(
        self,
        client: TestClient,
        mock_oidc_auth_l2,
        mock_hmac_validation,
        high_confidence_pep_payload
    ):
        """
        Given a high-confidence PEP case
        When viewing the case
        Then EDD checklist is required (FR-033)
        """
        # Create case
        create_response = client.post(
            "/webhooks/indue",
            json=high_confidence_pep_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # Get EDD checklist
        edd_response = client.get(
            f"/cases/{case_id}/edd-checklist",
            headers={"Authorization": "Bearer l2-valid-token"}
        )

        assert edd_response.status_code == 200
        checklist = edd_response.json()
        assert checklist["required"] is True
        assert len(checklist["items"]) > 0


class TestEDDCompletion:
    """Test EDD completion workflow."""

    def test_l2_can_complete_edd_checklist(
        self,
        client: TestClient,
        mock_oidc_auth_l2,
        mock_hmac_validation,
        high_confidence_pep_payload
    ):
        """
        Given a high-confidence PEP case with EDD requirements
        When L2 completes all EDD items
        Then the checklist is marked complete (FR-034)
        """
        # Create case
        create_response = client.post(
            "/webhooks/indue",
            json=high_confidence_pep_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        create_data = create_response.json()
        case_id = create_data["id"]
        assert create_data["caseType"] == "PEP_HIGH_CONFIDENCE", f"Wrong case type: {create_data['caseType']}"

        # Complete EDD checklist
        edd_response = client.post(
            f"/cases/{case_id}/edd-checklist",
            json={
                "items": [
                    {"itemId": "SOURCE_OF_WEALTH", "completed": True, "notes": "Verified salary income"},
                    {"itemId": "SOURCE_OF_FUNDS", "completed": True, "notes": "Bank statements reviewed"},
                    {"itemId": "PEP_RELATIONSHIP", "completed": True, "notes": "No current political exposure"},
                    {"itemId": "BUSINESS_PURPOSE", "completed": True, "notes": "Personal banking only"}
                ]
            },
            headers={"Authorization": "Bearer l2-valid-token"}
        )

        assert edd_response.status_code == 200, f"EDD update failed: {edd_response.json()}"
        data = edd_response.json()
        assert data["completed"] is True

    def test_edd_completion_clears_block(
        self,
        client: TestClient,
        mock_oidc_auth_l2,
        mock_hmac_validation,
        high_confidence_pep_payload
    ):
        """
        Given a high-confidence PEP case with block
        When EDD is completed and case closed
        Then the onboarding block is cleared
        """
        # Create case
        create_response = client.post(
            "/webhooks/indue",
            json=high_confidence_pep_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]
        customer_id = high_confidence_pep_payload["customerId"]

        # Claim case
        client.post(
            f"/cases/{case_id}/claim",
            headers={"Authorization": "Bearer l2-valid-token"}
        )

        # Complete EDD
        client.post(
            f"/cases/{case_id}/edd-checklist",
            json={
                "items": [
                    {"itemId": "SOURCE_OF_WEALTH", "completed": True, "notes": "Verified"},
                    {"itemId": "SOURCE_OF_FUNDS", "completed": True, "notes": "Verified"},
                    {"itemId": "PEP_RELATIONSHIP", "completed": True, "notes": "Verified"},
                    {"itemId": "BUSINESS_PURPOSE", "completed": True, "notes": "Verified"}
                ]
            },
            headers={"Authorization": "Bearer l2-valid-token"}
        )

        # Close case
        client.post(
            f"/cases/{case_id}/close",
            json={
                "reason": "EDD completed - customer approved",
                "documentation": "All EDD items verified successfully"
            },
            headers={"Authorization": "Bearer l2-valid-token"}
        )

        # Verify block is cleared
        block_response = client.get(
            f"/onboarding-blocks/{customer_id}",
            headers={"Authorization": "Bearer l2-valid-token"}
        )

        assert block_response.status_code == 200
        assert block_response.json()["isBlocked"] is False

    def test_incomplete_edd_prevents_closure(
        self,
        client: TestClient,
        mock_oidc_auth_l2,
        mock_hmac_validation,
        high_confidence_pep_payload
    ):
        """
        Given a high-confidence PEP case with incomplete EDD
        When trying to close the case
        Then closure is prevented
        """
        pass  # Implementation pending


class TestPEPThresholds:
    """Test PEP confidence threshold behavior."""

    def test_score_above_threshold_is_high_confidence(
        self,
        client: TestClient,
        mock_hmac_validation
    ):
        """
        Given a PEP match score above threshold (e.g., 85)
        When processing the alert
        Then it is classified as high-confidence (FR-030)
        """
        payload = {
            "screeningId": "test-screening-high",
            "customerId": "cust-pep-high",
            "screeningType": "PEP",
            "matchScore": 85,  # Above default 80 threshold
            "matchDetails": {
                "name": "High Confidence PEP",
                "matchType": "EXACT",
                "category": "NATIONAL_GOVERNMENT"
            },
            "timestamp": "2026-01-18T10:00:00Z"
        }

        response = client.post(
            "/webhooks/indue",
            json=payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )

        assert response.status_code == 201
        assert response.json()["caseType"] == "PEP_HIGH_CONFIDENCE"

    def test_score_at_threshold_is_low_confidence(
        self,
        client: TestClient,
        mock_hmac_validation
    ):
        """
        Given a PEP match score equal to threshold
        When processing the alert
        Then it is classified as low-confidence (EC-011)
        """
        payload = {
            "screeningId": "test-screening-equal",
            "customerId": "cust-pep-equal",
            "screeningType": "PEP",
            "matchScore": 80,  # Equal to default threshold
            "matchDetails": {
                "name": "Threshold PEP",
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
        # Score equal to threshold is treated as low-confidence
        assert response.json()["caseType"] in ["PEP_SCREENING", "PEP_LOW_CONFIDENCE"]


# Fixtures

@pytest.fixture
def high_confidence_pep_payload():
    """Create a high-confidence PEP webhook payload."""
    return {
        "screeningId": "test-screening-pep-001",
        "customerId": "cust-pep-001",
        "screeningType": "PEP",
        "matchScore": 92,  # High confidence
        "matchDetails": {
            "name": "Senator Smith",
            "matchType": "EXACT",
            "category": "NATIONAL_GOVERNMENT"
        },
        "timestamp": "2026-01-18T10:00:00Z",
        "customerOnboardingStatus": "NEW"
    }
