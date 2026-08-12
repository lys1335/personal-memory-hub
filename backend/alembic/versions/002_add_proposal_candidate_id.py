"""add candidate_id to proposals

Revision ID: 002_add_proposal_candidate_id
Revises: 001_initial
Create Date: 2026-08-12

P0 Fix: Add candidate_id FK to proposals table for proper lineage tracking.
- candidate_id is nullable to accommodate historical Approved Proposals
- Partial unique index prevents duplicate pending proposals per candidate
- FK uses ON DELETE SET NULL to preserve proposal history
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_proposal_candidate_id'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add candidate_id column (UUID type to match candidates.id)
    op.add_column('proposals', sa.Column('candidate_id', sa.UUID(), nullable=True))

    # Add FK constraint with ON DELETE SET NULL
    op.create_foreign_key(
        'fk_proposals_candidate',
        'proposals',
        'candidates',
        ['candidate_id'],
        ['id'],
        ondelete='SET NULL'
    )

    # Add index for candidate_id lookups
    op.create_index('idx_proposals_candidate_id', 'proposals', ['candidate_id'])

    # Add partial unique index for pending proposals
    # This ensures at most one pending proposal per candidate
    op.create_index(
        'uk_proposals_pending_per_candidate',
        'proposals',
        ['workspace_id', 'candidate_id'],
        unique=True,
        postgresql_where=sa.text("status = 'pending'")
    )


def downgrade() -> None:
    # Remove partial unique index
    op.drop_index('uk_proposals_pending_per_candidate', table_name='proposals')

    # Remove regular index
    op.drop_index('idx_proposals_candidate_id', table_name='proposals')

    # Remove FK constraint
    op.drop_constraint('fk_proposals_candidate', 'proposals', type_='foreignkey')

    # Remove column
    op.drop_column('proposals', 'candidate_id')
