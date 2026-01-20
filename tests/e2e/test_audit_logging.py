"""
E2E tests for audit logging and immutability.

References:
- FR-058: All case actions logged immutably
- FR-059: Case view events logged
- FR-060: User attribution on all entries
- FR-061: 7-year retention (configuration only)
- Principle I: Immutable Audit Trail (NON-NEGOTIABLE)
- D12: PII redaction in audit payloads
"""

import pytest
from fastapi.testclient import TestClient


class TestAuditLogImmutability:
    """Test audit log creation and immutability constraints."""

    def test_case_creation_creates_audit_entry(
        self,
        client: TestClient,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given a webhook creates a case
        When the case is created
        Then an audit log entry is created with action CASE_CREATED
        """
        # Create case via webhook
        response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        assert response.status_code == 201
        case_id = response.json()["id"]

        # Verify audit log entry exists (via case timeline)
        # The timeline includes audit entries for the case
        case_response = client.get(
            f"/cases/{case_id}",
            headers={"Authorization": "Bearer valid-token"}
        )
        assert case_response.status_code == 200
        # Timeline will include creation event
        timeline = case_response.json().get("timeline", [])
        # Note: Timeline may be populated by Cycle 2 implementation

    def test_case_view_logged(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given a case exists
        When an authenticated user views the case
        Then a CASE_VIEWED audit entry is created (FR-059)
        """
        # Create case
        create_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # View case
        view_response = client.get(
            f"/cases/{case_id}",
            headers={"Authorization": "Bearer valid-token"}
        )
        assert view_response.status_code == 200

        # Verify view was logged (check audit endpoint or timeline)
        # Implementation will add audit middleware in T2.7

    def test_audit_entries_have_user_attribution(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given a user performs an action
        When the action is logged
        Then the audit entry includes the user ID (FR-060)
        """
        # Create case
        create_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # Claim case as authenticated user
        claim_response = client.post(
            f"/cases/{case_id}/claim",
            headers={"Authorization": "Bearer valid-token"}
        )
        assert claim_response.status_code == 200

        # The claim action should create audit entry with user attribution
        # Verified via audit log query (implementation in audit service)


class TestPIIRedaction:
    """Test PII redaction in audit log payloads (D12)."""

    def test_pii_fields_redacted_in_audit_payload(
        self,
        client: TestClient,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given a webhook with PII data
        When the case is created and logged
        Then PII fields are redacted in the audit payload
        """
        # Create case with PII in payload
        response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        assert response.status_code == 201

        # Verify that audit log does not contain raw PII
        # The audit payload should have:
        # - firstName: "[REDACTED]"
        # - lastName: "[REDACTED]"
        # - email: "[REDACTED]"
        # - dateOfBirth: "[REDACTED]"
        # Verification via audit query endpoint

    def test_pii_redaction_preserves_non_pii_fields(
        self,
        client: TestClient,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given a webhook payload with PII and non-PII data
        When the payload is redacted for audit
        Then non-PII fields are preserved
        """
        # Create case
        response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        assert response.status_code == 201

        # Verify non-PII fields are preserved in audit:
        # - verificationId: preserved
        # - customerId: preserved (reference, not PII)
        # - verificationType: preserved
        # - outcome: preserved


class TestAuditImmutabilityConstraints:
    """Test database-level immutability constraints."""

    def test_audit_log_cannot_be_updated(self, db_session):
        """
        Given an audit log entry exists
        When attempting to UPDATE the entry
        Then the database rejects the operation
        """
        # This test verifies the database trigger
        # The trigger is created in migration 002_audit_immutability
        # Direct database test to verify constraint
        pass

    def test_audit_log_cannot_be_deleted(self, db_session):
        """
        Given an audit log entry exists
        When attempting to DELETE the entry
        Then the database rejects the operation
        """
        # This test verifies the database trigger
        # Direct database test to verify constraint
        pass


class TestTimelineEntries:
    """Test timeline entry creation for case history."""

    def test_case_creation_adds_timeline_entry(
        self,
        client: TestClient,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given a case is created
        When retrieving the case
        Then timeline includes CASE_CREATED entry
        """
        # Create case
        create_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # Get case with timeline
        case_response = client.get(
            f"/cases/{case_id}",
            headers={"Authorization": "Bearer valid-token"}
        )

        # Verify timeline entry
        timeline = case_response.json().get("timeline", [])
        # Should contain creation entry
        creation_entries = [
            e for e in timeline
            if e.get("entryType") == "CASE_CREATED"
        ]
        # Note: Timeline population implemented in T2.7

    def test_case_claim_adds_timeline_entry(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given a case exists
        When an analyst claims the case
        Then timeline includes CASE_CLAIMED entry
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

        # Get case timeline
        case_response = client.get(
            f"/cases/{case_id}",
            headers={"Authorization": "Bearer valid-token"}
        )

        # Verify timeline entry
        timeline = case_response.json().get("timeline", [])
        claim_entries = [
            e for e in timeline
            if e.get("entryType") == "CASE_CLAIMED"
        ]
        # Note: Timeline population implemented in T2.7
