# coding=utf-8
"""
从数据库读取用户配置
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from trendradar.models.base import Base
from trendradar.models.user import User, UserConfig
from trendradar.models.keyword import Keyword
from trendradar.models.channel import NotificationChannel


class DatabaseConfigReader:
    """从数据库读取用户配置的类"""

    def __init__(self, db: Session):
        """
        初始化配置读取器

        Args:
            db: 数据库会话
        """
        self.db = db

    def get_all_active_users(self) -> List[User]:
        """
        获取所有激活的用户

        Returns:
            用户列表
        """
        return self.db.query(User).filter(User.is_active == True).all()

    def get_user_config(self, user_id: UUID) -> Optional[UserConfig]:
        """
        获取用户配置

        Args:
            user_id: 用户 ID

        Returns:
            用户配置对象或 None
        """
        return self.db.query(UserConfig).filter(UserConfig.user_id == user_id).first()

    def get_user_keywords(self, user_id: UUID) -> List[Keyword]:
        """
        获取用户的关键词

        Args:
            user_id: 用户 ID

        Returns:
            关键词列表（按 group_order 排序）
        """
        return self.db.query(Keyword).filter(
            Keyword.user_id == user_id
        ).order_by(Keyword.group_order, Keyword.created_at).all()

    def get_user_channels(self, user_id: UUID, enabled_only: bool = True) -> List[NotificationChannel]:
        """
        获取用户的推送渠道

        Args:
            user_id: 用户 ID
            enabled_only: 是否只返回启用的渠道

        Returns:
            推送渠道列表
        """
        query = self.db.query(NotificationChannel).filter(NotificationChannel.user_id == user_id)

        if enabled_only:
            query = query.filter(NotificationChannel.enabled == True)

        return query.all()

    def get_user_filter_words(self, user_id: UUID) -> List[str]:
        """
        获取用户的过滤词

        Args:
            user_id: 用户 ID

        Returns:
            过滤词列表
        """
        keywords = self.db.query(Keyword).filter(
            Keyword.user_id == user_id,
            Keyword.is_filtered == True
        ).all()

        return [k.content for k in keywords]
