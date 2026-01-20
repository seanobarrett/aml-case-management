"""
Migration for audit log immutability constraints.

Creates tables and triggers that enforce:
- Audit logs cannot be updated after creation
- Audit logs cannot be deleted
- Timeline entries follow same immutability rules

References:
- D1: Append-only log with event sourcing
- Principle I: Immutable Audit Trail (NON-NEGOTIABLE)
- FR-061: 7-year retention
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# Revision identifiers
revision = "002_audit_immutability"
down_revision = "001_core_entities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create audit tables with immutability constraints."""

    # Audit logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("action_detail", sa.Text(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_audit_logs_action_type", "audit_logs", ["action_type"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_case_id", "audit_logs", ["case_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # Timeline entries table
    op.create_table(
        "timeline_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id"), nullable=False),
        sa.Column("entry_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("acting_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_timeline_entries_case_id", "timeline_entries", ["case_id"])
    op.create_index("ix_timeline_entries_entry_type", "timeline_entries", ["entry_type"])
    op.create_index("ix_timeline_entries_created_at", "timeline_entries", ["created_at"])

    # Create immutability trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_audit_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            IF TG_OP = 'UPDATE' THEN
                RAISE EXCEPTION 'Audit records cannot be modified (immutable audit trail)';
            ELSIF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Audit records cannot be deleted (immutable audit trail - 7 year retention required)';
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Apply immutability triggers to audit_logs
    op.execute("""
        CREATE TRIGGER audit_logs_immutable_update
        BEFORE UPDATE ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_modification();
    """)

    op.execute("""
        CREATE TRIGGER audit_logs_immutable_delete
        BEFORE DELETE ON audit_logs
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_modification();
    """)

    # Apply immutability triggers to timeline_entries
    op.execute("""
        CREATE TRIGGER timeline_entries_immutable_update
        BEFORE UPDATE ON timeline_entries
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_modification();
    """)

    op.execute("""
        CREATE TRIGGER timeline_entries_immutable_delete
        BEFORE DELETE ON timeline_entries
        FOR EACH ROW
        EXECUTE FUNCTION prevent_audit_modification();
    """)

    # Add comment documenting retention requirement
    op.execute("""
        COMMENT ON TABLE audit_logs IS
        'Immutable audit log with 7-year retention requirement per AUSTRAC AML/CTF regulations. Records cannot be modified or deleted.';
    """)

    op.execute("""
        COMMENT ON TABLE timeline_entries IS
        'Immutable case timeline entries providing human-readable case history. Records cannot be modified or deleted.';
    """)


def downgrade() -> None:
    """Remove audit tables and triggers."""

    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS audit_logs_immutable_update ON audit_logs")
    op.execute("DROP TRIGGER IF EXISTS audit_logs_immutable_delete ON audit_logs")
    op.execute("DROP TRIGGER IF EXISTS timeline_entries_immutable_update ON timeline_entries")
    op.execute("DROP TRIGGER IF EXISTS timeline_entries_immutable_delete ON timeline_entries")

    # Drop function
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_modification()")

    # Drop tables
    op.drop_table("timeline_entries")
    op.drop_table("audit_logs")
