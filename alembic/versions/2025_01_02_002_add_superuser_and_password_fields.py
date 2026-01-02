"""Add superuser and password fields

Revision ID: 002
Revises: 001
Create Date: 2025-01-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import bcrypt as _bcrypt

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加新字段到 users 表
    op.add_column('users', sa.Column('password_hash', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'))

    # 创建超级管理员账号
    # 账号: lengmodkx@gmail.com
    # 密码: lemon2judy
    password_bytes = "lemon2judy".encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    superadmin_password = _bcrypt.hashpw(password_bytes, _bcrypt.gensalt()).decode('utf-8')

    op.execute(
        f"""
        INSERT INTO users (email, name, provider, provider_id, password_hash, is_superuser, email_verified, tier, daily_push_limit, keyword_limit, is_active)
        VALUES (
            'lengmodkx@gmail.com',
            'Super Admin',
            'email',
            'lengmodkx@gmail.com',
            '{superadmin_password}',
            true,
            true,
            'premium',
            9999,
            9999,
            true
        )
        ON CONFLICT (email) DO NOTHING;
        """
    )


def downgrade() -> None:
    # 删除超级管理员账号
    op.execute("DELETE FROM users WHERE email = 'lengmodkx@gmail.com'")

    # 删除新字段
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'is_superuser')
    op.drop_column('users', 'password_hash')
