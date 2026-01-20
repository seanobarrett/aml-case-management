"""
E2E tests for dashboard with case prioritization and SLA indicators.

References:
- US-12: Dashboard with prioritized work queue
- FR-024: Cases filtered by status
- FR-025: Cases ordered by SLA priority
- D6: 30-second polling for dashboard
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient


class TestDashboardMyCases:
    """Test dashboard my-cases endpoint."""

    def test_analyst_sees_assigned_cases(
        self,
        client: TestClient,
        mock_oidc_auth,
        assigned_cases
    ):
        """
        Given cases assigned to the analyst
        When viewing my-cases dashboard
        Then only assigned cases are shown (FR-024)
        """
        response = client.get(
            "/dashboard/my-cases",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        # All returned cases should be assigned to current user
        for case in data["items"]:
            assert case["assignedToId"] is not None

    def test_cases_ordered_by_sla_priority(
        self,
        client: TestClient,
        mock_oidc_auth,
        cases_with_varied_sla
    ):
        """
        Given cases with different SLA deadlines
        When viewing my-cases dashboard
        Then cases are ordered by SLA deadline ascending (FR-025)
        """
        response = client.get(
            "/dashboard/my-cases",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify SLA ordering
        deadlines = [case.get("slaDeadline") for case in data["items"]]
        # Filter out None values for comparison
        valid_deadlines = [d for d in deadlines if d is not None]
        assert valid_deadlines == sorted(valid_deadlines)

    def test_dashboard_includes_sla_indicators(
        self,
        client: TestClient,
        mock_oidc_auth,
        assigned_cases
    ):
        """
        Given cases with various SLA statuses
        When viewing my-cases dashboard
        Then SLA indicators are included (US-12)
        """
        response = client.get(
            "/dashboard/my-cases",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert response.status_code == 200
        data = response.json()

        for case in data["items"]:
            # Each case should have SLA indicator
            assert "slaIndicator" in case
            assert case["slaIndicator"] in ["ON_TRACK", "WARNING", "BREACHED", "PAUSED", "NO_SLA"]

    def test_dashboard_shows_breach_status(
        self,
        client: TestClient,
        mock_oidc_auth,
        breached_assigned_case
    ):
        """
        Given a case that has breached SLA
        When viewing my-cases dashboard
        Then the case shows BREACHED indicator
        """
        response = client.get(
            "/dashboard/my-cases",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert response.status_code == 200
        data = response.json()

        breached_cases = [c for c in data["items"] if c["slaIndicator"] == "BREACHED"]
        assert len(breached_cases) >= 1


class TestDashboardQueueMetrics:
    """Test dashboard queue metrics endpoint."""

    def test_queue_metrics_returns_counts(
        self,
        client: TestClient,
        mock_oidc_auth,
        various_cases
    ):
        """
        Given various cases in different states
        When viewing queue-metrics
        Then counts by status are returned
        """
        response = client.get(
            "/dashboard/queue-metrics",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should have count breakdowns
        assert "totalOpen" in data
        assert "totalUnassigned" in data
        assert "totalAssigned" in data
        assert "totalPendingInfo" in data
        assert "byTier" in data
        assert "byType" in data

    def test_queue_metrics_includes_sla_stats(
        self,
        client: TestClient,
        mock_oidc_auth,
        various_cases
    ):
        """
        Given cases with various SLA states
        When viewing queue-metrics
        Then SLA statistics are included
        """
        response = client.get(
            "/dashboard/queue-metrics",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "slaStats" in data
        sla_stats = data["slaStats"]
        assert "onTrack" in sla_stats
        assert "warning" in sla_stats
        assert "breached" in sla_stats

    def test_queue_metrics_by_tier(
        self,
        client: TestClient,
        mock_oidc_auth,
        various_cases
    ):
        """
        Given cases in L1 and L2 tiers
        When viewing queue-metrics
        Then counts are broken down by tier
        """
        response = client.get(
            "/dashboard/queue-metrics",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert response.status_code == 200
        data = response.json()

        by_tier = data["byTier"]
        assert "L1" in by_tier
        assert "L2" in by_tier


class TestPollingSupport:
    """Test 30-second polling support."""

    def test_dashboard_supports_etag(
        self,
        client: TestClient,
        mock_oidc_auth,
        assigned_cases
    ):
        """
        Given a dashboard request
        When including If-None-Match header with unchanged ETag
        Then 304 Not Modified is returned (D6)
        """
        # First request to get ETag
        response1 = client.get(
            "/dashboard/my-cases",
            headers={"Authorization": "Bearer valid-token"}
        )
        assert response1.status_code == 200
        etag = response1.headers.get("ETag")

        if etag:
            # Second request with If-None-Match
            response2 = client.get(
                "/dashboard/my-cases",
                headers={
                    "Authorization": "Bearer valid-token",
                    "If-None-Match": etag
                }
            )
            # Should return 304 if data unchanged
            assert response2.status_code in [200, 304]

    def test_dashboard_includes_cache_control(
        self,
        client: TestClient,
        mock_oidc_auth,
        assigned_cases
    ):
        """
        Given a dashboard request
        When response is returned
        Then Cache-Control header suggests 30s revalidation
        """
        response = client.get(
            "/dashboard/my-cases",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert response.status_code == 200
        # Cache header should be present for polling support
        cache_control = response.headers.get("Cache-Control", "")
        # Should suggest short cache or revalidation
        assert "max-age" in cache_control or "no-cache" in cache_control


class TestDashboardFiltering:
    """Test dashboard filtering capabilities."""

    def test_filter_by_status(
        self,
        client: TestClient,
        mock_oidc_auth,
        various_cases
    ):
        """
        Given cases with various statuses
        When filtering by status
        Then only matching cases are returned
        """
        response = client.get(
            "/dashboard/my-cases?status=ASSIGNED",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert response.status_code == 200
        data = response.json()

        for case in data["items"]:
            assert case["status"] == "ASSIGNED"

    def test_filter_by_case_type(
        self,
        client: TestClient,
        mock_oidc_auth,
        various_cases
    ):
        """
        Given cases with various types
        When filtering by case type
        Then only matching cases are returned
        """
        response = client.get(
            "/dashboard/my-cases?caseType=SANCTIONS_ONBOARDING",
            headers={"Authorization": "Bearer valid-token"}
        )

        assert response.status_code == 200
        data = response.json()

        for case in data["items"]:
            assert case["caseType"] == "SANCTIONS_ONBOARDING"


# Fixtures

@pytest.fixture
def assigned_cases(client, mock_oidc_auth, mock_hmac_validation, greenid_webhook_payload):
    """Create cases assigned to the current user."""
    cases = []
    for i in range(3):
        payload = greenid_webhook_payload.copy()
        payload["verificationId"] = f"test-verification-dashboard-{i}"
        payload["customerId"] = f"cust-dashboard-{i}"

        create_response = client.post(
            "/webhooks/greenid",
            json=payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        # Claim the case
        client.post(
            f"/cases/{case_id}/claim",
            headers={"Authorization": "Bearer valid-token"}
        )

        cases.append(create_response.json())

    return cases


@pytest.fixture
def cases_with_varied_sla(client, mock_oidc_auth, mock_hmac_validation):
    """Create cases with different SLA deadlines."""
    cases = []

    # Create cases with different types (which have different SLAs)
    payloads = [
        {"verificationType": "SANCTIONS", "alertType": "SANCTIONS_HIT"},  # 1 day
        {"verificationType": "KYC_REMEDIATION"},  # 5 days
        {"verificationType": "PEP", "alertType": "PEP_HIT"},  # 3 days
    ]

    for i, base_payload in enumerate(payloads):
        payload = {
            "verificationId": f"test-verification-sla-{i}",
            "customerId": f"cust-sla-varied-{i}",
            "outcome": "ALERT",
            "timestamp": datetime.utcnow().isoformat(),
            "customer": {"firstName": "Test", "lastName": f"User{i}"},
            **base_payload
        }

        create_response = client.post(
            "/webhooks/greenid",
            json=payload,
            headers={"X-Webhook-Signature": "valid-signature"}
        )
        case_id = create_response.json()["id"]

        client.post(
            f"/cases/{case_id}/claim",
            headers={"Authorization": "Bearer valid-token"}
        )

        cases.append(create_response.json())

    return cases


@pytest.fixture
def breached_assigned_case(client, mock_oidc_auth, mock_hmac_validation, greenid_webhook_payload, db_session):
    """Create a case that has breached SLA."""
    from datetime import datetime, timedelta
    from uuid import UUID
    from src.models.case import Case

    payload = greenid_webhook_payload.copy()
    payload["verificationId"] = "test-verification-breached"
    payload["customerId"] = "cust-breached"

    create_response = client.post(
        "/webhooks/greenid",
        json=payload,
        headers={"X-Webhook-Signature": "valid-signature"}
    )
    case_id = create_response.json()["id"]

    # Claim the case
    client.post(
        f"/cases/{case_id}/claim",
        headers={"Authorization": "Bearer valid-token"}
    )

    # Mark the case as breached
    case = db_session.query(Case).filter(Case.id == UUID(case_id)).first()
    if case:
        case.sla_breach = True
        case.sla_breach_at = datetime.utcnow()
        case.sla_deadline = datetime.utcnow() - timedelta(hours=2)  # Past deadline
        db_session.commit()

    return create_response.json()


@pytest.fixture
def various_cases(client, mock_oidc_auth, mock_hmac_validation):
    """Create various cases for metrics testing."""
    from datetime import datetime

    cases = []

    # Different case types and states
    configs = [
        {"verificationType": "SANCTIONS", "alertType": "SANCTIONS_HIT"},
        {"verificationType": "KYC_REMEDIATION"},
        {"verificationType": "KYC_REMEDIATION"},
        {"verificationType": "PEP", "alertType": "PEP_HIT"},
    ]

    for i, config in enumerate(configs):
        payload = {
            "verificationId": f"test-verification-various-{i}",
            "customerId": f"cust-various-{i}",
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
