"""Add agent policy scanner and risk reporting fields.

Revision ID: 0002_phase4_to_8_fields
Revises: 0001_initial_schema
Create Date: 2026-05-28
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_phase4_to_8_fields"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table_name)}


def _add_if_missing(table_name: str, column: sa.Column) -> None:
    if column.name not in _columns(table_name):
        op.add_column(table_name, column)


def upgrade() -> None:
    _add_if_missing("targets", sa.Column("authorization_proof_type", sa.String(length=64), nullable=True))
    _add_if_missing("targets", sa.Column("authorization_proof", sa.Text(), nullable=True))

    scan_columns = _columns("scans")
    if "agent_trace" not in scan_columns:
        op.add_column("scans", sa.Column("agent_trace", sa.JSON(), nullable=True))
        op.execute("UPDATE scans SET agent_trace = '[]' WHERE agent_trace IS NULL")
        op.alter_column("scans", "agent_trace", nullable=False)
    _add_if_missing("scans", sa.Column("report_json", sa.JSON(), nullable=True))
    _add_if_missing("scans", sa.Column("armoriq_token", sa.Text(), nullable=True))
    _add_if_missing("scans", sa.Column("intent_plan", sa.JSON(), nullable=True))
    if "policy_decisions" not in scan_columns:
        op.add_column("scans", sa.Column("policy_decisions", sa.JSON(), nullable=True))
        op.execute("UPDATE scans SET policy_decisions = '[]' WHERE policy_decisions IS NULL")
        op.alter_column("scans", "policy_decisions", nullable=False)

    finding_columns = _columns("findings")
    if "risk_score" not in finding_columns:
        op.add_column("findings", sa.Column("risk_score", sa.Integer(), nullable=True))
        op.execute("UPDATE findings SET risk_score = 0 WHERE risk_score IS NULL")
        op.alter_column("findings", "risk_score", nullable=False)
        op.create_index(op.f("ix_findings_risk_score"), "findings", ["risk_score"], unique=False)
    if "risk_rating" not in finding_columns:
        op.add_column("findings", sa.Column("risk_rating", sa.String(length=16), nullable=True))
        op.execute("UPDATE findings SET risk_rating = 'info' WHERE risk_rating IS NULL")
        op.alter_column("findings", "risk_rating", nullable=False)
        op.create_index(op.f("ix_findings_risk_rating"), "findings", ["risk_rating"], unique=False)
    _add_if_missing("findings", sa.Column("business_impact", sa.Text(), nullable=True))
    _add_if_missing("findings", sa.Column("remediation", sa.Text(), nullable=True))
    if "risk_factors" not in finding_columns:
        op.add_column("findings", sa.Column("risk_factors", sa.JSON(), nullable=True))
        op.execute("UPDATE findings SET risk_factors = '{}' WHERE risk_factors IS NULL")
        op.alter_column("findings", "risk_factors", nullable=False)


def downgrade() -> None:
    for index_name in ("ix_findings_risk_score", "ix_findings_risk_rating"):
        try:
            op.drop_index(op.f(index_name), table_name="findings")
        except Exception:
            pass
    for table_name, columns in {
        "findings": ["risk_factors", "remediation", "business_impact", "risk_rating", "risk_score"],
        "scans": ["policy_decisions", "intent_plan", "armoriq_token", "report_json", "agent_trace"],
        "targets": ["authorization_proof", "authorization_proof_type"],
    }.items():
        existing = _columns(table_name)
        for column in columns:
            if column in existing:
                op.drop_column(table_name, column)
