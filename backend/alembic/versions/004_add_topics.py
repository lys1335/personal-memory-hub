"""Add topics and topic_links tables.

Phase 21.6 — Topic / topic_links schema.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision = '004_add_topics'
down_revision = '003_add_reconstructions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create topics table
    op.create_table(
        'topics',
        sa.Column('id', sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column('workspace_id', sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_topic_id', sa.dialects.postgresql.UUID(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='initial'),
        sa.Column('evidence_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reconstruction_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('metadata', postgresql.JSONB(), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_topic_id'], ['topics.id'], ondelete='SET NULL'),
        sa.CheckConstraint(
            "status IN ('initial', 'active', 'evolved', 'superseded', 'archived')",
            name='chk_topic_status'
        ),
        sa.UniqueConstraint('workspace_id', 'name', name='uk_topics_workspace_name'),
        sa.PrimaryKeyConstraint('id', name='topics_pkey'),
    )
    
    op.create_index('idx_topics_workspace_id', 'topics', ['workspace_id'])
    op.create_index('idx_topics_parent', 'topics', ['parent_topic_id'])
    
    # Create topic_links table
    op.create_table(
        'topic_links',
        sa.Column('topic_id', sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column('source_type', sa.String(20), nullable=False),
        sa.Column('source_id', sa.dialects.postgresql.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ondelete='CASCADE'),
        sa.CheckConstraint(
            "source_type IN ('reconstruction', 'candidate', 'entity')",
            name='chk_topic_links_source_type'
        ),
        sa.PrimaryKeyConstraint('topic_id', 'source_type', 'source_id', name='topic_links_pkey'),
    )
    
    op.create_index('idx_topic_links_source', 'topic_links', ['source_type', 'source_id'])


def downgrade() -> None:
    op.drop_table('topic_links')
    op.drop_table('topics')
