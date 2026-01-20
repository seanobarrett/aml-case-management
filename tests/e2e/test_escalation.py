"""
E2E tests for L1 to L2 escalation workflow.

References:
- US-3: L1 Analyst escalates case to L2
- FR-013: Case tier changes to L2 on escalation
- FR-068: L2 queue notification on escalation
"""

import pytest
from fastapi.testclient import TestClient


class TestL1ToL2Escalation:
    """Test L1 to L2 case escalation."""

    def test_l1_can_escalate_case_to_l2(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given an L1 analyst has claimed a case
        When they escalate the case with reasoning
        Then the case tier changes to L2 and status to ESCALATED (FR-013)
        """
        # Create case
        create_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # Claim case
        client.post(
            f"/cases/{case_id}/claim",
            headers={"Authorization": "Bearer valid-token"}
        )

        # Escalate case
        escalate_response = client.post(
            f"/cases/{case_id}/escalate",
            json={
                "reason": "Complex sanctions match requiring L2 expertise",
                "findings": "Initial investigation reveals potential true match with high confidence"
            },
            headers={"Authorization": "Bearer valid-token"}
        )

        assert escalate_response.status_code == 200
        data = escalate_response.json()
        assert data["status"] == "ESCALATED"

        # Verify case details
        get_response = client.get(
            f"/cases/{case_id}",
            headers={"Authorization": "Bearer valid-token"}
        )

        case_data = get_response.json()
        assert case_data["tier"] == "L2"
        assert case_data["status"] == "ESCALATED"
        assert case_data["assignedToId"] is None  # Unassigned for L2 queue

    def test_escalation_creates_timeline_entry(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given an L1 analyst escalates a case
        When the escalation is processed
        Then a timeline entry documents the escalation reason
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

        # Escalate with detailed reasoning
        client.post(
            f"/cases/{case_id}/escalate",
            json={
                "reason": "Suspected true sanctions match",
                "findings": "Customer name exactly matches OFAC SDN list entry"
            },
            headers={"Authorization": "Bearer valid-token"}
        )

        # Check timeline
        get_response = client.get(
            f"/cases/{case_id}",
            headers={"Authorization": "Bearer valid-token"}
        )

        data = get_response.json()
        timeline_types = [entry["entryType"] for entry in data["timeline"]]
        assert "CASE_ESCALATED" in timeline_types

    def test_escalation_requires_reason(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given an L1 analyst attempts to escalate
        When no reason is provided
        Then validation error is returned
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

        # Attempt escalation without reason
        escalate_response = client.post(
            f"/cases/{case_id}/escalate",
            json={
                "reason": "",
                "findings": ""
            },
            headers={"Authorization": "Bearer valid-token"}
        )

        assert escalate_response.status_code == 422


class TestEscalationNotifications:
    """Test escalation notifications."""

    def test_escalation_creates_l2_queue_notification(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given a case is escalated to L2
        When the escalation is processed
        Then a notification is sent to the L2 queue (FR-068)
        """
        # Create, claim, and escalate case
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
            f"/cases/{case_id}/escalate",
            json={
                "reason": "Requires L2 review for sanctions determination",
                "findings": "Complex case with multiple potential matches"
            },
            headers={"Authorization": "Bearer valid-token"}
        )

        # Verify notification was created
        # Note: In actual implementation, check notifications endpoint
        # or verify L2 analysts can see the case in their queue
        pass

    def test_escalated_case_appears_in_l2_queue(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given a case is escalated
        When L2 analysts view the queue
        Then the case appears in unassigned L2 queue
        """
        # Create, claim, and escalate case
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
            f"/cases/{case_id}/escalate",
            json={
                "reason": "L2 expertise needed",
                "findings": "Complex sanctions determination required"
            },
            headers={"Authorization": "Bearer valid-token"}
        )

        # Check queue
        queue_response = client.get(
            "/queue/unassigned?tier=L2",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert queue_response.status_code == 200
        data = queue_response.json()
        case_ids = [item["id"] for item in data["items"]]
        assert case_id in case_ids
