"""
E2E tests for L1 case triage workflow.

References:
- US-1: L1 Analyst triages new KYC remediation case
- US-13: L1 Analyst closes case with satisfactory explanation
- FR-009: Mandatory closure justification
- FR-011: False positive documentation
- FR-012: L2 review flagging for L1 closures
- FR-015: Closure with supporting documentation
"""

import pytest
from fastapi.testclient import TestClient


class TestL1CaseClaim:
    """Test L1 case claiming from queue."""

    def test_l1_can_claim_case_from_queue(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given a case exists in the unassigned queue
        When an L1 analyst claims the case
        Then the case is assigned to them and status changes to ASSIGNED
        """
        # Create case
        create_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # Claim case
        claim_response = client.post(
            f"/cases/{case_id}/claim",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert claim_response.status_code == 200
        data = claim_response.json()
        assert data["status"] == "ASSIGNED"

    def test_claimed_case_shows_assigned_analyst(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given a case is claimed
        When viewing the case
        Then the assigned analyst ID is visible
        """
        # Create and claim case
        create_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        client.post(
            f"/cases/{case_id}/claim",
            headers={"Authorization": "Bearer valid-token"}
        )

        # Get case details
        get_response = client.get(
            f"/cases/{case_id}",
            headers={"Authorization": "Bearer valid-token"}
        )

        data = get_response.json()
        assert data["assignedToId"] is not None


class TestL1CaseClosure:
    """Test L1 case closure with documentation."""

    def test_l1_can_close_case_with_documentation(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given an L1 analyst has claimed a case
        When they close the case with documentation
        Then the case status changes to CLOSED (FR-009, FR-015)
        """
        # Create and claim case
        create_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        client.post(
            f"/cases/{case_id}/claim",
            headers={"Authorization": "Bearer valid-token"}
        )

        # Close case
        close_response = client.post(
            f"/cases/{case_id}/close",
            json={
                "reason": "False positive - customer name mismatch due to typo",
                "documentation": "Verified customer identity manually. The GreenID flag was due to a typo in the middle name."
            },
            headers={"Authorization": "Bearer valid-token"}
        )

        assert close_response.status_code == 200
        data = close_response.json()
        assert data["status"] == "CLOSED"

    def test_closure_requires_minimum_documentation(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given a case exists
        When closing without sufficient documentation
        Then validation error is returned (FR-009)
        """
        # Create and claim case
        create_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        client.post(
            f"/cases/{case_id}/claim",
            headers={"Authorization": "Bearer valid-token"}
        )

        # Try to close with minimal documentation
        close_response = client.post(
            f"/cases/{case_id}/close",
            json={
                "reason": "Done",
                "documentation": "OK"
            },
            headers={"Authorization": "Bearer valid-token"}
        )

        # Should fail validation (min 10 chars for reason, 20 for documentation)
        assert close_response.status_code == 422

    def test_l1_closure_flags_for_l2_review(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given an L1 analyst closes a case
        When the case is closed
        Then the case is flagged for L2 quality review (FR-012)
        """
        # Create, claim, and close case
        create_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        client.post(
            f"/cases/{case_id}/claim",
            headers={"Authorization": "Bearer valid-token"}
        )

        client.post(
            f"/cases/{case_id}/close",
            json={
                "reason": "False positive - identity verification passed",
                "documentation": "Customer provided additional documentation confirming identity."
            },
            headers={"Authorization": "Bearer valid-token"}
        )

        # Check case has L2 review status
        get_response = client.get(
            f"/cases/{case_id}",
            headers={"Authorization": "Bearer valid-token"}
        )

        data = get_response.json()
        assert data["l2ReviewStatus"] == "PENDING_REVIEW"


class TestImplicitClaim:
    """Test implicit claiming behavior (D13)."""

    def test_closing_unassigned_case_implicitly_claims(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given a case is not assigned
        When an analyst closes the case
        Then the case is implicitly claimed first (D13)
        """
        # Create case (don't claim)
        create_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # Close without explicit claim
        close_response = client.post(
            f"/cases/{case_id}/close",
            json={
                "reason": "False positive - system error in GreenID",
                "documentation": "Confirmed with GreenID support that this was a system error."
            },
            headers={"Authorization": "Bearer valid-token"}
        )

        assert close_response.status_code == 200

        # Verify case has assignee
        get_response = client.get(
            f"/cases/{case_id}",
            headers={"Authorization": "Bearer valid-token"}
        )

        data = get_response.json()
        assert data["assignedToId"] is not None
        assert data["status"] == "CLOSED"
