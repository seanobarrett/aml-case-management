"""Pytest configuration and fixtures for AML Case Management tests."""

import os
from uuid import UUID

# Set test database URL BEFORE any other imports to ensure SQLite is used
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from typing import Generator
from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, String, JSON
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.compiler import compiles

# Test database URL - uses in-memory SQLite for unit tests
TEST_DATABASE_URL = "sqlite:///:memory:"

# Fixed UUIDs for test users (consistent across tests)
TEST_USER_L1_ID = UUID("11111111-1111-1111-1111-111111111111")
TEST_USER_L2_ID = UUID("22222222-2222-2222-2222-222222222222")
TEST_USER_MANAGER_ID = UUID("33333333-3333-3333-3333-333333333333")
TEST_USER_READONLY_ID = UUID("44444444-4444-4444-4444-444444444444")

# Register JSONB compiler for SQLite - renders as JSON
@compiles(postgresql.JSONB, 'sqlite')
def compile_jsonb_sqlite(element, compiler, **kw):
    return compiler.visit_JSON(element, **kw)


def create_mock_user(user_id: UUID, email: str, role_str: str):
    """
    Create a properly configured CurrentUser for testing.

    Args:
        user_id: UUID for the user
        email: User email
        role_str: Role string (L1_ANALYST, L2_ANALYST, AML_MANAGER, READ_ONLY)

    Returns:
        CurrentUser instance
    """
    from src.middleware.auth import CurrentUser
    from src.models.user import UserRole, ROLE_PERMISSIONS

    role = UserRole(role_str)
    permissions = ROLE_PERMISSIONS.get(role, {})

    return CurrentUser(
        user_id=user_id,
        email=email,
        role=role,
        permissions=permissions
    )


@pytest.fixture(scope="session")
def engine():
    """Get the database engine from session module (uses env var we set above)."""
    from src.db.session import engine
    return engine


@pytest.fixture(scope="function")
def db_session(engine) -> Generator[Session, None, None]:
    """Create a new database session for each test."""
    # Import all models to register them with Base.metadata
    from src.models import (
        Base, Case, Customer, User, Assignment, WebhookReceipt,
        AuditLog, TimelineEntry, Notification, CustomerCommunication,
        InvestigationFindings, SMRRecommendation, OnboardingBlock,
        CaseLink, EDDChecklist, PEPThresholdConfig, HolidayOverride,
        AccountRestriction, CommunicationTemplate
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()
        # Clean up all data for next test using a new connection
        with engine.connect() as conn:
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(table.delete())
            conn.commit()


@pytest.fixture
def mock_hmac_validation():
    """Mock HMAC signature validation for webhook tests."""
    with patch("src.middleware.webhook_auth.validate_hmac_signature") as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def real_webhook_validation():
    """
    Enable real HMAC signature validation for tests.

    Sets a known webhook secret so signature validation actually runs.
    Without this, validation passes in development mode when no secret is set.
    """
    original_greenid = os.environ.get("GREENID_WEBHOOK_SECRET")
    original_indue = os.environ.get("INDUE_WEBHOOK_SECRET")
    original_env = os.environ.get("ENVIRONMENT")

    # Set secrets and production environment
    os.environ["GREENID_WEBHOOK_SECRET"] = "test-secret-greenid"
    os.environ["INDUE_WEBHOOK_SECRET"] = "test-secret-indue"
    os.environ["ENVIRONMENT"] = "production"

    # Reload the module to pick up new env vars
    import src.middleware.webhook_auth as webhook_auth
    import importlib
    importlib.reload(webhook_auth)

    yield {
        "greenid_secret": "test-secret-greenid",
        "indue_secret": "test-secret-indue"
    }

    # Restore original values
    if original_greenid is None:
        os.environ.pop("GREENID_WEBHOOK_SECRET", None)
    else:
        os.environ["GREENID_WEBHOOK_SECRET"] = original_greenid

    if original_indue is None:
        os.environ.pop("INDUE_WEBHOOK_SECRET", None)
    else:
        os.environ["INDUE_WEBHOOK_SECRET"] = original_indue

    if original_env is None:
        os.environ.pop("ENVIRONMENT", None)
    else:
        os.environ["ENVIRONMENT"] = original_env

    # Reload again to restore original behavior
    importlib.reload(webhook_auth)


@pytest.fixture
def unauthenticated(client):
    """
    Remove authentication for testing unauthenticated access.

    The client fixture sets up default auth, so this clears it
    to test endpoints that should reject unauthenticated requests.
    """
    from src.main import app
    from src.middleware.auth import get_current_user
    from fastapi import HTTPException, status

    async def no_auth():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    app.dependency_overrides[get_current_user] = no_auth
    yield
    # Restore default after test (client fixture will reset on next test anyway)


@pytest.fixture
def mock_auth_l1(client):
    """Mock authentication as L1 Analyst using FastAPI dependency override."""
    from src.main import app
    from src.middleware.auth import get_current_user

    mock_user = create_mock_user(TEST_USER_L1_ID, "l1.analyst@spriggy.com", "L1_ANALYST")

    async def override_auth():
        return mock_user

    app.dependency_overrides[get_current_user] = override_auth
    yield mock_user


@pytest.fixture
def mock_auth_l2(client):
    """Mock authentication as L2 Analyst using FastAPI dependency override."""
    from src.main import app
    from src.middleware.auth import get_current_user

    mock_user = create_mock_user(TEST_USER_L2_ID, "l2.analyst@spriggy.com", "L2_ANALYST")

    async def override_auth():
        return mock_user

    app.dependency_overrides[get_current_user] = override_auth
    yield mock_user


@pytest.fixture
def mock_auth_manager(client):
    """Mock authentication as AML Manager using FastAPI dependency override."""
    from src.main import app
    from src.middleware.auth import get_current_user

    mock_user = create_mock_user(TEST_USER_MANAGER_ID, "aml.manager@spriggy.com", "AML_MANAGER")

    async def override_auth():
        return mock_user

    app.dependency_overrides[get_current_user] = override_auth
    yield mock_user


@pytest.fixture
def mock_auth_readonly(client):
    """Mock authentication as Read-Only user using FastAPI dependency override."""
    from src.main import app
    from src.middleware.auth import get_current_user

    mock_user = create_mock_user(TEST_USER_READONLY_ID, "auditor@spriggy.com", "READ_ONLY")

    async def override_auth():
        return mock_user

    app.dependency_overrides[get_current_user] = override_auth
    yield mock_user


# Legacy fixture names for backward compatibility
@pytest.fixture
def mock_oidc_auth(mock_auth_l1):
    """Mock OIDC authentication for API tests (defaults to L1)."""
    yield mock_auth_l1


@pytest.fixture
def mock_oidc_auth_l2(mock_auth_l2):
    """Mock OIDC authentication for L2 API tests."""
    yield mock_auth_l2


@pytest.fixture
def mock_oidc_auth_manager(mock_auth_manager):
    """Mock OIDC authentication for Manager API tests."""
    yield mock_auth_manager


@pytest.fixture
def test_user_l1():
    """L1 Analyst test user data."""
    return {
        "id": str(TEST_USER_L1_ID),
        "email": "l1.analyst@spriggy.com",
        "role": "L1_ANALYST",
        "is_active": True
    }


@pytest.fixture
def test_user_l2():
    """L2 Analyst test user data."""
    return {
        "id": str(TEST_USER_L2_ID),
        "email": "l2.analyst@spriggy.com",
        "role": "L2_ANALYST",
        "is_active": True
    }


@pytest.fixture
def test_user_manager():
    """AML Manager test user data."""
    return {
        "id": str(TEST_USER_MANAGER_ID),
        "email": "aml.manager@spriggy.com",
        "role": "AML_MANAGER",
        "is_active": True
    }


@pytest.fixture
def test_user_readonly():
    """Read-Only test user data."""
    return {
        "id": str(TEST_USER_READONLY_ID),
        "email": "auditor@spriggy.com",
        "role": "READ_ONLY",
        "is_active": True
    }


@pytest.fixture
def greenid_webhook_payload():
    """Sample GreenID webhook payload for KYC remediation."""
    return {
        "verificationId": "verify-123",
        "customerId": "cust-456",
        "verificationType": "KYC_REMEDIATION",
        "outcome": "REFER",
        "timestamp": "2026-01-15T10:30:00Z",
        "customer": {
            "firstName": "John",
            "lastName": "Doe",
            "email": "john.doe@example.com",
            "dateOfBirth": "1990-01-15"
        }
    }


@pytest.fixture
def indue_webhook_payload():
    """Sample Indue webhook payload for PEP/Sanctions screening."""
    return {
        "screeningId": "screen-789",
        "customerId": "cust-456",
        "screeningType": "PEP",
        "matchScore": 85,
        "matchDetails": {
            "name": "John Doe",
            "matchType": "EXACT",
            "category": "PEP"
        },
        "timestamp": "2026-01-15T10:35:00Z"
    }


@pytest.fixture
def client(engine, db_session) -> Generator[TestClient, None, None]:
    """
    Create FastAPI test client with test database.

    Overrides database dependency to use test session.
    Automatically mocks authentication as an AML Manager for all requests.
    """
    from src.main import app
    from src.db.session import get_db
    from src.middleware.auth import get_current_user

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    # Create default mock user (AML Manager for most permissions)
    default_user = create_mock_user(TEST_USER_MANAGER_ID, "aml.manager@spriggy.com", "AML_MANAGER")

    async def override_get_current_user():
        return default_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
