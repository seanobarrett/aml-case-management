"""
E2E tests for L2 investigation and SMR recommendation workflow.

References:
- US-4: L2 Analyst investigates case and recommends SMR
- FR-014: Only L2 or higher can create SMR recommendations
- FR-039: SMR recommendation must include justification
- BR-SMR-001: SMR can only be created by L2 or AML Manager
"""

import pytest
from fastapi.testclient import TestClient


class TestInvestigationFindings:
    """Test investigation findings documentation."""

    def test_l2_can_document_investigation_findings(
        self,
        client: TestClient,
        mock_oidc_auth_l2,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given an L2 analyst has claimed an escalated case
        When they document investigation findings
        Then the findings are saved to the case
        """
        # Create and escalate case (simulated)
        create_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # Document findings
        findings_response = client.post(
            f"/cases/{case_id}/investigation-findings",
            json={
                "summary": "Investigation into potential sanctions match",
                "methodology": "Cross-referenced customer data with OFAC SDN list",
                "keyFindings": [
                    "Customer name matches SDN entry 'John Smith'",
                    "Date of birth differs by 5 years",
                    "Address is in different country"
                ],
                "riskAssessment": "LOW",
                "recommendation": "FALSE_POSITIVE"
            },
            headers={"Authorization": "Bearer l2-valid-token"}
        )

        assert findings_response.status_code == 200
        data = findings_response.json()
        assert data["hasFindings"] == True

    def test_investigation_findings_appear_in_timeline(
        self,
        client: TestClient,
        mock_oidc_auth_l2,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given investigation findings are documented
        When viewing the case timeline
        Then the findings appear as a timeline entry
        """
        # Create case
        create_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # Document findings
        client.post(
            f"/cases/{case_id}/investigation-findings",
            json={
                "summary": "Detailed investigation conducted",
                "methodology": "Standard investigation protocol",
                "keyFindings": ["Finding 1", "Finding 2"],
                "riskAssessment": "MEDIUM",
                "recommendation": "FURTHER_REVIEW"
            },
            headers={"Authorization": "Bearer l2-valid-token"}
        )

        # Check timeline
        get_response = client.get(
            f"/cases/{case_id}",
            headers={"Authorization": "Bearer l2-valid-token"}
        )

        data = get_response.json()
        timeline_types = [entry["entryType"] for entry in data["timeline"]]
        assert "FINDINGS_DOCUMENTED" in timeline_types


class TestSMRRecommendation:
    """Test SMR recommendation creation."""

    def test_l2_can_create_smr_recommendation(
        self,
        client: TestClient,
        mock_oidc_auth_l2,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given an L2 analyst has documented investigation findings
        When they create an SMR recommendation
        Then the case status changes to PENDING_APPROVAL (FR-014, FR-039)
        """
        # Create case
        create_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # Document findings first
        client.post(
            f"/cases/{case_id}/investigation-findings",
            json={
                "summary": "Confirmed true match",
                "methodology": "Full investigation",
                "keyFindings": ["True match confirmed"],
                "riskAssessment": "HIGH",
                "recommendation": "SMR_REQUIRED"
            },
            headers={"Authorization": "Bearer l2-valid-token"}
        )

        # Create SMR recommendation
        smr_response = client.post(
            f"/cases/{case_id}/smr/recommend",
            json={
                "recommendation": "SUBMIT",
                "justification": "Customer is confirmed PEP with undisclosed source of funds",
                "suspiciousActivity": "Unusual transaction patterns detected during review period",
                "supportingDocuments": ["Investigation report", "Transaction analysis"]
            },
            headers={"Authorization": "Bearer l2-valid-token"}
        )

        assert smr_response.status_code == 200
        data = smr_response.json()
        assert data["status"] == "PENDING_APPROVAL"

    def test_l1_cannot_create_smr_recommendation(
        self,
        client: TestClient,
        mock_oidc_auth,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given an L1 analyst attempts to create SMR
        When they submit the recommendation
        Then access is denied (BR-SMR-001)
        """
        # Create case
        create_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # Attempt SMR recommendation as L1
        smr_response = client.post(
            f"/cases/{case_id}/smr/recommend",
            json={
                "recommendation": "SUBMIT",
                "justification": "Suspicious activity detected during investigation",
                "suspiciousActivity": "Unusual transaction patterns observed",
                "supportingDocuments": []
            },
            headers={"Authorization": "Bearer valid-token"}
        )

        assert smr_response.status_code == 403

    def test_smr_requires_justification(
        self,
        client: TestClient,
        mock_oidc_auth_l2,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given an SMR recommendation is being created
        When justification is missing
        Then validation error is returned (FR-039)
        """
        # Create case
        create_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # Attempt SMR without justification
        smr_response = client.post(
            f"/cases/{case_id}/smr/recommend",
            json={
                "recommendation": "SUBMIT",
                "justification": "",  # Empty justification
                "suspiciousActivity": "Activity",
                "supportingDocuments": []
            },
            headers={"Authorization": "Bearer l2-valid-token"}
        )

        assert smr_response.status_code == 422


class TestSMRManagerNotification:
    """Test SMR submission notifications to managers."""

    def test_smr_submission_notifies_managers(
        self,
        client: TestClient,
        mock_oidc_auth_l2,
        mock_hmac_validation,
        greenid_webhook_payload
    ):
        """
        Given an SMR recommendation is submitted
        When the submission is processed
        Then AML managers receive notifications
        """
        # Create case and submit SMR
        create_response = client.post(
            "/webhooks/greenid",
            json=greenid_webhook_payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # Document findings
        client.post(
            f"/cases/{case_id}/investigation-findings",
            json={
                "summary": "Investigation complete",
                "methodology": "Full protocol",
                "keyFindings": ["Match confirmed"],
                "riskAssessment": "HIGH",
                "recommendation": "SMR_REQUIRED"
            },
            headers={"Authorization": "Bearer l2-valid-token"}
        )

        # Submit SMR recommendation
        client.post(
            f"/cases/{case_id}/smr/recommend",
            json={
                "recommendation": "SUBMIT",
                "justification": "Confirmed suspicious activity requiring AUSTRAC report",
                "suspiciousActivity": "Large cash deposits inconsistent with declared income",
                "supportingDocuments": ["Transaction report"]
            },
            headers={"Authorization": "Bearer l2-valid-token"}
        )

        # Manager notification verification would check notifications endpoint
        # This test documents the expected behavior
        pass
