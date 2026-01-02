# coding=utf-8
"""
用户相关数据模型
"""

from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from trendradar.models.base import Base


class UserTier(str, enum.Enum):
    """用户等级"""
    FREE = "free"
    PREMIUM = "premium"


class User(Base):
    """用户表"""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    avatar_url = Column(String(500))
    provider = Column(String(20), nullable=False)  # 'github' or 'google' or 'email'
    provider_id = Column(String(255), nullable=False)

    # 密码哈希（邮箱登录用户使用）
    password_hash = Column(String(255), nullable=True)

    # 超级管理员标识
    is_superuser = Column(Boolean, default=False, nullable=False)

    # 邮箱验证状态
    email_verified = Column(Boolean, default=False, nullable=False)

    # 用户等级和配额
    tier = Column(String(20), default=UserTier.FREE.value, nullable=False)
    daily_push_limit = Column(Integer, default=10, nullable=False)
    keyword_limit = Column(Integer, default=50, nullable=False)

    # 账户状态
    is_active = Column(Boolean, default=True, nullable=False)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    config = relationship("UserConfig", back_populates="user", uselist=False, cascade="all, delete-orphan")
    keywords = relationship("Keyword", back_populates="user", cascade="all, delete-orphan")
    channels = relationship("NotificationChannel", back_populates="user", cascade="all, delete-orphan")
    push_history = relationship("PushHistory", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, tier={self.tier})>"


class UserConfig(Base):
    """用户配置表"""

    __tablename__ = "user_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # 报告模式
    report_mode = Column(String(20), default="daily", nullable=False)  # 'daily', 'current', 'incremental'

    # 时区
    timezone = Column(String(50), default="Asia/Shanghai", nullable=False)

    # 推送时间窗口
    push_window_enabled = Column(Boolean, default=False, nullable=False)
    push_window_start = Column(String(5))  # HH:MM
    push_window_end = Column(String(5))    # HH:MM

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    user = relationship("User", back_populates="config")

    def __repr__(self):
        return f"<UserConfig(user_id={self.user_id}, mode={self.report_mode})>"
