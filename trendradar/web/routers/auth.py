# coding=utf-8
"""
认证相关 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette.requests import Request
import uuid

from trendradar.models.base import get_db
from trendradar.models.user import User, UserConfig, UserTier
from trendradar.web.auth.config import oauth
from trendradar.web.auth.utils import create_access_token
from trendradar.web.auth.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/login/{provider}")
async def login(provider: str, request: Request):
    """
    OAuth 登录入口

    Args:
        provider: OAuth 提供商 ('github' or 'google')
        request: FastAPI Request 对象

    Returns:
        重定向到 OAuth 授权页面
    """
    if provider not in ["github", "google"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的 OAuth 提供商: {provider}"
        )

    # 重定向到 OAuth 授权页面
    client = oauth.create_client(provider)
    return await client.authorize_redirect(request, redirect_uri=f"http://localhost:8000/auth/callback/{provider}")


@router.get("/callback/{provider}")
async def callback(
    provider: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    OAuth 回调处理

    Args:
        provider: OAuth 提供商
        request: FastAPI Request 对象
        db: 数据库会话

    Returns:
        设置 Cookie 并重定向到首页
    """
    if provider not in ["github", "google"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的 OAuth 提供商: {provider}"
        )

    # 获取 OAuth token
    client = oauth.create_client(provider)
    try:
        token = await client.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth 授权失败: {str(e)}"
        )

    # 获取用户信息
    user_data = await client.parse_id_token(request, token)

    # 根据提供商提取用户信息
    if provider == "github":
        email = user_data.get("email")
        name = user_data.get("name")
        avatar_url = user_data.get("picture")
        provider_id = str(user_data.get("sub"))
    else:  # google
        email = user_data.get("email")
        name = user_data.get("name")
        avatar_url = user_data.get("picture")
        provider_id = user_data.get("sub")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法获取用户邮箱"
        )

    # 查找或创建用户
    user = db.query(User).filter(
        User.provider == provider,
        User.provider_id == provider_id
    ).first()

    if not user:
        # 检查邮箱是否已被其他账户使用
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"该邮箱已被 {existing_user.provider} 账户使用"
            )

        # 创建新用户
        user = User(
            email=email,
            name=name or email.split("@")[0],
            avatar_url=avatar_url,
            provider=provider,
            provider_id=provider_id,
            tier=UserTier.FREE.value
        )
        db.add(user)
        db.flush()

        # 创建默认用户配置
        user_config = UserConfig(
            user_id=user.id,
            report_mode="daily",
            timezone="Asia/Shanghai"
        )
        db.add(user_config)
        db.commit()
        db.refresh(user)
    else:
        # 更新用户信息
        user.name = name or user.name
        user.avatar_url = avatar_url or user.avatar_url
        db.commit()
        db.refresh(user)

    # 创建 JWT token
    access_token = create_access_token({
        "user_id": str(user.id),
        "email": user.email,
        "tier": user.tier
    })

    # 重定向到首页，设置 HttpOnly Cookie
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=7 * 24 * 60 * 60,  # 7 天
        secure=False,  # 生产环境设置为 True（需要 HTTPS）
        samesite="lax"
    )

    return response


@router.post("/logout")
async def logout(response: Response):
    """
    退出登录

    Returns:
        清除 Cookie 并返回成功消息
    """
    response = Response(content='{"message": "退出登录成功"}', media_type="application/json")
    response.delete_cookie("access_token")
    return response


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """
    获取当前用户信息

    Args:
        current_user: 当前登录用户

    Returns:
        用户信息
    """
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
        "avatar_url": current_user.avatar_url,
        "tier": current_user.tier,
        "daily_push_limit": current_user.daily_push_limit,
        "keyword_limit": current_user.keyword_limit,
        "created_at": current_user.created_at.isoformat()
    }
