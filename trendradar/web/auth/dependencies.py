# coding=utf-8
"""
认证依赖和中间件
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from starlette.requests import Request

from trendradar.models.base import get_db
from trendradar.models.user import User
from trendradar.web.auth.utils import decode_access_token


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """
    获取当前登录用户（依赖注入）

    Args:
        request: FastAPI Request 对象
        db: 数据库会话

    Returns:
        当前用户对象

    Raises:
        HTTPException: 未登录或 token 无效
    """
    # 从 Cookie 获取 token
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录，请先登录"
        )

    # 解码 token
    payload = decode_access_token(token)
    user_id = payload.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 token"
        )

    # 查询用户
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账户已被禁用"
        )

    return user


async def get_optional_user(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    获取当前用户（可选）

    如果用户未登录，返回 None 而不是抛出异常

    Args:
        request: FastAPI Request 对象
        db: 数据库会话

    Returns:
        用户对象或 None
    """
    token = request.cookies.get("access_token")

    if not token:
        return None

    try:
        payload = decode_access_token(token)
        user_id = payload.get("user_id")

        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            return user
    except Exception:
        pass

    return None
