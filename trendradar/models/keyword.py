# coding=utf-8
"""
关键词数据模型
"""

from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from trendradar.models.base import Base


class Keyword(Base):
    """用户关键词表"""

    __tablename__ = "keywords"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 关键词内容
    content = Column(String(500), nullable=False)

    # 分组和排序
    group_order = Column(Integer, default=0, nullable=False)

    # 关键词类型
    is_required = Column(Boolean, default=False, nullable=False)  # 必须词（+）
    is_filtered = Column(Boolean, default=False, nullable=False)  # 过滤词（!）
    max_count = Column(Integer, default=0)  # 数量限制（@N），0 表示不限制

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 关系
    user = relationship("User", back_populates="keywords")

    def __repr__(self):
        return f"<Keyword(id={self.id}, content={self.content[:20]}, user_id={self.user_id})>"
