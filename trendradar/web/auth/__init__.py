# coding=utf-8
"""
认证模块
"""

from trendradar.web.auth.config import oauth
from trendradar.web.auth.utils import create_access_token, decode_access_token

__all__ = ["oauth", "create_access_token", "decode_access_token"]
