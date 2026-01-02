# coding=utf-8
"""
推送渠道和历史记录模型
"""

from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from trendradar.models.base import Base


class NotificationChannel(Base):
    """推送渠道表"""

    __tablename__ = "notification_channels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 渠道类型和配置
    channel_type = Column(String(20), nullable=False)  # 'feishu', 'telegram', 'dingtalk', 'email', 'ntfy', 'bark', 'slack'
    config = Column(JSON, nullable=False)  # 存储不同渠道的配置，如 {"webhook_url": "xxx", "token": "xxx"}

    # 状态
    enabled = Column(Boolean, default=True, nullable=False)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    user = relationship("User", back_populates="channels")

    def __repr__(self):
        return f"<NotificationChannel(id={self.id}, type={self.channel_type}, enabled={self.enabled})>"


class PushHistory(Base):
    """推送历史表"""

    __tablename__ = "push_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 推送信息
    channel_type = Column(String(50), nullable=False)
    content_count = Column(Integer, default=0, nullable=False)

    # 状态
    status = Column(String(20), nullable=False)  # 'success' or 'failed'
    error_message = Column(Text)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # 关系
    user = relationship("User", back_populates="push_history")

    def __repr__(self):
        return f"<PushHistory(id={self.id}, user_id={self.user_id}, status={self.status})>"
