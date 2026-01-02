# coding=utf-8
"""
数据库初始化脚本

用于连接到云数据库并创建所有表

使用方法:
    1. 设置环境变量 DATABASE_URL
    2. 运行: python scripts/init_database.py

示例:
    export DATABASE_URL="postgresql://user:pass@host:5432/trendradar"
    python scripts/init_database.py
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text
from trendradar.models.base import Base


def init_database():
    """初始化数据库表"""

    # 从环境变量获取数据库 URL
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ 错误: 未设置 DATABASE_URL 环境变量")
        print("\n请先设置数据库连接字符串：")
        print("\n示例:")
        print("  export DATABASE_URL='postgresql://username:password@host:5432/trendradar'")
        print("\n或者创建 .env 文件：")
        print("  DATABASE_URL=postgresql://username:password@host:5432/trendradar")
        sys.exit(1)

    print(f"📡 连接到数据库...")
    print(f"   {database_url[:50]}...")

    try:
        # 创建数据库引擎
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            echo=True  # 显示 SQL 日志，方便调试
        )

        # 测试连接
        print("\n🔍 测试数据库连接...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ 数据库连接成功!")
            print(f"   PostgreSQL 版本: {version.split(',')[0]}")

        # 创建所有表
        print("\n📊 创建数据库表...")
        Base.metadata.create_all(bind=engine)

        # 显示创建的表
        print("\n✅ 数据库表创建成功！")
        print("\n已创建的表:")
        for table_name in Base.metadata.tables.keys():
            print(f"  ✓ {table_name}")

        print(f"\n总计: {len(Base.metadata.tables)} 个表")

        print("\n💡 提示:")
        print("  - 可以使用 Alembic 管理数据库迁移")
        print("  - 运行 'alembic upgrade head' 应用迁移")
        print("  - 运行 'alembic revision --autogenerate -m \"描述\"' 创建新迁移")

    except Exception as e:
        print(f"\n❌ 数据库初始化失败: {e}")
        print("\n可能的原因:")
        print("  1. 数据库连接字符串不正确")
        print("  2. 数据库服务器不可达")
        print("  3. 用户名或密码错误")
        print("  4. 数据库不存在")
        print("\n请检查 DATABASE_URL 配置并重试")
        sys.exit(1)


def check_database_exists():
    """检查数据库是否存在"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return False

    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except:
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("TrendRadar 多用户系统 - 数据库初始化")
    print("=" * 60)

    # 检查环境变量
    if not check_database_exists():
        print("\n⚠️  警告: 无法连接到数据库")
        print("\n请确保:")
        print("  1. 已设置 DATABASE_URL 环境变量")
        print("  2. 数据库服务器正在运行")
        print("  3. 数据库已创建")
        print("\n继续尝试连接...\n")

    # 初始化数据库
    init_database()

    print("\n" + "=" * 60)
    print("✅ 数据库初始化完成!")
    print("=" * 60)
