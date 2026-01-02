# coding=utf-8
"""
数据库基类和会话管理
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import os

# 从环境变量获取数据库 URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://trendradar:trendradar@localhost/trendradar"
)

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # 检查连接有效性
    pool_size=5,         # 连接池大小
    max_overflow=10,     # 最大溢出连接数
    echo=False           # 生产环境关闭 SQL 日志
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话（依赖注入）

    用法:
        @app.get("/users")
        def read_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
