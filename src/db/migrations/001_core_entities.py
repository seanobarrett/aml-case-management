"""
Initial schema migration for core entities.

Creates tables for:
- Case: Main case record for AML investigations
- Customer: Customer snapshot at case creation (immutable)
- User: System users with RBAC roles
- Assignment: Case-to-analyst assignments
- WebhookReceipt: Duplicate webhook detection

References:
- D8: Optimistic locking with version column
- D9: Case reference sequence (AML-NNNN)
- EC-001: Concurrent updates handled via version column
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# Revision identifiers
revision = "001_core_entities"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create core entity tables."""

    # Create case reference sequence (D9)
    op.execute("CREATE SEQUENCE IF NOT EXISTS case_ref_seq START WITH 1001")

    # Enum types
    op.execute("""
        CREATE TYPE case_status AS ENUM (
            'OPEN',
            'ASSIGNED',
            'PENDING_INFORMATION',
            'ESCALATED',
            'PENDING_APPROVAL',
            'APPROVED',
            'CLOSED'
        )
    """)

    op.execute("""
        CREATE TYPE case_type AS ENUM (
            'KYC_REMEDIATION',
            'PEP_SCREENING',
            'PEP_HIGH_CONFIDENCE',
            'PEP_LOW_CONFIDENCE',
            'SANCTIONS_ONBOARDING',
            'SANCTIONS_EXISTING_CUSTOMER',
            'SUSPICIOUS_ACTIVITY'
        )
    """)

    op.execute("""
        CREATE TYPE case_tier AS ENUM (
            'L1',
            'L2'
        )
    """)

    op.execute("""
        CREATE TYPE user_role AS ENUM (
            'L1_ANALYST',
            'L2_ANALYST',
            'AML_MANAGER',
            'READ_ONLY'
        )
    """)

    op.execute("""
        CREATE TYPE l2_review_status AS ENUM (
            'NOT_REQUIRED',
            'PENDING_REVIEW',
            'REVIEWED_ACCEPTED',
            'REVIEWED_REOPENED'
        )
    """)

    op.execute("""
        CREATE TYPE assignment_reason AS ENUM (
            'MANUAL_CLAIM',
            'ESCALATION',
            'REOPEN',
            'ROLE_CHANGE',
            'ADMIN_REASSIGN'
        )
    """)

    # Users table (D5: RBAC roles)
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("role", sa.Enum("L1_ANALYST", "L2_ANALYST", "AML_MANAGER", "READ_ONLY", name="user_role"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_role", "users", ["role"])

    # Customers table (snapshot at case creation)
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("external_customer_id", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(255), nullable=True),
        sa.Column("last_name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("account_status", sa.String(50), nullable=True),
        sa.Column("onboarding_status", sa.String(50), nullable=True),
        sa.Column("account_closed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_customers_external_id", "customers", ["external_customer_id"])

    # Cases table
    op.create_table(
        "cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "case_reference",
            sa.String(20),
            nullable=False,
            unique=True,
            server_default=sa.text("'AML-' || nextval('case_ref_seq')::text")
        ),
        sa.Column("case_type", sa.Enum(
            "KYC_REMEDIATION", "PEP_SCREENING", "PEP_HIGH_CONFIDENCE",
            "PEP_LOW_CONFIDENCE", "SANCTIONS_ONBOARDING",
            "SANCTIONS_EXISTING_CUSTOMER", "SUSPICIOUS_ACTIVITY",
            name="case_type"
        ), nullable=False),
        sa.Column("status", sa.Enum(
            "OPEN", "ASSIGNED", "PENDING_INFORMATION", "ESCALATED",
            "PENDING_APPROVAL", "APPROVED", "CLOSED",
            name="case_status"
        ), nullable=False, server_default=sa.text("'OPEN'")),
        sa.Column("tier", sa.Enum("L1", "L2", name="case_tier"), nullable=False, server_default=sa.text("'L1'")),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("assigned_to_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("l2_review_status", sa.Enum(
            "NOT_REQUIRED", "PENDING_REVIEW", "REVIEWED_ACCEPTED", "REVIEWED_REOPENED",
            name="l2_review_status"
        ), nullable=False, server_default=sa.text("'NOT_REQUIRED'")),
        sa.Column("sla_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sla_breached", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("closure_reason", sa.Text(), nullable=True),
        sa.Column("closure_documentation", sa.Text(), nullable=True),
        sa.Column("enhanced_monitoring", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("external_verification_id", sa.String(255), nullable=True),
        sa.Column("external_screening_id", sa.String(255), nullable=True),
        sa.Column("pep_match_score", sa.Integer(), nullable=True),
        sa.Column("source_webhook_payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
    )
    op.create_index("ix_cases_case_reference", "cases", ["case_reference"])
    op.create_index("ix_cases_status", "cases", ["status"])
    op.create_index("ix_cases_tier", "cases", ["tier"])
    op.create_index("ix_cases_customer_id", "cases", ["customer_id"])
    op.create_index("ix_cases_assigned_to_id", "cases", ["assigned_to_id"])
    op.create_index("ix_cases_sla_deadline", "cases", ["sla_deadline"])
    op.create_index("ix_cases_l2_review_status", "cases", ["l2_review_status"])

    # Assignments table (case-analyst assignment history)
    op.create_table(
        "assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reason", sa.Enum(
            "MANUAL_CLAIM", "ESCALATION", "REOPEN", "ROLE_CHANGE", "ADMIN_REASSIGN",
            name="assignment_reason"
        ), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("unassigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index("ix_assignments_case_id", "assignments", ["case_id"])
    op.create_index("ix_assignments_user_id", "assignments", ["user_id"])
    op.create_index("ix_assignments_active", "assignments", ["case_id", "is_active"])

    # Webhook receipts table (duplicate detection - D3, EC-005)
    op.create_table(
        "webhook_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("payload_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("webhook_source", sa.String(50), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_webhook_receipts_payload_hash", "webhook_receipts", ["payload_hash"])
    op.create_index("ix_webhook_receipts_source_external", "webhook_receipts", ["webhook_source", "external_id"])

    # Updated_at trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            NEW.version = OLD.version + 1;
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    # Apply updated_at trigger to tables with version column
    for table in ["users", "cases"]:
        op.execute(f"""
            CREATE TRIGGER update_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """)


def downgrade() -> None:
    """Drop core entity tables."""
    # Drop triggers
    for table in ["users", "cases"]:
        op.execute(f"DROP TRIGGER IF EXISTS update_{table}_updated_at ON {table}")

    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")

    # Drop tables
    op.drop_table("webhook_receipts")
    op.drop_table("assignments")
    op.drop_table("cases")
    op.drop_table("customers")
    op.drop_table("users")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS assignment_reason")
    op.execute("DROP TYPE IF EXISTS l2_review_status")
    op.execute("DROP TYPE IF EXISTS user_role")
    op.execute("DROP TYPE IF EXISTS case_tier")
    op.execute("DROP TYPE IF EXISTS case_type")
    op.execute("DROP TYPE IF EXISTS case_status")

    # Drop sequence
    op.execute("DROP SEQUENCE IF EXISTS case_ref_seq")
