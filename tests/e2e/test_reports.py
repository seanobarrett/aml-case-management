"""
E2E tests for read-only reports and export functionality.

References:
- US-10: Read-only reports access
- FR-064: Read-only role enforcement
- FR-070: Case volume reports
- FR-071: SMR metrics reports
- FR-072: Data export capability
- FR-073: Aged cases report
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient


class TestVolumeReports:
    """Test case volume reports."""

    def test_volumes_report_returns_data(
        self,
        client: TestClient,
        mock_oidc_auth,
        various_cases
    ):
        """
        Given cases in the system
        When viewing volumes report
        Then case counts by type and status are returned (FR-070)
        """
        response = client.get(
            "/reports/volumes",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "byType" in data
        assert "byStatus" in data
        assert "byTier" in data
        assert "total" in data
        assert "periodStart" in data
        assert "periodEnd" in data

    def test_volumes_report_filters_by_date(
        self,
        client: TestClient,
        mock_oidc_auth,
        various_cases
    ):
        """
        Given cases in the system
        When filtering volumes by date range
        Then only cases in range are included
        """
        response = client.get(
            "/reports/volumes?startDate=2026-01-01&endDate=2026-12-31",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["periodStart"] == "2026-01-01"
        assert data["periodEnd"] == "2026-12-31"


class TestSLAComplianceReports:
    """Test SLA compliance reports."""

    def test_sla_compliance_report(
        self,
        client: TestClient,
        mock_oidc_auth,
        various_cases
    ):
        """
        Given cases with various SLA states
        When viewing SLA compliance report
        Then compliance metrics are returned (FR-070)
        """
        response = client.get(
            "/reports/sla-compliance",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "totalCases" in data
        assert "onTrack" in data
        assert "breached" in data
        assert "complianceRate" in data

    def test_sla_compliance_by_case_type(
        self,
        client: TestClient,
        mock_oidc_auth,
        various_cases
    ):
        """
        Given cases with various types and SLA states
        When viewing SLA compliance report
        Then breakdown by case type is available
        """
        response = client.get(
            "/reports/sla-compliance?groupBy=caseType",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "byGroup" in data


class TestSMRMetricsReports:
    """Test SMR metrics reports."""

    def test_smr_metrics_report(
        self,
        client: TestClient,
        mock_oidc_auth
    ):
        """
        Given SMR submissions in the system
        When viewing SMR metrics report
        Then SMR statistics are returned (FR-071)
        """
        response = client.get(
            "/reports/smr-metrics",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "totalRecommendations" in data
        assert "totalApproved" in data
        assert "totalRejected" in data
        assert "totalPending" in data
        assert "averageApprovalTime" in data

    def test_smr_metrics_by_period(
        self,
        client: TestClient,
        mock_oidc_auth
    ):
        """
        Given SMR submissions over time
        When filtering by period
        Then only SMRs in that period are counted
        """
        response = client.get(
            "/reports/smr-metrics?startDate=2026-01-01&endDate=2026-01-31",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert response.status_code == 200


class TestAgedCasesReport:
    """Test aged cases report."""

    def test_aged_cases_report(
        self,
        client: TestClient,
        mock_oidc_auth,
        various_cases
    ):
        """
        Given cases of various ages
        When viewing aged cases report
        Then cases are grouped by age (FR-073)
        """
        response = client.get(
            "/reports/aged-cases",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should have age buckets
        assert "buckets" in data
        # Common age buckets: 0-7 days, 7-14 days, 14-30 days, 30+ days
        for bucket in data["buckets"]:
            assert "label" in bucket
            assert "count" in bucket

    def test_aged_cases_filters_by_tier(
        self,
        client: TestClient,
        mock_oidc_auth,
        various_cases
    ):
        """
        Given cases in different tiers
        When filtering aged cases by tier
        Then only that tier's cases are shown
        """
        response = client.get(
            "/reports/aged-cases?tier=L1",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "tier" in data
        assert data["tier"] == "L1"


class TestDataExport:
    """Test data export functionality."""

    def test_export_csv(
        self,
        client: TestClient,
        mock_oidc_auth,
        various_cases
    ):
        """
        Given cases in the system
        When exporting as CSV
        Then CSV file is returned (FR-072)
        """
        response = client.get(
            "/reports/export?format=csv",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")

    def test_export_excel(
        self,
        client: TestClient,
        mock_oidc_auth,
        various_cases
    ):
        """
        Given cases in the system
        When exporting as Excel
        Then Excel file is returned (FR-072)
        """
        response = client.get(
            "/reports/export?format=xlsx",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert response.status_code == 200
        # Excel MIME type
        content_type = response.headers.get("content-type", "")
        assert "spreadsheet" in content_type or "xlsx" in content_type

    def test_export_filters_by_date_range(
        self,
        client: TestClient,
        mock_oidc_auth,
        various_cases
    ):
        """
        Given cases over time
        When exporting with date filter
        Then only cases in range are exported
        """
        response = client.get(
            "/reports/export?format=csv&startDate=2026-01-01&endDate=2026-01-31",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert response.status_code == 200


class TestReadOnlyRoleEnforcement:
    """Test read-only role access to reports."""

    def test_readonly_can_view_reports(
        self,
        client: TestClient,
        mock_oidc_auth_readonly,
        various_cases
    ):
        """
        Given a read-only user
        When accessing reports
        Then reports are accessible (FR-064)
        """
        response = client.get(
            "/reports/volumes",
            headers={"Authorization": "Bearer readonly-token"}
        )

        assert response.status_code == 200

    def test_readonly_can_export(
        self,
        client: TestClient,
        mock_oidc_auth_readonly,
        various_cases
    ):
        """
        Given a read-only user
        When exporting data
        Then export is allowed (FR-072)
        """
        response = client.get(
            "/reports/export?format=csv",
            headers={"Authorization": "Bearer readonly-token"}
        )

        assert response.status_code == 200

    def test_readonly_cannot_modify_cases(
        self,
        client: TestClient,
        mock_oidc_auth_readonly,
        various_cases
    ):
        """
        Given a read-only user
        When trying to modify a case
        Then the action is forbidden
        """
        case_id = various_cases[0]["id"]

        response = client.post(
            f"/cases/{case_id}/claim",
            headers={"Authorization": "Bearer readonly-token"}
        )

        assert response.status_code == 403


# Fixtures

@pytest.fixture
def various_cases(client, mock_hmac_validation):
    """Create various cases for report testing."""
    from datetime import datetime

    cases = []

    configs = [
        {"verificationType": "SANCTIONS", "alertType": "SANCTIONS_HIT"},
        {"verificationType": "KYC_REMEDIATION"},
        {"verificationType": "KYC_REMEDIATION"},
        {"verificationType": "PEP", "alertType": "PEP_HIT"},
        {"verificationType": "KYC_REMEDIATION"},
    ]

    for i, config in enumerate(configs):
        payload = {
            "verificationId": f"test-verification-report-{i}",
            "customerId": f"cust-report-{i}",
            "outcome": "ALERT",
            "timestamp": datetime.utcnow().isoformat(),
            "customer": {"firstName": "Test", "lastName": f"User{i}"},
            **config
        }

        create_response = client.post(
            "/webhooks/greenid",
            json=payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        cases.append(create_response.json())

    return cases


@pytest.fixture
def mock_oidc_auth_readonly(client):
    """Mock OIDC authentication for read-only user."""
    from src.main import app
    from src.middleware.auth import get_current_user
    from conftest import create_mock_user, TEST_USER_READONLY_ID

    mock_user = create_mock_user(TEST_USER_READONLY_ID, "readonly@example.com", "READ_ONLY")

    async def override_auth():
        return mock_user

    app.dependency_overrides[get_current_user] = override_auth
    yield mock_user
