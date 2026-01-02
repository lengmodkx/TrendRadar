# coding=utf-8
"""
更新超级管理员邮箱脚本
用法: python scripts/update_superadmin_email.py
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from passlib.context import CryptContext

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 从环境变量获取数据库 URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:lemon2judy@103.36.221.226:5432/TrendRadar")

def update_superadmin():
    """更新超级管理员账号"""

    # 创建数据库连接
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # 删除旧的管理员账号
        conn.execute(text("DELETE FROM users WHERE email = 'superadmin@trendradar.local'"))
        conn.execute(text("DELETE FROM user_configs WHERE user_id NOT IN (SELECT id FROM users)"))

        # 检查新管理员是否已存在
        result = conn.execute(text("SELECT id FROM users WHERE email = 'lengmodkx@gmail.com'"))
        if result.fetchone():
            print("管理员账号 lengmodkx@gmail.com 已存在，跳过创建")
            return

        # 创建新的管理员账号
        password_hash = pwd_context.hash("lemon2judy")

        conn.execute(text("""
            INSERT INTO users (email, name, provider, provider_id, password_hash, is_superuser, email_verified, tier, daily_push_limit, keyword_limit, is_active)
            VALUES (
                'lengmodkx@gmail.com',
                'Super Admin',
                'email',
                'lengmodkx@gmail.com',
                :password_hash,
                true,
                true,
                'premium',
                9999,
                9999,
                true
            )
        """), {"password_hash": password_hash})

        # 为管理员创建默认配置
        conn.execute(text("""
            INSERT INTO user_configs (user_id, report_mode, timezone)
            SELECT id, 'daily', 'Asia/Shanghai'
            FROM users
            WHERE email = 'lengmodkx@gmail.com'
        """))

        conn.commit()

        print("✅ 超级管理员账号创建成功！")
        print("   邮箱: lengmodkx@gmail.com")
        print("   密码: lemon2judy")

if __name__ == "__main__":
    try:
        update_superadmin()
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)
