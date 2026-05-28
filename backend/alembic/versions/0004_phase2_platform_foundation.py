"""Add Phase 2 platform foundation tables.

Revision ID: 0004_phase2_platform_foundation
Revises: 0003_target_authorization_proofs
Create Date: 2026-05-28
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_phase2_platform_foundation"
down_revision = "0003_target_authorization_proofs"
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
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("created_by_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_organizations_slug"), "organizations", ["slug"], unique=True)
    op.create_index(op.f("ix_organizations_created_by_id"), "organizations", ["created_by_id"], unique=False)

    op.create_table(
        "memberships",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_membership_org_user"),
    )
    op.create_index(op.f("ix_memberships_organization_id"), "memberships", ["organization_id"], unique=False)
    op.create_index(op.f("ix_memberships_user_id"), "memberships", ["user_id"], unique=False)
    op.create_index(op.f("ix_memberships_role"), "memberships", ["role"], unique=False)

    op.create_table(
        "teams",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_teams_organization_id"), "teams", ["organization_id"], unique=False)
    op.create_index(op.f("ix_teams_slug"), "teams", ["slug"], unique=False)

    _add_if_missing(
        "targets",
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index(op.f("ix_targets_organization_id"), "targets", ["organization_id"], unique=False)

    op.create_table(
        "scan_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=True),
        sa.Column("created_by_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scan_type", sa.String(length=32), nullable=False),
        sa.Column("policy_tier", sa.String(length=32), nullable=False),
        sa.Column("settings_json", sa.JSON(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scan_profiles_organization_id"), "scan_profiles", ["organization_id"], unique=False)
    op.create_index(op.f("ix_scan_profiles_created_by_id"), "scan_profiles", ["created_by_id"], unique=False)

    _add_if_missing(
        "scans",
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True),
    )
    _add_if_missing(
        "scans",
        sa.Column("scan_profile_id", sa.String(length=36), sa.ForeignKey("scan_profiles.id", ondelete="SET NULL"), nullable=True),
    )
    _add_if_missing(
        "scans",
        sa.Column("parent_scan_id", sa.String(length=36), sa.ForeignKey("scans.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index(op.f("ix_scans_organization_id"), "scans", ["organization_id"], unique=False)
    op.create_index(op.f("ix_scans_scan_profile_id"), "scans", ["scan_profile_id"], unique=False)
    op.create_index(op.f("ix_scans_parent_scan_id"), "scans", ["parent_scan_id"], unique=False)

    op.create_table(
        "scan_artifacts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("scan_id", sa.String(length=36), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("uri", sa.Text(), nullable=True),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scan_artifacts_scan_id"), "scan_artifacts", ["scan_id"], unique=False)
    op.create_index(op.f("ix_scan_artifacts_artifact_type"), "scan_artifacts", ["artifact_type"], unique=False)

    op.create_table(
        "finding_evidence",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("finding_id", sa.String(length=36), nullable=False),
        sa.Column("evidence_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("artifact_uri", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_by_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_finding_evidence_finding_id"), "finding_evidence", ["finding_id"], unique=False)
    op.create_index(op.f("ix_finding_evidence_evidence_type"), "finding_evidence", ["evidence_type"], unique=False)
    op.create_index(op.f("ix_finding_evidence_created_by_id"), "finding_evidence", ["created_by_id"], unique=False)

    op.create_table(
        "finding_comments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("finding_id", sa.String(length=36), nullable=False),
        sa.Column("author_id", sa.String(length=36), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_finding_comments_finding_id"), "finding_comments", ["finding_id"], unique=False)
    op.create_index(op.f("ix_finding_comments_author_id"), "finding_comments", ["author_id"], unique=False)

    op.create_table(
        "finding_suppressions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("finding_id", sa.String(length=36), nullable=False),
        sa.Column("created_by_id", sa.String(length=36), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_finding_suppressions_finding_id"), "finding_suppressions", ["finding_id"], unique=False)
    op.create_index(op.f("ix_finding_suppressions_created_by_id"), "finding_suppressions", ["created_by_id"], unique=False)
    op.create_index(op.f("ix_finding_suppressions_status"), "finding_suppressions", ["status"], unique=False)

    op.create_table(
        "remediation_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("finding_id", sa.String(length=36), nullable=False),
        sa.Column("actor_id", sa.String(length=36), nullable=True),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_remediation_history_finding_id"), "remediation_history", ["finding_id"], unique=False)
    op.create_index(op.f("ix_remediation_history_actor_id"), "remediation_history", ["actor_id"], unique=False)
    op.create_index(op.f("ix_remediation_history_to_status"), "remediation_history", ["to_status"], unique=False)

    op.create_table(
        "credential_references",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=True),
        sa.Column("created_by_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("credential_type", sa.String(length=64), nullable=False),
        sa.Column("vault_provider", sa.String(length=64), nullable=False),
        sa.Column("vault_reference", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_credential_references_organization_id"), "credential_references", ["organization_id"], unique=False)
    op.create_index(op.f("ix_credential_references_created_by_id"), "credential_references", ["created_by_id"], unique=False)
    op.create_index(op.f("ix_credential_references_credential_type"), "credential_references", ["credential_type"], unique=False)

    op.create_table(
        "webhook_integrations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=True),
        sa.Column("created_by_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("event_types", sa.JSON(), nullable=False),
        sa.Column("target_url", sa.Text(), nullable=False),
        sa.Column("secret_reference", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_webhook_integrations_organization_id"), "webhook_integrations", ["organization_id"], unique=False)
    op.create_index(op.f("ix_webhook_integrations_created_by_id"), "webhook_integrations", ["created_by_id"], unique=False)
    op.create_index(op.f("ix_webhook_integrations_is_active"), "webhook_integrations", ["is_active"], unique=False)

    op.create_table(
        "report_exports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("scan_id", sa.String(length=36), nullable=False),
        sa.Column("requested_by_id", sa.String(length=36), nullable=True),
        sa.Column("export_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("artifact_uri", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_report_exports_scan_id"), "report_exports", ["scan_id"], unique=False)
    op.create_index(op.f("ix_report_exports_requested_by_id"), "report_exports", ["requested_by_id"], unique=False)
    op.create_index(op.f("ix_report_exports_export_type"), "report_exports", ["export_type"], unique=False)
    op.create_index(op.f("ix_report_exports_status"), "report_exports", ["status"], unique=False)

    op.create_table(
        "tool_inventory",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("version", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tool_inventory_name"), "tool_inventory", ["name"], unique=True)
    op.create_index(op.f("ix_tool_inventory_category"), "tool_inventory", ["category"], unique=False)
    op.create_index(op.f("ix_tool_inventory_status"), "tool_inventory", ["status"], unique=False)

    op.create_table(
        "agent_execution_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("scan_id", sa.String(length=36), nullable=True),
        sa.Column("agent_name", sa.String(length=128), nullable=False),
        sa.Column("stage", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_execution_logs_scan_id"), "agent_execution_logs", ["scan_id"], unique=False)
    op.create_index(op.f("ix_agent_execution_logs_agent_name"), "agent_execution_logs", ["agent_name"], unique=False)
    op.create_index(op.f("ix_agent_execution_logs_stage"), "agent_execution_logs", ["stage"], unique=False)
    op.create_index(op.f("ix_agent_execution_logs_status"), "agent_execution_logs", ["status"], unique=False)


def downgrade() -> None:
    for table in (
        "agent_execution_logs",
        "tool_inventory",
        "report_exports",
        "webhook_integrations",
        "credential_references",
        "remediation_history",
        "finding_suppressions",
        "finding_comments",
        "finding_evidence",
        "scan_artifacts",
    ):
        op.drop_table(table)
    for index_name in ("ix_scans_parent_scan_id", "ix_scans_scan_profile_id", "ix_scans_organization_id"):
        op.drop_index(op.f(index_name), table_name="scans")
    for column in ("parent_scan_id", "scan_profile_id", "organization_id"):
        if column in _columns("scans"):
            op.drop_column("scans", column)
    op.drop_table("scan_profiles")
    op.drop_index(op.f("ix_targets_organization_id"), table_name="targets")
    if "organization_id" in _columns("targets"):
        op.drop_column("targets", "organization_id")
    op.drop_table("teams")
    op.drop_table("memberships")
    op.drop_index(op.f("ix_organizations_created_by_id"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_slug"), table_name="organizations")
    op.drop_table("organizations")
