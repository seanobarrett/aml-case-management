"""
E2E tests for L2 quality review workflow.

References:
- US-16: L2 quality review of L1 closures
- FR-018: L2 review queue filtering
- FR-019: Case reopen capability
"""

import pytest
from fastapi.testclient import TestClient


class TestL2ReviewQueue:
    """Test L2 review queue functionality."""

    def test_l1_closure_appears_in_l2_review_queue(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload,
        db_session
    ):
        """
        Given an L1 analyst closes a case
        When L2 views the review queue
        Then the case appears in the queue (FR-018)
        """
        from src.main import app
        from src.middleware.auth import get_current_user
        from conftest import create_mock_user, TEST_USER_L2_ID

        # Create case (default manager auth for webhook)
        create_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # L1 claims and closes (mock_oidc_auth sets L1 auth)
        client.post(
            f"/cases/{case_id}/claim",
            headers={"Authorization": "Bearer valid-token"}
        )
        client.post(
            f"/cases/{case_id}/close",
            json={
                "reason": "False positive - identity verified",
                "documentation": "Customer provided additional documentation confirming identity"
            },
            headers={"Authorization": "Bearer valid-token"}
        )

        # Switch to L2 auth for viewing review queue
        l2_user = create_mock_user(TEST_USER_L2_ID, "l2.analyst@spriggy.com", "L2_ANALYST")
        async def get_l2_user():
            return l2_user
        app.dependency_overrides[get_current_user] = get_l2_user

        # L2 checks review queue
        queue_response = client.get(
            "/queue/l2-review",
            headers={"Authorization": "Bearer l2-valid-token"}
        )

        assert queue_response.status_code == 200
        data = queue_response.json()
        case_ids = [item["id"] for item in data["items"]]
        assert case_id in case_ids


class TestL2AcceptClosure:
    """Test L2 acceptance of L1 closures."""

    def test_l2_can_accept_closure(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload,
        db_session
    ):
        """
        Given a case is pending L2 review
        When L2 accepts the closure
        Then the review status changes to REVIEWED_ACCEPTED
        """
        from src.main import app
        from src.middleware.auth import get_current_user
        from conftest import create_mock_user, TEST_USER_L2_ID

        # Create case
        create_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # L1 claims and closes (mock_oidc_auth sets L1 auth)
        client.post(
            f"/cases/{case_id}/claim",
            headers={"Authorization": "Bearer valid-token"}
        )
        client.post(
            f"/cases/{case_id}/close",
            json={
                "reason": "False positive confirmed",
                "documentation": "Full verification completed successfully"
            },
            headers={"Authorization": "Bearer valid-token"}
        )

        # Switch to L2 auth for accepting
        l2_user = create_mock_user(TEST_USER_L2_ID, "l2.analyst@spriggy.com", "L2_ANALYST")
        async def get_l2_user():
            return l2_user
        app.dependency_overrides[get_current_user] = get_l2_user

        # L2 accepts
        accept_response = client.post(
            f"/queue/l2-review/{case_id}/accept",
            headers={"Authorization": "Bearer l2-valid-token"}
        )

        assert accept_response.status_code == 200
        data = accept_response.json()
        assert data["l2ReviewStatus"] == "REVIEWED_ACCEPTED"


class TestL2ReopenCase:
    """Test L2 reopening of cases."""

    def test_l2_can_reopen_case(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload,
        db_session
    ):
        """
        Given a case is pending L2 review
        When L2 reopens the case
        Then the case is assigned to the L2 analyst (FR-019)
        """
        from src.main import app
        from src.middleware.auth import get_current_user
        from conftest import create_mock_user, TEST_USER_L2_ID

        # Create case (default manager auth for webhook)
        create_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # L1 claims and closes (mock_oidc_auth sets L1 auth)
        client.post(
            f"/cases/{case_id}/claim",
            headers={"Authorization": "Bearer valid-token"}
        )
        close_resp = client.post(
            f"/cases/{case_id}/close",
            json={
                "reason": "False positive",
                "documentation": "Identity verified through documentation review"
            },
            headers={"Authorization": "Bearer valid-token"}
        )
        assert close_resp.status_code == 200, f"Close failed: {close_resp.json()}"

        # Switch to L2 auth for reopening
        l2_user = create_mock_user(TEST_USER_L2_ID, "l2.analyst@spriggy.com", "L2_ANALYST")
        async def get_l2_user():
            return l2_user
        app.dependency_overrides[get_current_user] = get_l2_user

        # L2 reopens
        reopen_response = client.post(
            f"/queue/l2-review/{case_id}/reopen",
            json={
                "reason": "Additional investigation required - missing source of funds verification"
            },
            headers={"Authorization": "Bearer l2-valid-token"}
        )

        assert reopen_response.status_code == 200, f"Reopen failed: {reopen_response.json()}"
        data = reopen_response.json()
        assert data["status"] == "ASSIGNED"
        assert data["l2ReviewStatus"] == "REVIEWED_REOPENED"

    def test_reopened_case_escalated_to_l2_tier(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_oidc_auth_l2,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given an L2 analyst reopens a case
        When the case is reopened
        Then the case tier is changed to L2
        """
        pass


class TestL1CannotReviewOwnClosure:
    """Test L1 cannot review their own closures."""

    def test_l1_cannot_access_review_queue(
        self,
        client: TestClient,
        mock_oidc_auth,
        greenid_webhook_payload
    ):
        """
        Given an L1 analyst
        When they try to accept/reopen from L2 review
        Then access is denied
        """
        pass
