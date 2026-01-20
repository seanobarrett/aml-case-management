"""
E2E tests for new alert case linking.

References:
- EC-014: New alerts for customers with open cases are linked
- FR-046: Case linking for related cases
"""

import pytest
from fastapi.testclient import TestClient


class TestAlertCaseLinking:
    """Test new alerts are linked to existing open cases."""

    def test_new_alert_linked_to_existing_open_case(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given a customer has an open case
        When a new alert arrives for the same customer
        Then the new case is linked to the existing case (EC-014)
        """
        customer_id = greenid_webhook_payload["customerId"]

        # Create first case
        first_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        first_case_id = first_response.json()["id"]

        # Create second alert for same customer (different verificationId to avoid duplicate detection)
        second_payload = greenid_webhook_payload.copy()
        second_payload["verificationId"] = "verify-456"  # Different verification ID
        second_payload["verificationType"] = "PEP_SCREENING"

        second_response = client.post(
            "/webhooks/greenid",
            json=second_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        second_case_id = second_response.json()["id"]

        # Verify cases are linked
        links_response = client.get(
            f"/cases/{first_case_id}/linked-cases",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert links_response.status_code == 200
        linked_cases = links_response.json()["linkedCases"]
        linked_ids = [lc["caseId"] for lc in linked_cases]
        assert second_case_id in linked_ids

    def test_linked_cases_show_bidirectional_reference(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given two linked cases
        When viewing either case
        Then both show the link to each other
        """
        customer_id = greenid_webhook_payload["customerId"]

        # Create first case
        first_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        first_case_id = first_response.json()["id"]

        # Create second case for same customer (different verificationId to avoid duplicate detection)
        second_payload = greenid_webhook_payload.copy()
        second_payload["verificationId"] = "verify-457"

        second_response = client.post(
            "/webhooks/greenid",
            json=second_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        second_case_id = second_response.json()["id"]

        # Check from first case
        first_links = client.get(
            f"/cases/{first_case_id}/linked-cases",
            headers={"Authorization": "Bearer valid-token"}
        ).json()["linkedCases"]

        # Check from second case
        second_links = client.get(
            f"/cases/{second_case_id}/linked-cases",
            headers={"Authorization": "Bearer valid-token"}
        ).json()["linkedCases"]

        # Both should reference each other
        first_linked_ids = [lc["caseId"] for lc in first_links]
        second_linked_ids = [lc["caseId"] for lc in second_links]

        assert second_case_id in first_linked_ids
        assert first_case_id in second_linked_ids

    def test_closed_cases_not_linked_to_new_alerts(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given a customer has a closed case
        When a new alert arrives
        Then a new independent case is created (not linked)
        """
        # Create and close first case
        first_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        first_case_id = first_response.json()["id"]

        # Claim and close
        claim_response = client.post(
            f"/cases/{first_case_id}/claim",
            headers={"Authorization": "Bearer valid-token"}
        )
        assert claim_response.status_code == 200, f"Claim failed: {claim_response.json()}"

        close_response = client.post(
            f"/cases/{first_case_id}/close",
            json={
                "reason": "False positive",
                "documentation": "Identity verified through manual document review process"
            },
            headers={"Authorization": "Bearer valid-token"}
        )
        assert close_response.status_code == 200, f"Close failed: {close_response.json()}"
        assert close_response.json()["status"] == "CLOSED", f"Case not closed: {close_response.json()}"

        # Verify case is actually closed
        verify_response = client.get(
            f"/cases/{first_case_id}",
            headers={"Authorization": "Bearer valid-token"}
        )
        assert verify_response.json()["status"] == "CLOSED", f"Case status not CLOSED: {verify_response.json()}"

        # Create new alert for same customer (different verificationId to avoid duplicate detection)
        second_payload = greenid_webhook_payload.copy()
        second_payload["verificationId"] = "verify-458"

        second_response = client.post(
            "/webhooks/greenid",
            json=second_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        second_case_id = second_response.json()["id"]

        # Verify no link to closed case
        links_response = client.get(
            f"/cases/{second_case_id}/linked-cases",
            headers={"Authorization": "Bearer valid-token"}
        )

        linked_cases = links_response.json()["linkedCases"]
        linked_ids = [lc["caseId"] for lc in linked_cases]
        assert first_case_id not in linked_ids


class TestCaseLinkTypes:
    """Test different case link types."""

    def test_new_alert_link_type(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given a new alert creates a linked case
        When viewing the link
        Then the link type is NEW_ALERT
        """
        # Create two cases for same customer
        first_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        first_case_id = first_response.json()["id"]

        second_payload = greenid_webhook_payload.copy()
        second_payload["verificationId"] = "verify-459"

        second_response = client.post(
            "/webhooks/greenid",
            json=second_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )

        # Check link type
        links_response = client.get(
            f"/cases/{first_case_id}/linked-cases",
            headers={"Authorization": "Bearer valid-token"}
        )

        linked_cases = links_response.json()["linkedCases"]
        assert len(linked_cases) > 0
        assert linked_cases[0]["linkType"] == "NEW_ALERT"

    def test_analyst_notified_of_linked_cases(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given an analyst is assigned to an open case
        When a new alert creates a linked case
        Then the analyst is notified
        """
        # Create and claim first case
        first_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        first_case_id = first_response.json()["id"]

        client.post(
            f"/cases/{first_case_id}/claim",
            headers={"Authorization": "Bearer valid-token"}
        )

        # Create second case for same customer (different verificationId to avoid duplicate detection)
        second_payload = greenid_webhook_payload.copy()
        second_payload["verificationId"] = "verify-460"

        client.post(
            "/webhooks/greenid",
            json=second_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )

        # Check notifications
        notifications_response = client.get(
            "/notifications",
            headers={"Authorization": "Bearer valid-token"}
        )

        notifications = notifications_response.json()["items"]
        link_notifications = [
            n for n in notifications
            if "linked" in n["message"].lower() or "new alert" in n["message"].lower()
        ]
        assert len(link_notifications) > 0
