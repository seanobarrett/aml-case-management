"""
E2E tests for supplementary SMR creation and workflow.

References:
- US-18: Supplementary SMR filing
- FR-044: Create supplementary case from original
- FR-045: Supplementary follows full SMR workflow
- FR-046: Bidirectional linking between cases
- FR-047: Multiple supplementary filings allowed
"""

import pytest
from datetime import datetime
from fastapi.testclient import TestClient


class TestSupplementarySmrCreation:
    """Test supplementary SMR case creation."""

    def test_create_supplementary_from_original(
        self,
        client: TestClient,
        mock_oidc_auth_l2,
        completed_smr_case
    ):
        """
        Given a completed case with filed SMR
        When creating a supplementary case
        Then a new case is created linked to the original (FR-044)
        """
        original_case_id = completed_smr_case

        response = client.post(
            f"/cases/{original_case_id}/create-supplementary",
            json={
                "reason": "New information discovered regarding transaction patterns",
                "newEvidence": "Additional transaction analysis shows broader pattern"
            },
            headers={"Authorization": "Bearer l2-token"}
        )

        assert response.status_code == 201, f"Create supplementary failed: {response.json()}"
        data = response.json()

        # Supplementary case created
        assert data["caseType"] == "SMR_SUPPLEMENTARY"
        assert data["linkedTo"]["originalCaseId"] == original_case_id
        assert data["status"] == "OPEN"

    def test_supplementary_inherits_customer_info(
        self,
        client: TestClient,
        mock_oidc_auth_l2,
        completed_smr_case
    ):
        """
        Given a completed case with customer info
        When creating a supplementary case
        Then customer information is inherited
        """
        original_case_id = completed_smr_case

        # Get original case customer
        original_response = client.get(
            f"/cases/{original_case_id}",
            headers={"Authorization": "Bearer l2-token"}
        )
        original_customer = original_response.json()["customer"]

        # Create supplementary
        response = client.post(
            f"/cases/{original_case_id}/create-supplementary",
            json={"reason": "Additional information"},
            headers={"Authorization": "Bearer l2-token"}
        )

        supplementary_data = response.json()

        # Customer is the same
        assert supplementary_data["customer"]["id"] == original_customer["id"]


class TestBidirectionalNavigation:
    """Test bidirectional navigation between linked cases."""

    def test_original_shows_supplementary_links(
        self,
        client: TestClient,
        mock_oidc_auth_l2,
        case_with_supplementary
    ):
        """
        Given an original case with supplementary
        When viewing the original case
        Then supplementary cases are listed (FR-046)
        """
        original_case_id, supplementary_case_id = case_with_supplementary

        response = client.get(
            f"/cases/{original_case_id}",
            headers={"Authorization": "Bearer l2-token"}
        )

        data = response.json()
        linked_cases = data.get("linkedCases", [])

        # Find supplementary in linked cases
        supplementary_links = [
            lc for lc in linked_cases
            if lc.get("linkType") == "SUPPLEMENTARY"
        ]
        assert len(supplementary_links) >= 1
        assert any(lc["caseId"] == supplementary_case_id for lc in supplementary_links)

    def test_supplementary_shows_original_link(
        self,
        client: TestClient,
        mock_oidc_auth_l2,
        case_with_supplementary
    ):
        """
        Given a supplementary case
        When viewing the supplementary case
        Then original case is linked (FR-046)
        """
        original_case_id, supplementary_case_id = case_with_supplementary

        response = client.get(
            f"/cases/{supplementary_case_id}",
            headers={"Authorization": "Bearer l2-token"}
        )

        data = response.json()

        # Should link back to original
        assert data.get("linkedTo", {}).get("originalCaseId") == original_case_id


class TestMultipleSupplementaryFilings:
    """Test multiple supplementary filings per original."""

    def test_can_create_multiple_supplementary_cases(
        self,
        client: TestClient,
        mock_oidc_auth_l2,
        completed_smr_case
    ):
        """
        Given a completed case with filed SMR
        When creating multiple supplementary cases
        Then all are created and linked correctly (FR-047)
        """
        original_case_id = completed_smr_case

        # Create first supplementary
        response1 = client.post(
            f"/cases/{original_case_id}/create-supplementary",
            json={"reason": "First supplementary - initial findings"},
            headers={"Authorization": "Bearer l2-token"}
        )
        assert response1.status_code == 201
        supp1_id = response1.json()["id"]

        # Create second supplementary
        response2 = client.post(
            f"/cases/{original_case_id}/create-supplementary",
            json={"reason": "Second supplementary - additional transactions"},
            headers={"Authorization": "Bearer l2-token"}
        )
        assert response2.status_code == 201
        supp2_id = response2.json()["id"]

        # Create third supplementary
        response3 = client.post(
            f"/cases/{original_case_id}/create-supplementary",
            json={"reason": "Third supplementary - new suspicious activity"},
            headers={"Authorization": "Bearer l2-token"}
        )
        assert response3.status_code == 201
        supp3_id = response3.json()["id"]

        # All three should be different
        assert len({supp1_id, supp2_id, supp3_id}) == 3

        # Original should show all three
        original_response = client.get(
            f"/cases/{original_case_id}",
            headers={"Authorization": "Bearer l2-token"}
        )
        linked = original_response.json().get("linkedCases", [])
        supplementary_ids = [lc["caseId"] for lc in linked if lc.get("linkType") == "SUPPLEMENTARY"]

        assert supp1_id in supplementary_ids
        assert supp2_id in supplementary_ids
        assert supp3_id in supplementary_ids


class TestSupplementarySmrWorkflow:
    """Test supplementary case follows full SMR workflow."""

    def test_supplementary_requires_smr_recommendation(
        self,
        client: TestClient,
        mock_oidc_auth_l2,
        case_with_supplementary
    ):
        """
        Given a supplementary case
        When trying to close it
        Then SMR recommendation is required (FR-045)
        """
        _, supplementary_case_id = case_with_supplementary

        # Claim the case first
        client.post(
            f"/cases/{supplementary_case_id}/claim",
            headers={"Authorization": "Bearer l2-token"}
        )

        # Try to close without SMR
        response = client.post(
            f"/cases/{supplementary_case_id}/close",
            json={
                "reason": "Investigation complete",
                "documentation": "All investigation checks have been done"
            },
            headers={"Authorization": "Bearer l2-token"}
        )

        # Should fail - supplementary requires SMR workflow
        assert response.status_code == 400
        assert "SMR" in response.json().get("detail", "")

    def test_supplementary_smr_approval_workflow(
        self,
        client: TestClient,
        case_with_supplementary
    ):
        """
        Given a supplementary case with SMR recommendation
        When manager approves
        Then case can be closed with filed SMR (FR-045)
        """
        from src.main import app
        from src.middleware.auth import get_current_user
        from conftest import create_mock_user, TEST_USER_L2_ID, TEST_USER_MANAGER_ID

        _, supplementary_case_id = case_with_supplementary

        # case_with_supplementary sets L2 auth, re-assert it for clarity
        l2_user = create_mock_user(TEST_USER_L2_ID, "l2.analyst@spriggy.com", "L2_ANALYST")
        async def get_l2_user():
            return l2_user
        app.dependency_overrides[get_current_user] = get_l2_user

        # Claim as L2 analyst
        client.post(
            f"/cases/{supplementary_case_id}/claim",
            headers={"Authorization": "Bearer l2-token"}
        )

        # Create SMR recommendation as L2 analyst
        smr_response = client.post(
            f"/cases/{supplementary_case_id}/smr/recommend",
            json={
                "recommendation": "SUBMIT",
                "justification": "Supplementary information confirms suspicious activity",
                "suspiciousActivity": "Continued suspicious transaction patterns detected"
            },
            headers={"Authorization": "Bearer l2-token"}
        )
        assert smr_response.status_code in [200, 201], f"SMR recommend failed: {smr_response.json()}"

        # Switch to manager auth for approval
        manager_user = create_mock_user(TEST_USER_MANAGER_ID, "aml.manager@spriggy.com", "AML_MANAGER")
        async def get_manager_user():
            return manager_user
        app.dependency_overrides[get_current_user] = get_manager_user

        # Manager approves
        approval_response = client.post(
            f"/cases/{supplementary_case_id}/smr/approve",
            json={},
            headers={"Authorization": "Bearer manager-token"}
        )
        assert approval_response.status_code == 200, f"SMR approve failed: {approval_response.json()}"

        # Record AUSTRAC reference to mark SMR as FILED
        file_response = client.post(
            f"/cases/{supplementary_case_id}/smr/record-reference",
            json={"austracReference": "SMR-2026-SUPP-001"},
            headers={"Authorization": "Bearer manager-token"}
        )
        assert file_response.status_code == 200, f"SMR file failed: {file_response.json()}"

        # Now case can be closed
        close_response = client.post(
            f"/cases/{supplementary_case_id}/close",
            json={
                "reason": "SMR filed - investigation complete",
                "documentation": "Supplementary SMR filed to AUSTRAC with reference"
            },
            headers={"Authorization": "Bearer manager-token"}
        )
        assert close_response.status_code == 200, f"Close failed: {close_response.json()}"


class TestSupplementaryValidation:
    """Test validation for supplementary case creation."""

    def test_cannot_create_supplementary_from_open_case(
        self,
        client: TestClient,
        mock_oidc_auth_l2,
        open_case_id
    ):
        """
        Given an open case (not yet closed)
        When trying to create supplementary
        Then operation is rejected
        """
        response = client.post(
            f"/cases/{open_case_id}/create-supplementary",
            json={"reason": "New information"},
            headers={"Authorization": "Bearer l2-token"}
        )

        assert response.status_code == 400
        assert "closed" in response.json().get("detail", "").lower()

    def test_cannot_create_supplementary_without_smr(
        self,
        client: TestClient,
        mock_oidc_auth_l2,
        closed_case_without_smr
    ):
        """
        Given a closed case without SMR
        When trying to create supplementary
        Then operation is rejected
        """
        case_id = closed_case_without_smr

        response = client.post(
            f"/cases/{case_id}/create-supplementary",
            json={"reason": "New information"},
            headers={"Authorization": "Bearer l2-token"}
        )

        assert response.status_code == 400
        assert "SMR" in response.json().get("detail", "")

    def test_only_l2_or_manager_can_create_supplementary(
        self,
        client: TestClient,
        mock_oidc_auth,  # L1 analyst
        completed_smr_case
    ):
        """
        Given an L1 analyst
        When trying to create supplementary
        Then operation is forbidden
        """
        # Re-set L1 auth after completed_smr_case fixture (which sets manager auth)
        from src.main import app
        from src.middleware.auth import get_current_user
        from conftest import create_mock_user, TEST_USER_L1_ID

        l1_user = create_mock_user(TEST_USER_L1_ID, "l1.analyst@spriggy.com", "L1_ANALYST")
        async def get_l1_user():
            return l1_user
        app.dependency_overrides[get_current_user] = get_l1_user

        response = client.post(
            f"/cases/{completed_smr_case}/create-supplementary",
            json={"reason": "New information"},
            headers={"Authorization": "Bearer valid-token"}  # L1 token
        )

        assert response.status_code == 403


# Fixtures

@pytest.fixture
def seed_smr_users(db_session):
    """Seed test users for SMR workflow."""
    from src.models.user import User, UserRole
    from conftest import TEST_USER_L2_ID, TEST_USER_MANAGER_ID

    # Check if users already exist
    existing_l2 = db_session.query(User).filter(User.id == TEST_USER_L2_ID).first()
    if not existing_l2:
        l2_user = User(
            id=TEST_USER_L2_ID,
            email="l2.analyst@spriggy.com",
            role=UserRole.L2_ANALYST,
            tier="L2",
            is_active=True
        )
        db_session.add(l2_user)

    existing_mgr = db_session.query(User).filter(User.id == TEST_USER_MANAGER_ID).first()
    if not existing_mgr:
        manager_user = User(
            id=TEST_USER_MANAGER_ID,
            email="aml.manager@spriggy.com",
            role=UserRole.AML_MANAGER,
            tier=None,
            is_active=True
        )
        db_session.add(manager_user)

    db_session.commit()


@pytest.fixture
def completed_smr_case(client, mock_hmac_validation, db_session, seed_smr_users):
    """Create a completed case with filed SMR."""
    from uuid import UUID
    from conftest import TEST_USER_L2_ID, TEST_USER_MANAGER_ID, create_mock_user
    from src.main import app
    from src.middleware.auth import get_current_user

    # Ensure manager auth is active (may have been overridden by other fixtures)
    manager_user = create_mock_user(TEST_USER_MANAGER_ID, "aml.manager@spriggy.com", "AML_MANAGER")
    async def get_manager_user():
        return manager_user
    app.dependency_overrides[get_current_user] = get_manager_user

    # Create case via webhook (no auth needed for webhook)
    payload = {
        "verificationId": "test-verification-supp",
        "customerId": "cust-supp-001",
        "verificationType": "PEP_HIGH_CONFIDENCE",
        "outcome": "ALERT",
        "timestamp": datetime.utcnow().isoformat(),
        "customer": {"firstName": "Supplementary", "lastName": "Test"}
    }

    create_response = client.post(
        "/webhooks/greenid",
        json=payload,
        headers={"X-Webhook-Signature": "valid-signature"}
    )
    case_id = create_response.json()["id"]

    # Claim the case
    client.post(f"/cases/{case_id}/claim", headers={"Authorization": "Bearer manager-token"})

    # Create SMR recommendation (manager can also create SMR)
    smr_response = client.post(
        f"/cases/{case_id}/smr/recommend",
        json={
            "recommendation": "SUBMIT",
            "justification": "High risk PEP match confirmed through verification",
            "suspiciousActivity": "Customer matches politically exposed person database with high confidence"
        },
        headers={"Authorization": "Bearer manager-token"}
    )
    assert smr_response.status_code in [200, 201], f"SMR creation failed: {smr_response.json()}"

    # Fix the SMR recommender to be L2 (for proper segregation of duties)
    from src.models.smr_recommendation import SMRRecommendation
    smr_data = smr_response.json()
    smr = db_session.query(SMRRecommendation).filter(
        SMRRecommendation.id == UUID(smr_data["id"])
    ).first()
    if smr:
        smr.recommended_by_id = TEST_USER_L2_ID
        db_session.commit()
        db_session.refresh(smr)

    # Manager approves
    approve_response = client.post(
        f"/cases/{case_id}/smr/approve",
        json={},
        headers={"Authorization": "Bearer manager-token"}
    )
    assert approve_response.status_code == 200, f"SMR approval failed: {approve_response.json()}"

    # Close the case
    close_response = client.post(
        f"/cases/{case_id}/close",
        json={
            "reason": "SMR filed with AUSTRAC",
            "documentation": "SMR reference: SMR-2026-001. Case investigation complete with SMR filed."
        },
        headers={"Authorization": "Bearer manager-token"}
    )
    assert close_response.status_code == 200, f"Close failed: {close_response.json()}"

    return case_id


@pytest.fixture
def case_with_supplementary(client, completed_smr_case):
    """Create an original case with a supplementary."""
    from conftest import create_mock_user, TEST_USER_L2_ID
    from src.main import app
    from src.middleware.auth import get_current_user

    original_case_id = completed_smr_case

    # Set L2 auth explicitly (completed_smr_case leaves manager auth set)
    l2_user = create_mock_user(TEST_USER_L2_ID, "l2analyst@example.com", "L2_ANALYST")
    async def get_l2_user():
        return l2_user
    app.dependency_overrides[get_current_user] = get_l2_user

    response = client.post(
        f"/cases/{original_case_id}/create-supplementary",
        json={"reason": "Test supplementary case"},
        headers={"Authorization": "Bearer l2-token"}
    )

    supplementary_id = response.json()["id"]
    return original_case_id, supplementary_id


@pytest.fixture
def open_case_id(client, mock_oidc_auth, mock_hmac_validation):
    """Create an open case."""
    payload = {
        "verificationId": "test-verification-open",
        "customerId": "cust-open-001",
        "verificationType": "KYC_REMEDIATION",
        "outcome": "ALERT",
        "timestamp": datetime.utcnow().isoformat(),
        "customer": {"firstName": "Open", "lastName": "Case"}
    }

    response = client.post(
        "/webhooks/greenid",
        json=payload,
        headers={"X-Webhook-Signature": "valid-signature"}
    )
    return response.json()["id"]


@pytest.fixture
def closed_case_without_smr(client, mock_oidc_auth, mock_hmac_validation):
    """Create a closed case without SMR."""
    payload = {
        "verificationId": "test-verification-no-smr",
        "customerId": "cust-no-smr-001",
        "verificationType": "KYC_REMEDIATION",
        "outcome": "ALERT",
        "timestamp": datetime.utcnow().isoformat(),
        "customer": {"firstName": "NoSmr", "lastName": "Case"}
    }

    create_response = client.post(
        "/webhooks/greenid",
        json=payload,
        headers={"X-Webhook-Signature": "valid-signature"}
    )
    case_id = create_response.json()["id"]

    # Claim and close without SMR
    client.post(
        f"/cases/{case_id}/claim",
        headers={"Authorization": "Bearer valid-token"}
    )

    close_resp = client.post(
        f"/cases/{case_id}/close",
        json={
            "reason": "FALSE_POSITIVE",
            "documentation": "No suspicious activity found after investigation"
        },
        headers={"Authorization": "Bearer valid-token"}
    )
    assert close_resp.status_code == 200, f"Close failed: {close_resp.json()}"

    return case_id


@pytest.fixture
def mock_oidc_auth_l2(mocker):
    """Mock OIDC authentication for L2 analyst."""
    from conftest import create_mock_user, TEST_USER_L2_ID

    mock_user = create_mock_user(TEST_USER_L2_ID, "l2analyst@example.com", "L2_ANALYST")

    mocker.patch(
        "src.middleware.auth.get_current_user",
        return_value=mock_user
    )
    return mock_user


@pytest.fixture
def mock_oidc_auth_manager(mocker):
    """Mock OIDC authentication for manager."""
    from conftest import create_mock_user, TEST_USER_MANAGER_ID

    mock_user = create_mock_user(TEST_USER_MANAGER_ID, "manager@example.com", "AML_MANAGER")

    mocker.patch(
        "src.middleware.auth.get_current_user",
        return_value=mock_user
    )
    return mock_user
