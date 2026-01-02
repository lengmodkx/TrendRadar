# coding=utf-8
"""
管理员 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import uuid

from trendradar.models.base import get_db
from trendradar.models.user import User
from trendradar.web.auth.dependencies import get_current_admin


# 请求模型
class UpdateUserStatusRequest(BaseModel):
    """更新用户状态请求"""
    is_active: bool


class UpdateUserTierRequest(BaseModel):
    """更新用户等级请求"""
    tier: str  # 'free' or 'premium'


# 响应模型
class UserListItem(BaseModel):
    """用户列表项"""
    id: str
    email: str
    name: str
    provider: str
    tier: str
    is_active: bool
    is_superuser: bool
    created_at: str

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """用户列表响应"""
    total: int
    page: int
    page_size: int
    users: List[UserListItem]


class SystemStatsResponse(BaseModel):
    """系统统计响应"""
    total_users: int
    active_users: int
    free_users: int
    premium_users: int
    superusers: int
    today_new_users: int
    today_push_count: int
    weekly_active_users: int


router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=UserListResponse)
async def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    tier: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    获取用户列表（分页）

    Args:
        page: 页码
        page_size: 每页数量
        search: 搜索关键词（邮箱或姓名）
        tier: 用户等级筛选
        is_active: 账户状态筛选
        current_admin: 当前管理员
        db: 数据库会话

    Returns:
        分页用户列表
    """
    # 构建查询
    query = db.query(User)

    # 搜索过滤
    if search:
        query = query.filter(
            (User.email.ilike(f"%{search}%")) |
            (User.name.ilike(f"%{search}%"))
        )

    # 等级过滤
    if tier:
        query = query.filter(User.tier == tier)

    # 状态过滤
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    # 计算总数
    total = query.count()

    # 分页
    offset = (page - 1) * page_size
    users = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()

    # 转换为响应模型
    user_items = [
        UserListItem(
            id=str(user.id),
            email=user.email,
            name=user.name,
            provider=user.provider,
            tier=user.tier,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at.isoformat()
        )
        for user in users
    ]

    return UserListResponse(
        total=total,
        page=page,
        page_size=page_size,
        users=user_items
    )


@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    request_data: UpdateUserStatusRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    更新用户状态（启用/禁用）

    Args:
        user_id: 用户 ID
        request_data: 状态更新请求数据
        current_admin: 当前管理员
        db: 数据库会话

    Returns:
        更新结果
    """
    # 查找目标用户
    target_user = db.query(User).filter(User.id == user_id).first()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 不能修改其他管理员的状态
    if target_user.is_superuser and target_user.id != current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不能修改其他管理员的状态"
        )

    # 更新状态
    target_user.is_active = request_data.is_active
    db.commit()

    return {
        "message": "用户状态更新成功",
        "user_id": str(target_user.id),
        "is_active": target_user.is_active
    }


@router.put("/users/{user_id}/tier")
async def update_user_tier(
    user_id: str,
    request_data: UpdateUserTierRequest,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    更新用户等级

    Args:
        user_id: 用户 ID
        request_data: 等级更新请求数据
        current_admin: 当前管理员
        db: 数据库会话

    Returns:
        更新结果
    """
    # 验证 tier 值
    if request_data.tier not in ["free", "premium"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的用户等级，必须是 'free' 或 'premium'"
        )

    # 查找目标用户
    target_user = db.query(User).filter(User.id == user_id).first()

    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    # 不能修改其他管理员的等级
    if target_user.is_superuser and target_user.id != current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不能修改其他管理员的等级"
        )

    # 更新等级和配额
    target_user.tier = request_data.tier
    if request_data.tier == "premium":
        target_user.daily_push_limit = 100
        target_user.keyword_limit = 500
    else:
        target_user.daily_push_limit = 10
        target_user.keyword_limit = 50

    db.commit()

    return {
        "message": "用户等级更新成功",
        "user_id": str(target_user.id),
        "tier": target_user.tier,
        "daily_push_limit": target_user.daily_push_limit,
        "keyword_limit": target_user.keyword_limit
    }


@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    获取系统统计信息

    Args:
        current_admin: 当前管理员
        db: 数据库会话

    Returns:
        系统统计数据
    """
    # 总用户数
    total_users = db.query(User).count()

    # 活跃用户数
    active_users = db.query(User).filter(User.is_active == True).count()

    # Free 用户数
    free_users = db.query(User).filter(User.tier == "free").count()

    # Premium 用户数
    premium_users = db.query(User).filter(User.tier == "premium").count()

    # 超级管理员数
    superusers = db.query(User).filter(User.is_superuser == True).count()

    # 今日新增用户
    today = datetime.now().date()
    today_new_users = db.query(User).filter(
        User.created_at >= today
    ).count()

    # 7天活跃用户（有登录记录的用户，这里简化处理）
    week_ago = datetime.now() - timedelta(days=7)
    weekly_active_users = db.query(User).filter(
        User.created_at >= week_ago
    ).count()

    # 今日推送数量（从 push_history 表统计）
    from trendradar.models.user import PushHistory
    today_push_count = db.query(PushHistory).filter(
        PushHistory.created_at >= today
    ).count()

    return SystemStatsResponse(
        total_users=total_users,
        active_users=active_users,
        free_users=free_users,
        premium_users=premium_users,
        superusers=superusers,
        today_new_users=today_new_users,
        today_push_count=today_push_count,
        weekly_active_users=weekly_active_users
    )
