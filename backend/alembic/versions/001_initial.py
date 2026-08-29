"""initial baseline schema (Step 1, 001_initial)

Revision ID: 001_initial
Revises:
Create Date: 2026-08-28

Baseline schema established BEFORE 002_add_proposal_candidate_id.
Creates the 15 memory-domain tables (memory_models.py) plus the
proposals table (proposal_model.py) WITHOUT candidate_id, which is
added later by 002_add_proposal_candidate_id. Each business table
carries a workspace_id -> workspace.id CASCADE FK for workspace
isolation, exactly mirroring the ORM models.

NOTE: This migration is hand-authored from Base.metadata (not via
autogenerate) to avoid create_table conflicts with 003/004.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create workspace table
    op.create_table(
        'workspace',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id')
    )

    # Create user_profiles table
    op.create_table(
        'user_profiles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('external_user_id', sa.String(length=255), nullable=True),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('avatar_url', sa.Text(), nullable=True),
        sa.Column('_meta', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('workspace_id', 'external_user_id', name='uk_user_profiles_external')
    )

    # Create areas table
    op.create_table(
        'areas',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('parent_area_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'name', name='uk_areas_workspace_name'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_area_id'], ['areas.id'], ondelete='SET NULL')
    )

    # Create entities table
    op.create_table(
        'entities',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('area_id', sa.UUID(), nullable=False),
        sa.Column('parent_entity_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('canonical_name', sa.String(length=255), nullable=False),
        sa.Column('aliases', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('_meta', postgresql.JSONB(), nullable=False),
        sa.Column('observation_count', sa.Integer(), nullable=False),
        sa.Column('belief_count', sa.Integer(), nullable=False),
        sa.Column('pattern_count', sa.Integer(), nullable=False),
        sa.Column('relationship_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user_profiles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['parent_entity_id'], ['entities.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('workspace_id', 'entity_type', 'canonical_name', name='uk_entities_type_name'),
        sa.CheckConstraint("entity_type IN (\'Project\', \'Person\', \'Organization\', \'Tool\', \'Technology\',\'Concept\', \'Event\', \'Location\', \'Object\', \'Agent\', \'Model\', \'Document\')", name='chk_entity_type'),
        sa.ForeignKeyConstraint(['area_id'], ['areas.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create evidences table
    op.create_table(
        'evidences',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=True),
        sa.Column('area_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('evidence_type', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('raw_content', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('importance', sa.Float(), nullable=False),
        sa.Column('signal_strength', sa.Float(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('_meta', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user_profiles.id'], ondelete='SET NULL'),
        sa.CheckConstraint("char_length(content) > 0", name='chk_evidence_not_empty'),
        sa.ForeignKeyConstraint(['area_id'], ['areas.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='SET NULL')
    )

    # Create memory_nodes table
    op.create_table(
        'memory_nodes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=True),
        sa.Column('parent_node_id', sa.UUID(), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('node_type', sa.String(length=50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('observation_type', sa.String(length=50), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('importance', sa.Float(), nullable=False),
        sa.Column('signal_strength', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('generated_by', sa.String(length=50), nullable=False),
        sa.Column('evidence_links', postgresql.JSONB(), nullable=False),
        sa.Column('contradict_evidence', postgresql.JSONB(), nullable=False),
        sa.Column('_meta', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user_profiles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['parent_node_id'], ['memory_nodes.id'], ondelete='SET NULL'),
        sa.CheckConstraint("source IN (\'user\', \'manual\', \'explicit_command\', \'archive_derived\', \'ai_reflect\', \'import\')", name='chk_memory_source'),
        sa.CheckConstraint("generated_by IN (\'user\', \'manual\', \'ai_reflect\', \'archive\', \'import\')", name='chk_memory_generated_by'),
        sa.CheckConstraint("importance >= 0.0 AND importance <= 1.0", name='chk_importance_range'),
        sa.CheckConstraint("status IN (\'active\', \'candidate\', \'deprecated\', \'superseded\', \'orphaned\')", name='chk_memory_status'),
        sa.CheckConstraint("level IN (1, 2, 3)", name='chk_level_valid'),
        sa.CheckConstraint("(level = 1 AND node_type = \'Observation\') OR (level = 2 AND node_type = \'Pattern\') OR (level = 3 AND node_type = \'Belief\')", name='chk_level_type_consistency'),
        sa.CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name='chk_confidence_range'),
        sa.CheckConstraint("signal_strength >= 0.0 AND signal_strength <= 1.0", name='chk_signal_strength_range'),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='SET NULL'),
        sa.CheckConstraint("(level = 1 AND observation_type IN (\'activity\', \'decision\', \'preference\', \'fact\', \'goal\', \'problem\', \'event\')) OR level != 1", name='chk_observation_type'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create memory_evidences table
    op.create_table(
        'memory_evidences',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('memory_node_id', sa.UUID(), nullable=False),
        sa.Column('evidence_id', sa.UUID(), nullable=False),
        sa.Column('relationship_type', sa.String(length=50), nullable=False),
        sa.Column('contribution_weight', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint("contribution_weight >= 0.0 AND contribution_weight <= 1.0", name='chk_weight_range'),
        sa.ForeignKeyConstraint(['memory_node_id'], ['memory_nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evidence_id'], ['evidences.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("relationship_type IN (\'supports\', \'derived_from\', \'contradicts\', \'attenuates\')", name='chk_relationship_type'),
        sa.UniqueConstraint('memory_node_id', 'evidence_id', name='uk_memory_evidences'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE')
    )

    # Create relationships table
    op.create_table(
        'relationships',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('source_id', sa.UUID(), nullable=False),
        sa.Column('target_id', sa.UUID(), nullable=False),
        sa.Column('relationship_type', sa.String(length=50), nullable=False),
        sa.Column('strength', sa.Float(), nullable=False),
        sa.Column('_meta', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['source_id'], ['entities.id'], ondelete='CASCADE'),
        sa.CheckConstraint("relationship_type IN (\'belongs_to\', \'part_of\', \'uses\', \'depends_on\', \'related_to\',\'affects\', \'derived_from\', \'owns\', \'created_by\', \'about\')", name='chk_relationship_type'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_id', 'target_id', 'relationship_type', name='uk_relationship_direction'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE'),
        sa.CheckConstraint("source_id != target_id", name='chk_no_self_relationship'),
        sa.CheckConstraint("strength >= 0.0 AND strength <= 1.0", name='chk_strength_range'),
        sa.ForeignKeyConstraint(['target_id'], ['entities.id'], ondelete='CASCADE')
    )

    # Create memory_relationships table
    op.create_table(
        'memory_relationships',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('source_node_id', sa.UUID(), nullable=False),
        sa.Column('target_node_id', sa.UUID(), nullable=False),
        sa.Column('relationship_type', sa.String(length=50), nullable=False),
        sa.Column('contribution_weight', sa.Float(), nullable=False),
        sa.Column('_meta', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint("relationship_type IN (\'supports\', \'derived_from\', \'contradicts\', \'attenuates\')", name='chk_memory_relationship_type'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE'),
        sa.CheckConstraint("source_node_id != target_node_id", name='chk_no_self_memory_rel'),
        sa.ForeignKeyConstraint(['target_node_id'], ['memory_nodes.id'], ondelete='CASCADE'),
        sa.CheckConstraint("contribution_weight >= 0.0 AND contribution_weight <= 1.0", name='chk_memory_rel_weight_range'),
        sa.UniqueConstraint('source_node_id', 'target_node_id', 'relationship_type', name='uk_memory_relationship_direction'),
        sa.ForeignKeyConstraint(['source_node_id'], ['memory_nodes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create archives table
    op.create_table(
        'archives',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('source_archive_id', sa.UUID(), nullable=False),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('archive_type', sa.String(length=20), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('source_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE'),
        sa.CheckConstraint("period_start <= period_end", name='chk_archive_period'),
        sa.CheckConstraint("archive_type IN (\'monthly\', \'yearly\')", name='chk_archive_type'),
        sa.ForeignKeyConstraint(['source_archive_id'], ['archives.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("source_count >= 0", name='chk_source_count_non_negative')
    )

    # Create tags table
    op.create_table(
        'tags',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('tag_type', sa.String(length=20), nullable=False),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.UniqueConstraint('workspace_id', 'name', name='uk_tags_workspace_name'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE'),
        sa.CheckConstraint("tag_type IN (\'system\', \'ai\', \'user\')", name='chk_tag_type')
    )

    # Create tag_links table
    op.create_table(
        'tag_links',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('tag_id', sa.UUID(), nullable=False),
        sa.Column('target_type', sa.String(length=20), nullable=False),
        sa.Column('target_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tag_id', 'target_type', 'target_id', name='uk_tag_links'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("target_type IN (\'entity\', \'memory_node\', \'archive\')", name='chk_target_type')
    )

    # Create candidates table
    op.create_table(
        'candidates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=False),
        sa.Column('area_id', sa.UUID(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('candidate_type', sa.String(length=20), nullable=False),
        sa.Column('evidence_source', sa.String(length=50), nullable=False),
        sa.Column('evidence_id', sa.UUID(), nullable=False),
        sa.Column('evidence_chain', postgresql.JSONB(), nullable=False),
        sa.Column('evidence_count', sa.Integer(), nullable=False),
        sa.Column('evidence_strength', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('ingested_by', sa.String(length=50), nullable=False),
        sa.Column('ingestion_timestamp', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('verified_at', sa.UUID(), nullable=False),
        sa.Column('verified_by', sa.String(length=50), nullable=True),
        sa.Column('modified_by', sa.String(length=50), nullable=True),
        sa.Column('modification_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint("evidence_count >= 1", name='chk_candidate_has_evidence'),
        sa.CheckConstraint("evidence_strength >= 0.0 AND evidence_strength <= 1.0", name='chk_candidate_evidence_strength'),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['area_id'], ['areas.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE'),
        sa.CheckConstraint("candidate_type IN (\'pattern\', \'belief\')", name='chk_candidate_type'),
        sa.CheckConstraint("jsonb_array_length(evidence_chain) > 0", name='chk_candidate_evidence_chain_not_empty')
    )

    # Create tasks table
    op.create_table(
        'tasks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=False),
        sa.Column('area_id', sa.UUID(), nullable=False),
        sa.Column('task_type', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('evidence_driven', sa.Boolean(), nullable=False),
        sa.Column('debounce_key', sa.String(length=255), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.Column('max_retries', sa.Integer(), nullable=False),
        sa.Column('payload', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('completed_at', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='SET NULL'),
        sa.CheckConstraint("task_type IN (\'INGESTION\', \'REFLECTION\', \'ACTIVATION\', \'ARCHIVE\')", name='chk_task_type'),
        sa.CheckConstraint("status IN (\'pending\', \'running\', \'completed\', \'failed\', \'dead_letter\')", name='chk_task_status'),
        sa.ForeignKeyConstraint(['area_id'], ['areas.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('workspace_id', 'task_type', 'debounce_key', name='uk_tasks_debounce'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create vector_documents table
    op.create_table(
        'vector_documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('source_id', sa.UUID(), nullable=False),
        sa.Column('area_id', sa.UUID(), nullable=True),
        sa.Column('entity_id', sa.UUID(), nullable=True),
        sa.Column('memory_level', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('importance_score', sa.Float(), nullable=False),
        sa.Column('embedding', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint("source_type IN (\'memory_node\', \'archive\', \'entity_summary\')", name='chk_vector_doc_source_type'),
        sa.CheckConstraint("importance_score >= 0.0 AND importance_score <= 1.0", name='chk_vector_doc_importance_score'),
        sa.ForeignKeyConstraint(['area_id'], ['areas.id'], ondelete='SET NULL'),
        sa.CheckConstraint("memory_level IN (1, 2, 3, 4)", name='chk_vector_doc_memory_level'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['entity_id'], ['entities.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE')
    )

    # Create proposals table
    op.create_table(
        'proposals',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('workspace_id', sa.String(), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('source_level', sa.DateTime(), nullable=True),
        sa.Column('target_level', sa.Integer(), nullable=False),
        sa.Column('entity', sa.String(length=255), nullable=True),
        sa.Column('evidence_chain', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Double(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )



def downgrade() -> None:
    op.drop_table('proposals')
    op.drop_table('vector_documents')
    op.drop_table('tasks')
    op.drop_table('candidates')
    op.drop_table('tag_links')
    op.drop_table('tags')
    op.drop_table('archives')
    op.drop_table('memory_relationships')
    op.drop_table('relationships')
    op.drop_table('memory_evidences')
    op.drop_table('memory_nodes')
    op.drop_table('evidences')
    op.drop_table('entities')
    op.drop_table('areas')
    op.drop_table('user_profiles')
    op.drop_table('workspace')
