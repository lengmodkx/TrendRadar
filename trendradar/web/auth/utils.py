# coding=utf-8
"""
JWT 认证工具
"""

from datetime import datetime, timedelta
from typing import Dict
from jose import JWTError, jwt
from fastapi import HTTPException, status
import os
import sys

# JWT 配置
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-this-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 7


def create_access_token(data: Dict) -> str:
    """
    创建 JWT access token

    Args:
        data: 要编码的数据（通常包含 user_id, email, tier）

    Returns:
        JWT token 字符串
    """
    to_encode = data.copy()

    # 设置过期时间
    expire = datetime.utcnow() + timedelta(days=JWT_EXPIRATION_DAYS)
    to_encode.update({"exp": expire})

    # 编码 token
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Dict:
    """
    解码 JWT access token

    Args:
        token: JWT token 字符串

    Returns:
        解码后的 payload

    Raises:
        HTTPException: token 无效或过期
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码

    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码

    Returns:
        密码是否匹配
    """
    # Import bcrypt inside function to avoid module reload issues
    import bcrypt

    # bcrypt 有 72 字节限制，需要截断
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]

    # hashed_password 是字符串，需要转换为 bytes
    if isinstance(hashed_password, str):
        hashed_bytes = hashed_password.encode('utf-8')
    else:
        hashed_bytes = hashed_password

    return bcrypt.checkpw(password_bytes, hashed_bytes)


def get_password_hash(password: str) -> str:
    """
    获取密码哈希

    Args:
        password: 明文密码

    Returns:
        哈希后的密码
    """
    # Import bcrypt inside function to avoid module reload issues
    import bcrypt

    # bcrypt 有 72 字节限制，需要截断
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]

    # 生成哈希并返回字符串
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode('utf-8')
