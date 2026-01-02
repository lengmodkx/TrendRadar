# coding=utf-8
"""
配额检查器
"""

from datetime import datetime
from typing import Tuple
from uuid import UUID
from sqlalchemy.orm import Session

from trendradar.models.base import Base
from trendradar.models.user import User
from trendradar.models.channel import PushHistory


class QuotaChecker:
    """配额检查器"""

    def __init__(self, db: Session):
        """
        初始化配额检查器

        Args:
            db: 数据库会话
        """
        self.db = db

    def can_push(self, user_id: UUID) -> Tuple[bool, str]:
        """
        检查用户是否可以推送

        Args:
            user_id: 用户 ID

        Returns:
            (是否可以推送, 原因说明)
        """
        # 获取用户信息
        user = self.db.query(User).filter(User.id == user_id).first()

        if not user:
            return False, "用户不存在"

        if not user.is_active:
            return False, "账户已被禁用"

        # 付费用户无限制
        if user.tier == "premium":
            return True, ""

        # 免费用户检查每日推送限制
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        push_count = self.db.query(PushHistory).filter(
            PushHistory.user_id == user_id,
            PushHistory.created_at >= today_start,
            PushHistory.status == "success"
        ).count()

        if push_count >= user.daily_push_limit:
            return False, f"今日推送配额已用完 ({push_count}/{user.daily_push_limit})"

        return True, ""

    def record_push(self, user_id: UUID, channel_type: str, content_count: int, success: bool = True, error_message: str = ""):
        """
        记录推送历史

        Args:
            user_id: 用户 ID
            channel_type: 渠道类型
            content_count: 推送内容数量
            success: 是否成功
            error_message: 错误信息
        """
        history = PushHistory(
            user_id=user_id,
            channel_type=channel_type,
            content_count=content_count,
            status="success" if success else "failed",
            error_message=error_message
        )
        self.db.add(history)
        self.db.commit()

    def get_today_push_count(self, user_id: UUID) -> int:
        """
        获取用户今天的推送次数

        Args:
            user_id: 用户 ID

        Returns:
            今天推送成功的次数
        """
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        return self.db.query(PushHistory).filter(
            PushHistory.user_id == user_id,
            PushHistory.created_at >= today_start,
            PushHistory.status == "success"
        ).count()
