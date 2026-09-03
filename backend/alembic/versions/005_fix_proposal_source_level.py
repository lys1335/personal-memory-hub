"""Fix proposals.source_level type: DateTime -> Integer (P0-2 / Fix①).

Step 2 Phase 1 — proposal_model.py declares source_level as Integer and the
service/repository write integers (1, 2, 3, ...), but the initial migration
(001_initial.py) created the column as DateTime. That mismatch made every
proposal insert fail (or store garbage). This migration converts the column
to Integer, leaving the 001 baseline untouched so roll-forward/forward is
consistent.

Safety: due to the original bug, the source_level column has never held
valid data — every existing row is expected to be NULL. To guarantee the
type change succeeds on PostgreSQL regardless of stray data, we force the
conversion with ``postgresql_using='NULL::integer'`` (clears any non-castable
values to NULL rather than raising). The column is nullable, so this is safe.

Reversible: downgrade converts back to DateTime, again clearing values to
NULL via ``postgresql_using='NULL::timestamp'``.
"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision = '005_fix_proposal_source_level'
down_revision = '004_add_topics'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        'proposals',
        'source_level',
        type_=sa.Integer(),
        existing_type=sa.DateTime(),
        existing_nullable=True,
        postgresql_using='NULL::integer',
    )


def downgrade() -> None:
    op.alter_column(
        'proposals',
        'source_level',
        type_=sa.DateTime(),
        existing_type=sa.Integer(),
        existing_nullable=True,
        postgresql_using='NULL::timestamp',
    )
