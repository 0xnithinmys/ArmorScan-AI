"""Add target authorization proof records.

Revision ID: 0003_target_authorization_proofs
Revises: 0002_phase4_to_8_fields
Create Date: 2026-05-28
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_target_authorization_proofs"
down_revision = "0002_phase4_to_8_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "target_authorization_proofs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("target_id", sa.String(length=36), nullable=False),
        sa.Column("created_by_id", sa.String(length=36), nullable=True),
        sa.Column("proof_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("challenge_token", sa.String(length=128), nullable=False),
        sa.Column("verification_target", sa.Text(), nullable=False),
        sa.Column("expected_value", sa.Text(), nullable=False),
        sa.Column("submitted_value", sa.Text(), nullable=True),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_target_authorization_proofs_target_id"),
        "target_authorization_proofs",
        ["target_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_target_authorization_proofs_created_by_id"),
        "target_authorization_proofs",
        ["created_by_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_target_authorization_proofs_proof_type"),
        "target_authorization_proofs",
        ["proof_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_target_authorization_proofs_status"),
        "target_authorization_proofs",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_target_authorization_proofs_challenge_token"),
        "target_authorization_proofs",
        ["challenge_token"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_target_authorization_proofs_challenge_token"),
        table_name="target_authorization_proofs",
    )
    op.drop_index(
        op.f("ix_target_authorization_proofs_status"),
        table_name="target_authorization_proofs",
    )
    op.drop_index(
        op.f("ix_target_authorization_proofs_proof_type"),
        table_name="target_authorization_proofs",
    )
    op.drop_index(
        op.f("ix_target_authorization_proofs_created_by_id"),
        table_name="target_authorization_proofs",
    )
    op.drop_index(
        op.f("ix_target_authorization_proofs_target_id"),
        table_name="target_authorization_proofs",
    )
    op.drop_table("target_authorization_proofs")
