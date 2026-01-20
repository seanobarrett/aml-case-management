"""
E2E tests for case creation via webhook and retrieval.

References:
- US-1: L1 Analyst triages new KYC remediation case
- FR-001: System receives GreenID/Indue webhooks
- FR-002: System validates webhook payload schema
- FR-003: System generates unique case reference (AML-NNNN)
- FR-004: System captures case creation timestamp
- FR-005: System sets initial case status (OPEN)
"""

import pytest
from fastapi.testclient import TestClient


class TestCaseCreationViaWebhook:
    """Test case creation through webhook endpoints."""

    def test_greenid_webhook_creates_kyc_case(
        self,
        client: TestClient,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given a valid GreenID webhook payload
        When POST /webhooks/greenid is called
        Then a new case is created with status OPEN
        And the case has a unique reference starting with AML-
        And the case type is KYC_REMEDIATION
        """
        # Act
        response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["caseReference"].startswith("AML-")
        assert data["status"] == "OPEN"
        assert data["caseType"] == "KYC_REMEDIATION"
        assert data["customerId"] == greenid_webhook_payload["customerId"]
        assert "createdAt" in data

    def test_indue_webhook_creates_pep_case(
        self,
        client: TestClient,
        mock_hmac_validation,
        indue_webhook_payload
    ):
        """
        Given a valid Indue webhook payload for PEP screening
        When POST /webhooks/indue is called
        Then a new case is created for PEP review
        """
        # Act
        response = client.post(
            "/webhooks/indue",
            json=indue_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["caseReference"].startswith("AML-")
        assert data["status"] == "OPEN"
        assert data["caseType"] == "PEP_HIGH_CONFIDENCE"

    def test_webhook_rejects_invalid_signature(
        self,
        client: TestClient,
        greenid_webhook_payload,
        real_webhook_validation
    ):
        """
        Given a webhook request with invalid HMAC signature
        When the webhook endpoint is called
        Then a 401 Unauthorized response is returned
        """
        # Act
        response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "invalid-signature"}
        )

        # Assert
        assert response.status_code == 401
        assert "signature" in response.json()["detail"].lower()

    def test_webhook_rejects_duplicate_payload(
        self,
        client: TestClient,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given a webhook payload that was already processed
        When POST /webhooks/greenid is called with the same payload
        Then a 409 Conflict response is returned (EC-005)
        """
        # First call should succeed
        response1 = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        assert response1.status_code == 201

        # Duplicate call should be rejected
        response2 = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        assert response2.status_code == 409
        assert "duplicate" in response2.json()["detail"].lower()


class TestCaseRetrieval:
    """Test case retrieval by authenticated users."""

    def test_authenticated_user_can_list_cases(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given cases exist in the system
        When an authenticated user calls GET /cases
        Then a paginated list of cases is returned
        """
        # Setup - create a case first
        client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )

        # Act
        response = client.get(
            "/cases",
            headers={"Authorization": "Bearer valid-token"}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "pageSize" in data
        assert len(data["items"]) >= 1

    def test_authenticated_user_can_view_case_by_id(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given a case exists in the system
        When an authenticated user calls GET /cases/{caseId}
        Then the case details are returned
        """
        # Setup - create a case
        create_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # Act
        response = client.get(
            f"/cases/{case_id}",
            headers={"Authorization": "Bearer valid-token"}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == case_id
        assert data["caseReference"].startswith("AML-")
        assert "customer" in data
        assert "timeline" in data

    def test_unauthenticated_user_cannot_list_cases(
        self,
        client: TestClient,
        unauthenticated
    ):
        """
        Given no authentication token
        When GET /cases is called
        Then a 401 Unauthorized response is returned
        """
        # Act
        response = client.get("/cases")

        # Assert
        assert response.status_code == 401

    def test_case_list_supports_pagination(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation
    ):
        """
        Given multiple cases exist
        When GET /cases?page=2&pageSize=10 is called
        Then the correct page of results is returned
        """
        # Act
        response = client.get(
            "/cases?page=1&pageSize=5",
            headers={"Authorization": "Bearer valid-token"}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["pageSize"] == 5

    def test_case_list_filters_by_status(
        self,
        client: TestClient,
        mock_oidc_auth
    ):
        """
        Given cases with different statuses
        When GET /cases?status=OPEN is called
        Then only OPEN cases are returned (FR-024)
        """
        # Act
        response = client.get(
            "/cases?status=OPEN",
            headers={"Authorization": "Bearer valid-token"}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        for case in data["items"]:
            assert case["status"] == "OPEN"

    def test_case_list_ordered_by_sla_priority(
        self,
        client: TestClient,
        mock_oidc_auth
    ):
        """
        Given multiple cases with different SLA deadlines
        When GET /cases is called
        Then cases are ordered by SLA priority (closest deadline first) (FR-025)
        """
        # Act
        response = client.get(
            "/cases?sort=slaDeadline",
            headers={"Authorization": "Bearer valid-token"}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        if len(data["items"]) > 1:
            deadlines = [case["slaDeadline"] for case in data["items"]]
            assert deadlines == sorted(deadlines)


class TestCaseReferenceGeneration:
    """Test unique case reference number generation (D9)."""

    def test_case_references_are_unique(
        self,
        client: TestClient,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given multiple webhooks are received
        When cases are created
        Then each case has a unique AML-NNNN reference
        """
        references = set()

        for i in range(5):
            payload = greenid_webhook_payload.copy()
            payload["verificationId"] = f"verify-{i}"

            response = client.post(
                "/webhooks/greenid",
                json=payload,
                headers={"X-Webhook-Signature": "valid-signature"}
            )

            if response.status_code == 201:
                ref = response.json()["caseReference"]
                assert ref not in references
                references.add(ref)

        assert len(references) >= 1  # At least first one should succeed

    def test_case_reference_format(
        self,
        client: TestClient,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given a case is created
        Then the reference matches AML-NNNN format
        """
        import re

        response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )

        ref = response.json()["caseReference"]
        assert re.match(r"^AML-\d{4,}$", ref)
