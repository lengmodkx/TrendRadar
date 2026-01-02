"""Initial multiuser schema

Revision ID: 001
Revises:
Create Date: 2025-01-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建 users 表
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('avatar_url', sa.String(500)),
        sa.Column('provider', sa.String(20), nullable=False),
        sa.Column('provider_id', sa.String(255), nullable=False),
        sa.Column('tier', sa.String(20), nullable=False, server_default='free'),
        sa.Column('daily_push_limit', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('keyword_limit', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_provider', 'users', ['provider', 'provider_id'])

    # 创建 user_configs 表
    op.create_table(
        'user_configs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('report_mode', sa.String(20), nullable=False, server_default='daily'),
        sa.Column('timezone', sa.String(50), nullable=False, server_default='Asia/Shanghai'),
        sa.Column('push_window_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('push_window_start', sa.String(5)),
        sa.Column('push_window_end', sa.String(5)),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_user_configs_user_id', 'user_configs', ['user_id'], unique=True)

    # 创建 keywords 表
    op.create_table(
        'keywords',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.String(500), nullable=False),
        sa.Column('group_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_filtered', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('max_count', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_keywords_user_id', 'keywords', ['user_id'])
    op.create_index('ix_keywords_group_order', 'keywords', ['user_id', 'group_order'])

    # 创建 notification_channels 表
    op.create_table(
        'notification_channels',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('channel_type', sa.String(20), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_notification_channels_user_id', 'notification_channels', ['user_id'])

    # 创建 push_history 表
    op.create_table(
        'push_history',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('channel_type', sa.String(50), nullable=False),
        sa.Column('content_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('error_message', sa.Text()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_push_history_user_id_created', 'push_history', ['user_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_push_history_user_id_created', table_name='push_history')
    op.drop_table('push_history')

    op.drop_index('ix_notification_channels_user_id', table_name='notification_channels')
    op.drop_table('notification_channels')

    op.drop_index('ix_keywords_group_order', table_name='keywords')
    op.drop_index('ix_keywords_user_id', table_name='keywords')
    op.drop_table('keywords')

    op.drop_index('ix_user_configs_user_id', table_name='user_configs')
    op.drop_table('user_configs')

    op.drop_index('ix_users_provider', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
