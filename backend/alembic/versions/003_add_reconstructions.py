"""add reconstructions table

Revision ID: 003_add_reconstructions
Revises: 002_add_proposal_candidate_id
Create Date: 2026-08-13

Phase 21.2: Add Reconstruction persistence layer.
Reconstruction is a persistent semantic version object between Evidence and Candidate.

- Saves semantic_summary extracted from Evidence chain
- Supports version chain via parent_reconstruction_id
- Links to exactly one Candidate (candidate_id UNIQUE)
- Workspace and Entity scoped
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_add_reconstructions'
down_revision = '002_add_proposal_candidate_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create reconstructions table
    op.create_table(
        'reconstructions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=False),
        sa.Column('semantic_summary', sa.Text(), nullable=False),
        sa.Column('decision_type', sa.String(50), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False, default=0.0),
        sa.Column('evidence_refs', sa.dialects.postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('evidence_count', sa.Integer(), nullable=False, default=0),
        sa.Column('parent_reconstruction_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='active'),
        sa.Column('candidate_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id', name='reconstructions_pkey'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_reconstruction_id'], ['reconstructions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='SET NULL'),
        sa.CheckConstraint(
            "status IN ('initial', 'active', 'updated', 'superseded', 'archived')",
            name='chk_reconstruction_status'
        ),
        sa.CheckConstraint(
            "evidence_count >= 0",
            name='chk_reconstruction_evidence_count'
        ),
        sa.CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name='chk_reconstruction_confidence'
        ),
    )

    # Index for parent_reconstruction_id lookups (version chain)
    op.create_index(
        'idx_reconstructions_parent',
        'reconstructions',
        ['parent_reconstruction_id']
    )

    # Index for entity lookups
    op.create_index(
        'idx_reconstructions_entity',
        'reconstructions',
        ['entity_id']
    )

    # Index for status lookups
    op.create_index(
        'idx_reconstructions_status',
        'reconstructions',
        ['status']
    )

    # Unique constraint: each Candidate can only have one active Reconstruction
    op.create_index(
        'uk_reconstructions_one_active_per_candidate',
        'reconstructions',
        ['candidate_id'],
        unique=True,
        postgresql_where=sa.text("status = 'active'")
    )


def downgrade() -> None:
    op.drop_index('uk_reconstructions_one_active_per_candidate', table_name='reconstructions')
    op.drop_index('idx_reconstructions_status', table_name='reconstructions')
    op.drop_index('idx_reconstructions_entity', table_name='reconstructions')
    op.drop_index('idx_reconstructions_parent', table_name='reconstructions')
    op.drop_table('reconstructions')
