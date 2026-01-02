# coding=utf-8
"""
认证相关 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from starlette.requests import Request
from pydantic import BaseModel, EmailStr, Field
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


# 请求模型
class RegisterRequest(BaseModel):
    """注册请求"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str = Field(..., min_length=8, max_length=100)
    name: str = Field(..., min_length=2, max_length=100)


class LoginRequest(BaseModel):
    """登录请求"""
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=100)


@router.post("/register")
async def register(
    request_data: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    邮箱注册
    """
    # 验证密码一致性
    if request_data.password != request_data.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="两次输入的密码不一致"
        )

    # 检查邮箱是否已存在
    existing_user = db.query(User).filter(User.email == request_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册"
        )

    # 哈希密码（在函数内部导入 bcrypt）
    import bcrypt
    password_bytes = request_data.password.encode('utf-8')[:72]
    password_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')

    # 创建新用户
    user = User(
        email=request_data.email,
        name=request_data.name,
        provider="email",
        provider_id=request_data.email,
        password_hash=password_hash,
        tier=UserTier.FREE.value,
        email_verified=False
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

    # 创建 JWT token
    access_token = create_access_token({
        "user_id": str(user.id),
        "email": user.email,
        "tier": user.tier
    })

    # 返回 JSON 响应并设置 HttpOnly Cookie
    response = JSONResponse(
        content={
            "message": "注册成功",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "tier": user.tier
            }
        },
        status_code=status.HTTP_201_CREATED
    )
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=7 * 24 * 60 * 60,
        secure=False,
        samesite="lax"
    )

    return response


@router.post("/login")
async def login(
    request_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    邮箱登录
    """
    # 查找用户
    user = db.query(User).filter(
        User.email == request_data.email,
        User.provider == "email"
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )

    # 验证密码（在函数内部导入 bcrypt）
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="该账户不支持密码登录，请使用 OAuth 登录"
        )

    import bcrypt
    password_bytes = request_data.password.encode('utf-8')[:72]
    hashed_bytes = user.password_hash.encode('utf-8')

    if not bcrypt.checkpw(password_bytes, hashed_bytes):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )

    # 检查账户状态
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该账户已被禁用"
        )

    # 创建 JWT token
    access_token = create_access_token({
        "user_id": str(user.id),
        "email": user.email,
        "tier": user.tier
    })

    # 返回 JSON 响应并设置 HttpOnly Cookie
    response = JSONResponse(
        content={
            "message": "登录成功",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "tier": user.tier,
                "is_superuser": user.is_superuser
            }
        }
    )
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=7 * 24 * 60 * 60,
        secure=False,
        samesite="lax"
    )

    return response


@router.api_route("/logout", methods=["GET", "POST"])
async def logout(request: Request, response: Response):
    """
    退出登录

    支持 GET 和 POST 方法

    - GET: 重定向到登录页面
    - POST: 返回 JSON 响应（用于 AJAX 调用）

    Returns:
        GET: 重定向到登录页面
        POST: JSON 响应
    """
    from fastapi.responses import RedirectResponse

    # 清除 Cookie
    if request.method == "POST":
        # POST 请求：返回 JSON 响应
        response_obj = Response(content='{"message": "退出登录成功"}', media_type="application/json")
        response_obj.delete_cookie("access_token")
        return response_obj
    else:
        # GET 请求：重定向到登录页面
        redirect_resp = RedirectResponse(url="/", status_code=302)
        redirect_resp.delete_cookie("access_token")
        return redirect_resp


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
