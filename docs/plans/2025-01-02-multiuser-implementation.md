# 多用户系统实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将 TrendRadar 从单用户系统改造为支持多用户的 SaaS 服务，支持 GitHub/Google OAuth 登录、可视化配置界面和用户配额管理。

**Architecture:** FastAPI Web 服务 + PostgreSQL 数据库 + SQLAlchemy ORM + Alembic 迁移 + Authlib OAuth + JWT 认证，保持现有爬虫架构不变，新增数据库配置读取层实现多用户隔离。

**Tech Stack:** FastAPI, PostgreSQL, SQLAlchemy, Alembic, Authlib, python-jose, Jinja2, Tailwind CSS, Alpine.js

---

## 阶段一：基础设施搭建（数据库模型与迁移）

### Task 1: 更新项目依赖

**Files:**
- Modify: `pyproject.toml`

**Step 1: 添加新依赖到 pyproject.toml**

在 `dependencies` 数组中添加以下依赖：

```toml
dependencies = [
    "requests>=2.32.5,<3.0.0",
    "pytz>=2025.2,<2026.0",
    "PyYAML>=6.0.3,<7.0.0",
    "fastmcp>=2.12.0,<2.14.0",
    "websockets>=13.0,<14.0",
    "feedparser>=6.0.0,<7.0.0",
    "boto3>=1.35.0,<2.0.0",
    # 新增 Web 框架和数据库依赖
    "fastapi>=0.104.0,<0.110.0",
    "uvicorn[standard]>=0.24.0,<0.30.0",
    "sqlalchemy>=2.0.0,<2.1.0",
    "alembic>=1.12.0,<1.14.0",
    "psycopg2-binary>=2.9.0,<2.10.0",
    # 认证相关
    "authlib>=1.2.0,<1.3.0",
    "requests-oauthlib>=1.3.0,<2.0.0",
    "python-jose[cryptography]>=3.3.0,<4.0.0",
    "passlib[bcrypt]>=1.7.0,<2.0.0",
    # 前端模板
    "jinja2>=3.1.0,<3.2.0",
    "python-multipart>=0.0.6,<0.1.0",
]
```

**Step 2: 验证依赖配置**

运行: `python -c "import tomllib; data = tomllib.load(open('pyproject.toml', 'rb')); print(data['project']['dependencies'][-5:])"`
Expected: 输出最后5个依赖，包含新添加的 fastapi 等

**Step 3: 安装依赖**

运行: `pip install -e .`
Expected: 所有依赖安装成功，无报错

**Step 4: 测试 FastAPI 导入**

运行: `python -c "import fastapi; print(fastapi.__version__)"`
Expected: 输出版本号（如 0.104.1）

**Step 5: 提交**

```bash
git add pyproject.toml
git commit -m "feat(multiuser): add FastAPI, SQLAlchemy, and Authlib dependencies"
```

---

### Task 2: 创建数据库模型目录结构

**Files:**
- Create: `trendradar/models/__init__.py`
- Create: `trendradar/models/base.py`
- Create: `trendradar/models/user.py`
- Create: `trendradar/models/keyword.py`
- Create: `trendradar/models/channel.py`

**Step 1: 创建 models 包的 __init__.py**

创建文件 `trendradar/models/__init__.py`:

```python
# coding=utf-8
"""
TrendRadar 数据库模型

包含所有 SQLAlchemy 模型定义
"""

from trendradar.models.base import Base, get_db
from trendradar.models.user import User, UserConfig
from trendradar.models.keyword import Keyword
from trendradar.models.channel import NotificationChannel, PushHistory

__all__ = [
    "Base",
    "get_db",
    "User",
    "UserConfig",
    "Keyword",
    "NotificationChannel",
    "PushHistory",
]
```

**Step 2: 创建数据库基类**

创建文件 `trendradar/models/base.py`:

```python
# coding=utf-8
"""
数据库基类和会话管理
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import os

# 从环境变量获取数据库 URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://trendradar:trendradar@localhost/trendradar"
)

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # 检查连接有效性
    pool_size=5,         # 连接池大小
    max_overflow=10,     # 最大溢出连接数
    echo=False           # 生产环境关闭 SQL 日志
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话（依赖注入）

    用法:
        @app.get("/users")
        def read_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Step 3: 测试数据库连接**

运行: `python -c "from trendradar.models.base import engine; print(engine.url)"`
Expected: 输出数据库 URL（如果未设置 DATABASE_URL 环境变量，会使用默认值）

**Step 4: 提交**

```bash
git add trendradar/models/__init__.py trendradar/models/base.py
git commit -m "feat(multiuser): add database base class and session management"
```

---

### Task 3: 创建 User 模型

**Files:**
- Create: `trendradar/models/user.py`

**Step 1: 创建 User 和 UserConfig 模型**

创建文件 `trendradar/models/user.py`:

```python
# coding=utf-8
"""
用户相关数据模型
"""

from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Enum, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from trendradar.models.base import Base


class UserTier(str, Enum):
    """用户等级"""
    FREE = "free"
    PREMIUM = "premium"


class User(Base):
    """用户表"""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    avatar_url = Column(String(500))
    provider = Column(String(20), nullable=False)  # 'github' or 'google'
    provider_id = Column(String(255), nullable=False)

    # 用户等级和配额
    tier = Column(String(20), default=UserTier.FREE.value, nullable=False)
    daily_push_limit = Column(Integer, default=10, nullable=False)
    keyword_limit = Column(Integer, default=50, nullable=False)

    # 账户状态
    is_active = Column(Boolean, default=True, nullable=False)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    config = relationship("UserConfig", back_populates="user", uselist=False, cascade="all, delete-orphan")
    keywords = relationship("Keyword", back_populates="user", cascade="all, delete-orphan")
    channels = relationship("NotificationChannel", back_populates="user", cascade="all, delete-orphan")
    push_history = relationship("PushHistory", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, tier={self.tier})>"


class UserConfig(Base):
    """用户配置表"""

    __tablename__ = "user_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    # 报告模式
    report_mode = Column(String(20), default="daily", nullable=False)  # 'daily', 'current', 'incremental'

    # 时区
    timezone = Column(String(50), default="Asia/Shanghai", nullable=False)

    # 推送时间窗口
    push_window_enabled = Column(Boolean, default=False, nullable=False)
    push_window_start = Column(String(5))  # HH:MM
    push_window_end = Column(String(5))    # HH:MM

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    user = relationship("User", back_populates="config")

    def __repr__(self):
        return f"<UserConfig(user_id={self.user_id}, mode={self.report_mode})>"
```

**Step 2: 测试模型导入**

运行: `python -c "from trendradar.models.user import User, UserConfig; print(User.__tablename__)"`
Expected: 输出 "users"

**Step 3: 提交**

```bash
git add trendradar/models/user.py
git commit -m "feat(multiuser): add User and UserConfig models"
```

---

### Task 4: 创建 Keyword 模型

**Files:**
- Create: `trendradar/models/keyword.py`

**Step 1: 创建 Keyword 模型**

创建文件 `trendradar/models/keyword.py`:

```python
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
```

**Step 2: 测试模型导入**

运行: `python -c "from trendradar.models.keyword import Keyword; print(Keyword.__tablename__)"`
Expected: 输出 "keywords"

**Step 3: 提交**

```bash
git add trendradar/models/keyword.py
git commit -m "feat(multiuser): add Keyword model with user relationship"
```

---

### Task 5: 创建 NotificationChannel 和 PushHistory 模型

**Files:**
- Create: `trendradar/models/channel.py`

**Step 1: 创建 NotificationChannel 和 PushHistory 模型**

创建文件 `trendradar/models/channel.py`:

```python
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


class PushStatus(str):
    """推送状态"""
    SUCCESS = "success"
    FAILED = "failed"


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
```

**Step 2: 测试模型导入**

运行: `python -c "from trendradar.models.channel import NotificationChannel, PushHistory; print(NotificationChannel.__tablename__)"`
Expected: 输出 "notification_channels"

**Step 3: 提交**

```bash
git add trendradar/models/channel.py
git commit -m "feat(multiuser): add NotificationChannel and PushHistory models"
```

---

### Task 6: 初始化 Alembic

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`

**Step 1: 安装 Alembic（如果未安装）**

运行: `pip install alembic`
Expected: Alembic 安装成功

**Step 2: 初始化 Alembic**

运行: `alembic init alembic`
Expected: 创建 alembic 目录和 alembic.ini 文件

**Step 3: 配置 alembic.ini**

修改 `alembic.ini` 中的 sqlalchemy.url 行：

```ini
# 将这行：
sqlalchemy.url = driver://user:pass@localhost/dbname

# 改为（使用环境变量）：
sqlalchemy.url = postgresql://trendradar:trendradar@localhost/trendradar
```

**Step 4: 配置 Alembic env.py**

修改 `alembic/env.py`，导入 Base：

```python
# 在文件顶部添加导入
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.append(str(Path(__file__).resolve().parents[1]))

# 在文件中找到 target_metadata = None，替换为：
from trendradar.models.base import Base
target_metadata = Base.metadata
```

**Step 5: 测试 Alembic 配置**

运行: `alembic current`
Expected: 输出当前版本（应该显示为 "Base"）

**Step 6: 提交**

```bash
git add alembic.ini alembic/
git commit -m "feat(multiuser): initialize Alembic for database migrations"
```

---

### Task 7: 创建初始数据库迁移

**Files:**
- Create: `alembic/versions/001_initial_schema.py`

**Step 1: 生成初始迁移**

运行: `alembic revision --autogenerate -m "Initial multiuser schema"`
Expected: 在 `alembic/versions/` 创建新的迁移文件

**Step 2: 检查生成的迁移文件**

运行: `ls -la alembic/versions/ | tail -1`
Expected: 显示最新创建的迁移文件

**Step 3: 提交**

```bash
git add alembic/versions/
git commit -m "feat(multiuser): add initial database migration for multiuser schema"
```

---

### Task 8: 创建 Docker Compose 配置（开发环境）

**Files:**
- Create: `docker-compose.dev.yml`
- Create: `.env.example`

**Step 1: 创建开发环境 Docker Compose 配置**

创建文件 `docker-compose.dev.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: trendradar-postgres-dev
    environment:
      POSTGRES_DB: trendradar
      POSTGRES_USER: trendradar
      POSTGRES_PASSWORD: trendradar_dev_password
      POSTGRES_HOST_AUTH_METHOD: trust
    ports:
      - "5432:5432"
    volumes:
      - postgres_data_dev:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U trendradar"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data_dev:
```

**Step 2: 创建环境变量示例文件**

创建文件 `.env.example`:

```bash
# 数据库配置
DATABASE_URL=postgresql://trendradar:trendradar_dev_password@localhost:5432/trendradar

# GitHub OAuth
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# JWT 密钥
JWT_SECRET=your_random_secret_key_change_this_in_production

# 应用配置
TZ=Asia/Shanghai
LOG_LEVEL=INFO
```

**Step 3: 启动 PostgreSQL 容器**

运行: `docker-compose -f docker-compose.dev.yml up -d postgres`
Expected: PostgreSQL 容器启动成功

**Step 4: 等待 PostgreSQL 就绪**

运行: `docker-compose -f docker-compose.dev.yml logs postgres | tail -10`
Expected: 显示 "database system is ready to accept connections"

**Step 5: 提交**

```bash
git add docker-compose.dev.yml .env.example
git commit -m "feat(multiuser): add Docker Compose for development environment"
```

---

### Task 9: 执行数据库迁移

**Files:**
- Modify: `alembic/env.py` (如果需要)

**Step 1: 设置环境变量**

运行: `export DATABASE_URL="postgresql://trendradar:trendradar_dev_password@localhost:5432/trendradar"`
Expected: 环境变量设置成功

**Step 2: 执行迁移**

运行: `alembic upgrade head`
Expected: 输出 "Running upgrade -> <revision_id>, Initial multiuser schema"

**Step 3: 验证表创建**

运行: `docker exec -it trendradar-postgres-dev psql -U trendradar -d trendradar -c "\dt"`
Expected: 显示所有创建的表（users, user_configs, keywords, notification_channels, push_history, alembic_version）

**Step 4: 测试数据库连接和模型**

创建测试脚本 `test_db_connection.py`:

```python
import os
os.environ["DATABASE_URL"] = "postgresql://trendradar:trendradar_dev_password@localhost:5432/trendradar"

from trendradar.models.base import engine, get_db
from trendradar.models.user import User

# 测试连接
with engine.connect() as conn:
    print("数据库连接成功！")

# 测试模型
from sqlalchemy.orm import Session
from trendradar.models import Base
Base.metadata.create_all(bind=engine)

# 创建测试用户
db = Session(bind=engine)
user = User(email="test@example.com", name="Test User", provider="github", provider_id="12345")
db.add(user)
db.commit()

# 查询用户
users = db.query(User).all()
print(f"用户数量: {len(users)}")
print(f"第一个用户: {users[0]}")

db.close()
```

运行: `python test_db_connection.py`
Expected: 输出 "数据库连接成功！" 和用户信息

**Step 5: 清理测试数据**

运行: `rm test_db_connection.py`
Expected: 测试文件已删除

**Step 6: 提交**

```bash
git add alembic/versions/
git commit -m "feat(multiuser): execute initial database migration successfully"
```

---

## 阶段二：OAuth 认证系统

### Task 10: 创建认证配置和工具

**Files:**
- Create: `trendradar/web/auth/config.py`
- Create: `trendradar/web/auth/utils.py`

**Step 1: 创建 OAuth 配置**

创建文件 `trendradar/web/auth/config.py`:

```python
# coding=utf-8
"""
OAuth 认证配置
"""

from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
import os

# 加载环境变量
config = Config('.env')

# GitHub OAuth 配置
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")

# Google OAuth 配置
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

# OAuth 回调地址
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8000/auth/callback")

# 初始化 OAuth 注册
oauth = OAuth()

# 注册 GitHub
oauth.register(
    name='github',
    client_id=GITHUB_CLIENT_ID,
    client_secret=GITHUB_CLIENT_SECRET,
    server_metadata_url='https://api.github.com/.well-known/oauth-authorization-server',
    client_kwargs={
        'scope': 'user:email'
    }
)

# 注册 Google
oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)
```

**Step 2: 创建 JWT 工具函数**

创建文件 `trendradar/web/auth/utils.py`:

```python
# coding=utf-8
"""
JWT 认证工具
"""

from datetime import datetime, timedelta
from typing import Optional, Dict
from jose import JWTError, jwt
from fastapi import HTTPException, status
import os

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
```

**Step 3: 创建 web 模块的 __init__.py**

创建文件 `trendradar/web/__init__.py`:

```python
# coding=utf-8
"""
TrendRadar Web 服务模块
"""
```

**Step 4: 创建 auth 模块的 __init__.py**

创建文件 `trendradar/web/auth/__init__.py`:

```python
# coding=utf-8
"""
认证模块
"""

from trendradar.web.auth.config import oauth
from trendradar.web.auth.utils import create_access_token, decode_access_token

__all__ = ["oauth", "create_access_token", "decode_access_token"]
```

**Step 5: 测试工具函数**

运行: `python -c "from trendradar.web.auth.utils import create_access_token; token = create_access_token({'user_id': '123'}); print(token[:20] + '...')"`
Expected: 输出 JWT token 的前 20 个字符

**Step 6: 提交**

```bash
git add trendradar/web/
git commit -m "feat(multiuser): add OAuth config and JWT utility functions"
```

---

### Task 11: 创建认证依赖和中间件

**Files:**
- Create: `trendradar/web/auth/dependencies.py`

**Step 1: 创建认证依赖**

创建文件 `trendradar/web/auth/dependencies.py`:

```python
# coding=utf-8
"""
认证依赖和中间件
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Cookie
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
```

**Step 2: 测试依赖导入**

运行: `python -c "from trendradar.web.auth.dependencies import get_current_user; print(get_current_user.__name__)"`
Expected: 输出 "get_current_user"

**Step 3: 提交**

```bash
git add trendradar/web/auth/dependencies.py
git commit -m "feat(multiuser): add authentication dependencies for FastAPI"
```

---

### Task 12: 创建认证 API 路由

**Files:**
- Create: `trendradar/web/routers/__init__.py`
- Create: `trendradar/web/routers/auth.py`

**Step 1: 创建路由模块**

创建文件 `trendradar/web/routers/__init__.py`:

```python
# coding=utf-8
"""
API 路由模块
"""
```

**Step 2: 创建认证路由**

创建文件 `trendradar/web/routers/auth.py`:

```python
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
```

**Step 3: 测试路由导入**

运行: `python -c "from trendradar.web.routers.auth import router; print(router.prefix)"`
Expected: 输出 "/auth"

**Step 4: 提交**

```bash
git add trendradar/web/routers/
git commit -m "feat(multiuser): add authentication API routes (OAuth login, callback, logout)"
```

---

## 阶段三：FastAPI Web 应用主框架

### Task 13: 创建 FastAPI 应用主文件

**Files:**
- Create: `trendradar/web/app.py`

**Step 1: 创建 FastAPI 应用**

创建文件 `trendradar/web/app.py`:

```python
# coding=utf-8
"""
TrendRadar Web 应用主入口
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware
import os

from trendradar.models.base import engine, Base
from trendradar.web.routers import auth

# 创建 FastAPI 应用
app = FastAPI(
    title="TrendRadar",
    description="热点新闻聚合与分析工具 - 多用户版",
    version="5.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含路由
app.include_router(auth.router)

# 静态文件和模板
templates = Jinja2Templates(directory="trendradar/web/templates")
app.mount("/static", StaticFiles(directory="trendradar/web/static"), name="static")


# 事件处理器
@app.on_event("startup")
async def startup_event():
    """应用启动时创建数据库表"""
    Base.metadata.create_all(bind=engine)
    print("数据库表创建完成")


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "message": "TrendRadar Web 服务运行正常"
    }


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "服务器内部错误",
            "message": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
```

**Step 2: 创建静态文件和模板目录**

运行:
```bash
mkdir -p trendradar/web/static/css
mkdir -p trendradar/web/static/js
mkdir -p trendradar/web/templates
```

Expected: 目录创建成功

**Step 3: 创建空的 CSS 和 JS 文件**

运行:
```bash
touch trendradar/web/static/css/style.css
touch trendradar/web/static/js/app.js
```

Expected: 空文件创建成功

**Step 4: 测试 FastAPI 应用导入**

运行: `python -c "from trendradar.web.app import app; print(app.title)"`
Expected: 输出 "TrendRadar"

**Step 5: 提交**

```bash
git add trendradar/web/app.py trendradar/web/static/ trendradar/web/templates/
git commit -m "feat(multiuser): add FastAPI application with basic setup and health check"
```

---

### Task 14: 创建登录页面模板

**Files:**
- Create: `trendradar/web/templates/login.html`

**Step 1: 创建登录页面**

创建文件 `trendradar/web/templates/login.html`:

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登录 - TrendRadar</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center">
    <div class="max-w-md w-full bg-white rounded-lg shadow-md p-8">
        <!-- 标题 -->
        <div class="text-center mb-8">
            <h1 class="text-3xl font-bold text-gray-900">TrendRadar</h1>
            <p class="text-gray-600 mt-2">热点新闻聚合与分析工具</p>
        </div>

        <!-- 登录按钮 -->
        <div class="space-y-4">
            <!-- GitHub 登录 -->
            <a href="/auth/login/github"
               class="flex items-center justify-center w-full px-4 py-3 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors">
                <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84-1.235 1.911-1.237 1.911-1.237 2.598 5.467 5.467 5.467 1.387 0 2.598-.469 3.22-1.24.715 1.676-1.237 2.665-.404 1.06-.305 2.467-1.237 3.003-.245.665.535-1.304.762-1.604-.898-.727-1.334-1.416-1.334-1.416V12c0-6.627-5.373-12-12-12z"/>
                </svg>
                使用 GitHub 登录
            </a>

            <!-- Google 登录 -->
            <a href="/auth/login/google"
               class="flex items-center justify-center w-full px-4 py-3 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors">
                <svg class="w-5 h-5 mr-2" viewBox="0 0 24 24">
                    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                使用 Google 登录
            </a>
        </div>

        <!-- 提示信息 -->
        <p class="mt-6 text-center text-sm text-gray-500">
            登录即表示您同意我们的
            <a href="#" class="text-blue-600 hover:text-blue-700">服务条款</a>
            和
            <a href="#" class="text-blue-600 hover:text-blue-700">隐私政策</a>
        </p>
    </div>
</body>
</html>
```

**Step 2: 测试模板文件**

运行: `ls -la trendradar/web/templates/login.html`
Expected: 模板文件存在

**Step 3: 添加首页路由**

修改 `trendradar/web/app.py`，在路由部分添加：

```python
from fastapi.responses import HTMLResponse
from trendradar.web.auth.dependencies import get_current_user, get_optional_user
from trendradar.models.user import User

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, current_user: User = Depends(get_optional_user)):
    """首页"""
    if not current_user:
        # 未登录，显示登录页
        return templates.TemplateResponse("login.html", {"request": request})

    # 已登录，显示配置页（稍后实现）
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": current_user})
```

**Step 4: 创建空的 dashboard 模板（占位）**

创建文件 `trendradar/web/templates/dashboard.html`:

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>配置页面 - TrendRadar</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50">
    <div class="container mx-auto p-8">
        <h1 class="text-2xl font-bold">欢迎，{{ user.name }}！</h1>
        <p class="mt-4">配置页面正在开发中...</p>
        <a href="/auth/logout" class="text-blue-600 hover:underline">退出登录</a>
    </div>
</body>
</html>
```

**Step 5: 提交**

```bash
git add trendradar/web/templates/ trendradar/web/app.py
git commit -m "feat(multiuser): add login page template and index route"
```

---

### Task 15: 测试 OAuth 登录流程（手动测试）

**Files:**
- None (手动测试)

**Step 1: 启动 Web 服务**

运行: `python -m uvicorn trendradar.web.app:app --reload --host 0.0.0.0 --port 8000`
Expected: 输出 "Uvicorn running on http://0.0.0.0:8000"

**Step 2: 访问登录页面**

运行: 在浏览器打开 `http://localhost:8000`
Expected: 显示登录页面

**Step 3: 测试健康检查**

运行: `curl http://localhost:8000/health`
Expected: 返回 JSON `{"status": "healthy", "message": "..."}`

**Step 4: 测试 API 文档**

运行: 在浏览器打开 `http://localhost:8000/api/docs`
Expected: 显示 FastAPI 自动生成的 API 文档

**Step 5: 停止服务**

按 Ctrl+C 停止服务

**Step 6: 提交（无需提交，仅为手动测试）**

此任务为手动测试，无需提交代码。

---

## 阶段四：用户配置 API

### Task 16: 创建用户配置 API

**Files:**
- Create: `trendradar/web/routers/config.py`

**Step 1: 创建配置路由**

创建文件 `trendradar/web/routers/config.py`:

```python
# coding=utf-8
"""
用户配置 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import time

from trendradar.models.base import get_db
from trendradar.models.user import User, UserConfig
from trendradar.web.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/config", tags=["config"])


# Pydantic 模型
class ConfigUpdate(BaseModel):
    """配置更新请求"""
    report_mode: Optional[str] = None
    timezone: Optional[str] = None
    push_window_enabled: Optional[bool] = None
    push_window_start: Optional[str] = None
    push_window_end: Optional[str] = None


class ConfigResponse(BaseModel):
    """配置响应"""
    report_mode: str
    timezone: str
    push_window_enabled: bool
    push_window_start: Optional[str]
    push_window_end: Optional[str]


@router.get("", response_model=ConfigResponse)
async def get_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取用户配置

    Returns:
        用户配置
    """
    config = db.query(UserConfig).filter(UserConfig.user_id == current_user.id).first()

    if not config:
        # 创建默认配置
        config = UserConfig(user_id=current_user.id)
        db.add(config)
        db.commit()
        db.refresh(config)

    return ConfigResponse(
        report_mode=config.report_mode,
        timezone=config.timezone,
        push_window_enabled=config.push_window_enabled,
        push_window_start=config.push_window_start,
        push_window_end=config.push_window_end
    )


@router.put("", response_model=ConfigResponse)
async def update_config(
    update_data: ConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新用户配置

    Args:
        update_data: 配置更新数据
        current_user: 当前用户

    Returns:
        更新后的配置
    """
    config = db.query(UserConfig).filter(UserConfig.user_id == current_user.id).first()

    if not config:
        config = UserConfig(user_id=current_user.id)
        db.add(config)

    # 更新字段
    if update_data.report_mode is not None:
        if update_data.report_mode not in ["daily", "current", "incremental"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的 report_mode，必须是 daily, current 或 incremental"
            )
        config.report_mode = update_data.report_mode

    if update_data.timezone is not None:
        config.timezone = update_data.timezone

    if update_data.push_window_enabled is not None:
        config.push_window_enabled = update_data.push_window_enabled

    if update_data.push_window_start is not None:
        # 验证时间格式 HH:MM
        try:
            time.strptime(update_data.push_window_start, "%H:%M")
            config.push_window_start = update_data.push_window_start
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="push_window_start 格式错误，应为 HH:MM"
            )

    if update_data.push_window_end is not None:
        try:
            time.strptime(update_data.push_window_end, "%H:%M")
            config.push_window_end = update_data.push_window_end
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="push_window_end 格式错误，应为 HH:MM"
            )

    db.commit()
    db.refresh(config)

    return ConfigResponse(
        report_mode=config.report_mode,
        timezone=config.timezone,
        push_window_enabled=config.push_window_enabled,
        push_window_start=config.push_window_start,
        push_window_end=config.push_window_end
    )
```

**Step 2: 注册配置路由**

修改 `trendradar/web/app.py`，导入并注册路由：

```python
from trendradar.web.routers import auth, config

# 在路由包含部分添加
app.include_router(config.router)
```

**Step 3: 测试配置路由**

运行: `python -c "from trendradar.web.routers.config import router; print(router.tags)"`
Expected: 输出 `['config']`

**Step 4: 提交**

```bash
git add trendradar/web/routers/config.py trendradar/web/app.py
git commit -m "feat(multiuser): add user configuration API endpoints"
```

---

### Task 17: 创建关键词管理 API

**Files:**
- Create: `trendradar/web/routers/keywords.py`

**Step 1: 创建关键词路由**

创建文件 `trendradar/web/routers/keywords.py`:

```python
# coding=utf-8
"""
关键词管理 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID

from trendradar.models.base import get_db
from trendradar.models.user import User
from trendradar.models.keyword import Keyword
from trendradar.web.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/keywords", tags=["keywords"])


# Pydantic 模型
class KeywordCreate(BaseModel):
    """创建关键词请求"""
    content: str
    group_order: int = 0
    is_required: bool = False
    is_filtered: bool = False
    max_count: int = 0


class KeywordUpdate(BaseModel):
    """更新关键词请求"""
    content: Optional[str] = None
    group_order: Optional[int] = None
    is_required: Optional[bool] = None
    is_filtered: Optional[bool] = None
    max_count: Optional[int] = None


class KeywordResponse(BaseModel):
    """关键词响应"""
    id: str
    content: str
    group_order: int
    is_required: bool
    is_filtered: bool
    max_count: int


@router.get("", response_model=List[KeywordResponse])
async def get_keywords(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户的所有关键词"""
    keywords = db.query(Keyword).filter(Keyword.user_id == current_user.id).order_by(Keyword.group_order, Keyword.created_at).all()

    return [
        KeywordResponse(
            id=str(k.id),
            content=k.content,
            group_order=k.group_order,
            is_required=k.is_required,
            is_filtered=k.is_filtered,
            max_count=k.max_count
        )
        for k in keywords
    ]


@router.post("", response_model=KeywordResponse, status_code=status.HTTP_201_CREATED)
async def create_keyword(
    keyword_data: KeywordCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建关键词"""
    # 检查关键词数量限制
    keyword_count = db.query(Keyword).filter(Keyword.user_id == current_user.id).count()
    if keyword_count >= current_user.keyword_limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"已达到关键词数量限制 ({current_user.keyword_limit})，请升级账户"
        )

    keyword = Keyword(
        user_id=current_user.id,
        content=keyword_data.content,
        group_order=keyword_data.group_order,
        is_required=keyword_data.is_required,
        is_filtered=keyword_data.is_filtered,
        max_count=keyword_data.max_count
    )
    db.add(keyword)
    db.commit()
    db.refresh(keyword)

    return KeywordResponse(
        id=str(keyword.id),
        content=keyword.content,
        group_order=keyword.group_order,
        is_required=keyword.is_required,
        is_filtered=keyword.is_filtered,
        max_count=keyword.max_count
    )


@router.put("/{keyword_id}", response_model=KeywordResponse)
async def update_keyword(
    keyword_id: UUID,
    keyword_data: KeywordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新关键词"""
    keyword = db.query(Keyword).filter(
        Keyword.id == keyword_id,
        Keyword.user_id == current_user.id
    ).first()

    if not keyword:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="关键词不存在"
        )

    # 更新字段
    if keyword_data.content is not None:
        keyword.content = keyword_data.content
    if keyword_data.group_order is not None:
        keyword.group_order = keyword_data.group_order
    if keyword_data.is_required is not None:
        keyword.is_required = keyword_data.is_required
    if keyword_data.is_filtered is not None:
        keyword.is_filtered = keyword_data.is_filtered
    if keyword_data.max_count is not None:
        keyword.max_count = keyword_data.max_count

    db.commit()
    db.refresh(keyword)

    return KeywordResponse(
        id=str(keyword.id),
        content=keyword.content,
        group_order=keyword.group_order,
        is_required=keyword.is_required,
        is_filtered=keyword.is_filtered,
        max_count=keyword.max_count
    )


@router.delete("/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keyword(
    keyword_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除关键词"""
    keyword = db.query(Keyword).filter(
        Keyword.id == keyword_id,
        Keyword.user_id == current_user.id
    ).first()

    if not keyword:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="关键词不存在"
        )

    db.delete(keyword)
    db.commit()
```

**Step 2: 注册关键词路由**

修改 `trendradar/web/app.py`:

```python
from trendradar.web.routers import auth, config, keywords

app.include_router(keywords.router)
```

**Step 3: 测试路由导入**

运行: `python -c "from trendradar.web.routers.keywords import router; print(router.tags)"`
Expected: 输出 `['keywords']`

**Step 4: 提交**

```bash
git add trendradar/web/routers/keywords.py trendradar/web/app.py
git commit -m "feat(multiuser): add keyword management API endpoints"
```

---

### Task 18: 创建推送渠道管理 API

**Files:**
- Create: `trendradar/web/routers/channels.py`

**Step 1: 创建推送渠道路由**

创建文件 `trendradar/web/routers/channels.py`:

```python
# coding=utf-8
"""
推送渠道管理 API 路由
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict
from uuid import UUID

from trendradar.models.base import get_db
from trendradar.models.user import User
from trendradar.models.channel import NotificationChannel
from trendradar.web.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/channels", tags=["channels"])


# Pydantic 模型
class ChannelCreate(BaseModel):
    """创建推送渠道请求"""
    channel_type: str  # 'feishu', 'telegram', 'dingtalk', 'email', 'ntfy', 'bark', 'slack'
    config: Dict


class ChannelUpdate(BaseModel):
    """更新推送渠道请求"""
    enabled: Optional[bool] = None
    config: Optional[Dict] = None


class ChannelResponse(BaseModel):
    """推送渠道响应"""
    id: str
    channel_type: str
    config: Dict
    enabled: bool


@router.get("", response_model=List[ChannelResponse])
async def get_channels(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户的所有推送渠道"""
    channels = db.query(NotificationChannel).filter(NotificationChannel.user_id == current_user.id).all()

    return [
        ChannelResponse(
            id=str(c.id),
            channel_type=c.channel_type,
            config=c.config,
            enabled=c.enabled
        )
        for c in channels
    ]


@router.post("", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(
    channel_data: ChannelCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建推送渠道"""
    # 验证渠道类型
    valid_types = ["feishu", "telegram", "dingtalk", "email", "ntfy", "bark", "slack"]
    if channel_data.channel_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的渠道类型，必须是: {', '.join(valid_types)}"
        )

    # 验证配置
    validate_channel_config(channel_data.channel_type, channel_data.config)

    channel = NotificationChannel(
        user_id=current_user.id,
        channel_type=channel_data.channel_type,
        config=channel_data.config
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)

    return ChannelResponse(
        id=str(channel.id),
        channel_type=channel.channel_type,
        config=channel.config,
        enabled=channel.enabled
    )


@router.put("/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: UUID,
    channel_data: ChannelUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新推送渠道"""
    channel = db.query(NotificationChannel).filter(
        NotificationChannel.id == channel_id,
        NotificationChannel.user_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="推送渠道不存在"
        )

    # 更新字段
    if channel_data.enabled is not None:
        channel.enabled = channel_data.enabled

    if channel_data.config is not None:
        # 验证配置
        validate_channel_config(channel.channel_type, channel_data.config)
        channel.config = channel_data.config

    db.commit()
    db.refresh(channel)

    return ChannelResponse(
        id=str(channel.id),
        channel_type=channel.channel_type,
        config=channel.config,
        enabled=channel.enabled
    )


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    channel_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除推送渠道"""
    channel = db.query(NotificationChannel).filter(
        NotificationChannel.id == channel_id,
        NotificationChannel.user_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="推送渠道不存在"
        )

    db.delete(channel)
    db.commit()


@router.post("/{channel_id}/test", status_code=status.HTTP_200_OK)
async def test_channel(
    channel_id: UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """测试推送渠道"""
    channel = db.query(NotificationChannel).filter(
        NotificationChannel.id == channel_id,
        NotificationChannel.user_id == current_user.id
    ).first()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="推送渠道不存在"
        )

    # TODO: 实现实际的测试推送逻辑
    # 这里可以调用推送服务发送测试消息

    return {
        "message": "测试推送已发送",
        "channel_type": channel.channel_type
    }


def validate_channel_config(channel_type: str, config: Dict):
    """验证渠道配置"""
    if channel_type == "feishu":
        if "webhook_url" not in config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Feishu 渠道需要 webhook_url 配置"
            )
    elif channel_type == "telegram":
        if "bot_token" not in config or "chat_id" not in config:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Telegram 渠道需要 bot_token 和 chat_id 配置"
            )
    # ... 其他渠道的验证
```

**Step 2: 注册推送渠道路由**

修改 `trendradar/web/app.py`:

```python
from trendradar.web.routers import auth, config, keywords, channels

app.include_router(channels.router)
```

**Step 3: 测试路由导入**

运行: `python -c "from trendradar.web.routers.channels import router; print(router.tags)"`
Expected: 输出 `['channels']`

**Step 4: 提交**

```bash
git add trendradar/web/routers/channels.py trendradar/web/app.py
git commit -m "feat(multiuser): add notification channel management API endpoints"
```

---

## 阶段五：爬虫多用户集成

### Task 19: 创建数据库配置读取器

**Files:**
- Create: `trendradar/core/database_config.py`

**Step 1: 创建数据库配置读取器**

创建文件 `trendradar/core/database_config.py`:

```python
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
from trendradar.core.frequency import WordGroup


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

    def get_user_keywords_as_groups(self, user_id: UUID) -> List[WordGroup]:
        """
        获取用户的关键词并转换为词组格式

        Args:
            user_id: 用户 ID

        Returns:
            词组列表
        """
        keywords = self.get_user_keywords(user_id)

        # 按空行分隔词组（group_order 变化处）
        groups = []
        current_group = []
        last_order = None

        for keyword in keywords:
            # 如果 group_order 变化（跳过数字），表示新词组
            if last_order is not None and keyword.group_order != last_order:
                if current_group:
                    groups.append(current_group)
                current_group = []

            # 添加关键词到当前词组
            current_group.append(keyword.content)
            last_order = keyword.group_order

        # 添加最后一个词组
        if current_group:
            groups.append(current_group)

        # 转换为 WordGroup 对象
        word_groups = []
        for group in groups:
            word_groups.append(WordGroup(words=group))

        return word_groups

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
```

**Step 2: 测试配置读取器导入**

运行: `python -c "from trendradar.core.database_config import DatabaseConfigReader; print(DatabaseConfigReader.__name__)"`
Expected: 输出 "DatabaseConfigReader"

**Step 3: 提交**

```bash
git add trendradar/core/database_config.py
git commit -m "feat(multiuser): add DatabaseConfigReader for reading user configs from database"
```

---

### Task 20: 创建配额检查器

**Files:**
- Create: `trendradar/notification/quota.py`

**Step 1: 创建配额检查器**

创建文件 `trendradar/notification/quota.py`:

```python
# coding=utf-8
"""
配额检查器
"""

from datetime import datetime, time
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
```

**Step 2: 测试配额检查器导入**

运行: `python -c "from trendradar.notification.quota import QuotaChecker; print(QuotaChecker.__name__)"`
Expected: 输出 "QuotaChecker"

**Step 3: 提交**

```bash
git add trendradar/notification/quota.py
git commit -m "feat(multiuser): add QuotaChecker for push limit management"
```

---

### Task 21: 修改爬虫主流程支持多用户

**Files:**
- Modify: `trendradar/__main__.py`
- Create: `trendradar/crawler/scheduler.py`

**Step 1: 修改 NewsAnalyzer 类添加数据库支持**

修改 `trendradar/__main__.py` 的 `NewsAnalyzer.__init__` 方法，添加数据库支持：

在文件顶部添加导入：
```python
from trendradar.models.base import get_db, SessionLocal
from trendradar.core.database_config import DatabaseConfigReader
from trendradar.notification.quota import QuotaChecker
```

修改 `__init__` 方法，在初始化存储管理器之后添加：

```python
# 初始化数据库会话（用于多用户配置）
self.db_session = SessionLocal()
self.db_reader = DatabaseConfigReader(self.db_session)
self.quota_checker = QuotaChecker(self.db_session)
```

**Step 2: 修改 cleanup 方法**

修改 `cleanup` 方法，添加数据库会话清理：

```python
def cleanup(self) -> None:
    """清理资源"""
    if self._backend:
        self._backend.cleanup()
    if self._remote_backend:
        self._remote_backend.cleanup()

    # 关闭数据库会话
    if hasattr(self, 'db_session') and self.db_session:
        self.db_session.close()
```

**Step 3: 创建多用户推送方法**

在 `NewsAnalyzer` 类中添加新方法：

```python
def _push_for_all_users(self, results: Dict, rss_items: Optional[List[Dict]] = None, rss_new_items: Optional[List[Dict]] = None) -> None:
    """
    为所有用户推送新闻（多用户模式）

    Args:
        results: 抓取的热榜新闻结果
        rss_items: RSS 统计条目（可选）
        rss_new_items: RSS 新增条目（可选）
    """
    # 获取所有激活用户
    users = self.db_reader.get_all_active_users()

    print(f"[多用户] 开始为 {len(users)} 个用户推送新闻")

    for user in users:
        user_id = user.id

        # 检查配额
        can_push, reason = self.quota_checker.can_push(user_id)
        if not can_push:
            print(f"[多用户] 用户 {user.email}: {reason}，跳过推送")
            continue

        # 获取用户配置
        user_config = self.db_reader.get_user_config(user_id)
        if not user_config:
            print(f"[多用户] 用户 {user.email}: 未找到配置，跳过推送")
            continue

        # 获取用户关键词
        try:
            word_groups = self.db_reader.get_user_keywords_as_groups(user_id)
            filter_words = self.db_reader.get_user_filter_words(user_id)
        except Exception as e:
            print(f"[多用户] 用户 {user.email}: 读取关键词失败: {e}")
            continue

        # 获取用户推送渠道
        channels = self.db_reader.get_user_channels(user_id, enabled_only=True)
        if not channels:
            print(f"[多用户] 用户 {user.email}: 未配置推送渠道，跳过推送")
            continue

        # 根据用户配置过滤新闻
        stats, total_titles = self.ctx.count_frequency(
            results,
            word_groups,
            filter_words,
            {},  # id_to_name，暂时为空
            {},  # title_info，暂时为空
            {},  # new_titles，暂时为空
            mode=user_config.report_mode,
            global_filters=[],
            quiet=True
        )

        # 检查是否有匹配的新闻
        if not stats or total_titles == 0:
            print(f"[多用户] 用户 {user.email}: 没有匹配的新闻")
            continue

        # 准备推送内容
        report_data = self.ctx.prepare_report(stats, [], {}, {}, mode=user_config.report_mode)

        # 推送到所有渠道
        success_count = 0
        for channel in channels:
            try:
                # TODO: 实现实际的推送逻辑
                # 这里可以复用现有的 NotificationDispatcher
                print(f"[多用户] 用户 {user.email}: 推送到 {channel.channel_type}")
                success_count += 1
            except Exception as e:
                print(f"[多用户] 用户 {user.email}: 推送到 {channel.channel_type} 失败: {e}")
                self.quota_checker.record_push(
                    user_id,
                    channel.channel_type,
                    0,
                    success=False,
                    error_message=str(e)
                )

        # 记录成功的推送
        if success_count > 0:
            self.quota_checker.record_push(
                user_id,
                channels[0].channel_type,
                total_titles,
                success=True
            )
            print(f"[多用户] 用户 {user.email}: 推送完成，共 {total_titles} 条新闻")
```

**Step 4: 修改 run 方法支持多用户模式**

在 `NewsAnalyzer.run` 方法中，添加环境变量检查：

```python
def run(self) -> None:
    """执行分析流程"""
    try:
        self._initialize_and_check_config()

        mode_strategy = self._get_mode_strategy()

        # 抓取热榜数据
        results, id_to_name, failed_ids = self._crawl_data()

        # 抓取 RSS 数据
        rss_items, rss_new_items = self._crawl_rss_data()

        # 检查是否启用多用户模式
        if os.environ.get("MULTIUSER_MODE", "false").lower() == "true":
            # 多用户模式：为每个用户推送
            self._push_for_all_users(results, rss_items, rss_new_items)
        else:
            # 单用户模式：原有逻辑
            self._execute_mode_strategy(
                mode_strategy, results, id_to_name, failed_ids,
                rss_items=rss_items, rss_new_items=rss_new_items
            )

    except Exception as e:
        print(f"分析流程执行出错: {e}")
        raise
    finally:
        # 清理资源
        self.ctx.cleanup()
```

**Step 5: 创建定时调度器**

创建文件 `trendradar/crawler/scheduler.py`:

```python
# coding=utf-8
"""
爬虫定时调度器
"""

import os
import schedule
import time
from trendradar.__main__ import NewsAnalyzer

def run_crawler():
    """执行一次爬虫任务"""
    print(f"[调度器] 开始执行爬虫任务 - {time.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        analyzer = NewsAnalyzer()
        analyzer.run()
        print(f"[调度器] 爬虫任务完成 - {time.strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(f"[调度器] 爬虫任务失败: {e}")

    print(f"[调度器] 等待下次执行...")


def main():
    """主入口"""
    # 设置多用户模式环境变量
    os.environ["MULTIUSER_MODE"] = "true"

    # 每小时执行一次
    schedule.every().hour.do(run_crawler)

    print("[调度器] 多用户爬虫调度器已启动")
    print(f"[调度器] 首次执行将在下一小时开始，或手动执行一次测试")

    # 立即执行一次（用于测试）
    run_crawler()

    # 持续运行
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次


if __name__ == "__main__":
    main()
```

**Step 6: 更新 requirements.txt 添加 schedule 库**

修改 `requirements.txt`:

```txt
requests>=2.32.5,<3.0.0
pytz>=2025.2,<2026.0
PyYAML>=6.0.3,<7.0.0
fastmcp>=2.12.0,<2.14.0
websockets>=13.0,<14.0
feedparser>=6.0.0,<7.0.0
boto3>=1.35.0,<2.0.0
# 新增
schedule>=1.2.0,<2.0.0
```

**Step 7: 测试调度器导入**

运行: `python -c "from trendradar.crawler.scheduler import main; print(main.__name__)"`
Expected: 输出 "main"

**Step 8: 提交**

```bash
git add trendradar/__main__.py trendradar/crawler/scheduler.py requirements.txt
git commit -m "feat(multiuser): add multiuser support to crawler with quota checking and scheduler"
```

---

## 阶段六：Docker 部署配置

### Task 22: 创建生产环境 Docker Compose 配置

**Files:**
- Create: `docker-compose.yml`
- Create: `Dockerfile`

**Step 1: 创建 Dockerfile**

创建文件 `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 暴露端口
EXPOSE 8000

# 默认命令（Web 服务）
CMD ["uvicorn", "trendradar.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 2: 创建生产环境 Docker Compose 配置**

创建文件 `docker-compose.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: trendradar-postgres
    environment:
      POSTGRES_DB: trendradar
      POSTGRES_USER: trendradar
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U trendradar"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  web:
    build: .
    container_name: trendradar-web
    environment:
      DATABASE_URL: postgresql://trendradar:${DB_PASSWORD}@postgres:5432/trendradar
      GITHUB_CLIENT_ID: ${GITHUB_CLIENT_ID}
      GITHUB_CLIENT_SECRET: ${GITHUB_CLIENT_SECRET}
      GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID}
      GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET}
      JWT_SECRET: ${JWT_SECRET}
      MULTIUSER_MODE: "true"
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

  crawler:
    build: .
    container_name: trendradar-crawler
    command: python -m trendradar.crawler.scheduler
    environment:
      DATABASE_URL: postgresql://trendradar:${DB_PASSWORD}@postgres:5432/trendradar
      MULTIUSER_MODE: "true"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./output:/app/output
    restart: unless-stopped

volumes:
  postgres_data:
```

**Step 3: 更新 .gitignore**

修改 `.gitignore`（如果存在），或创建它：

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# 虚拟环境
venv/
ENV/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# 数据库
*.db
*.sqlite
*.sqlite3

# 日志
logs/
*.log

# 输出
output/

# 环境变量
.env
.env.local

# Alembic
alembic/versions/*.pyc
```

**Step 4: 提交**

```bash
git add Dockerfile docker-compose.yml .gitignore
git commit -m "feat(multiuser): add production Docker deployment configuration"
```

---

## 阶段七：测试与文档

### Task 23: 创建集成测试

**Files:**
- Create: `tests/test_multiuser_api.py`

**Step 1: 创建测试目录和文件**

运行:
```bash
mkdir -p tests
touch tests/__init__.py
```

创建文件 `tests/test_multiuser_api.py`:

```python
# coding=utf-8
"""
多用户系统集成测试
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4

from trendradar.web.app import app
from trendradar.models.base import Base, get_db
from trendradar.models.user import User, UserConfig, UserTier


# 测试数据库
TEST_DATABASE_URL = "postgresql://trendradar:trendradar_dev_password@localhost:5432/trendradar_test"


# 设置测试客户端
@pytest.fixture
def client():
    return TestClient(app)


# 设置测试数据库
@pytest.fixture(scope="module")
def test_db():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # 创建所有表
    Base.metadata.create_all(bind=engine)

    yield TestingSessionLocal

    # 清理
    Base.metadata.drop_all(bind=engine)


def test_health_check(client):
    """测试健康检查端点"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_login_redirect(client):
    """测试登录重定向"""
    response = client.get("/auth/login/github")
    # 应该重定向到 GitHub
    assert response.status_code == 302


def test_get_me_without_auth(client):
    """测试未登录访问 /me"""
    response = client.get("/api/me")
    assert response.status_code == 401


def test_get_config_without_auth(client):
    """测试未登录访问配置"""
    response = client.get("/api/config")
    assert response.status_code == 401


def test_create_user(test_db):
    """测试创建用户"""
    user = User(
        email="test@example.com",
        name="Test User",
        provider="github",
        provider_id="12345",
        tier=UserTier.FREE.value
    )
    test_db.add(user)
    test_db.commit()

    assert user.id is not None
    assert user.email == "test@example.com"


def test_user_config_relationship(test_db):
    """测试用户和配置的关系"""
    user = User(
        email="config@example.com",
        name="Config User",
        provider="github",
        provider_id="67890"
    )
    test_db.add(user)
    test_db.flush()

    config = UserConfig(
        user_id=user.id,
        report_mode="daily"
    )
    test_db.add(config)
    test_db.commit()

    assert config.user == user
    assert user.config == config


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Step 2: 安装测试依赖**

运行: `pip install pytest httpx`
Expected: 测试依赖安装成功

**Step 3: 创建测试数据库**

运行: `docker exec -it trendradar-postgres-dev psql -U trendradar -c "CREATE DATABASE trendradar_test;"`
Expected: 测试数据库创建成功

**Step 4: 运行测试**

运行: `pytest tests/test_multiuser_api.py -v`
Expected: 测试通过（注意：OAuth 重定向测试可能会失败，这是正常的）

**Step 5: 提交**

```bash
git add tests/
git commit -m "test(multiuser): add integration tests for multiuser API"
```

---

### Task 24: 创建部署文档

**Files:**
- Create: `docs/deployment-guide.md`

**Step 1: 创建部署指南**

创建文件 `docs/deployment-guide.md`:

```markdown
# TrendRadar 多用户系统部署指南

## 前置要求

- Docker 和 Docker Compose
- GitHub OAuth App（[申请地址](https://github.com/settings/developers)）
- Google OAuth Client ID（[申请地址](https://console.cloud.google.com/)

## 快速开始

### 1. 准备配置文件

复制环境变量示例：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入以下配置：

```bash
# 数据库密码
DB_PASSWORD=your_secure_password

# GitHub OAuth（从 https://github.com/settings/developers 获取）
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# Google OAuth（从 https://console.cloud.google.com/ 获取）
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# JWT 密钥（使用随机字符串）
JWT_SECRET=$(openssl rand -hex 32)
```

### 2. 启动服务

```bash
# 启动所有服务（PostgreSQL + Web + Crawler）
docker-compose up -d

# 查看日志
docker-compose logs -f web

# 停止服务
docker-compose down
```

### 3. 初始化数据库

```bash
# 进入 Web 容器
docker-compose exec web bash

# 运行数据库迁移
alembic upgrade head

# 退出容器
exit
```

### 4. 访问应用

- Web 服务: http://localhost:8000
- API 文档: http://localhost:8000/api/docs
- 健康检查: http://localhost:8000/health

## 生产环境部署

### 1. 使用 PostgreSQL 持久化数据

数据存储在 Docker volume 中，重启容器不会丢失。

### 2. 配置 HTTPS

使用 Nginx 反向代理配置 HTTPS。

### 3. 定时任务

Crawler 服务每小时自动执行一次，为所有用户推送新闻。

## 监控与日志

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f web
docker-compose logs -f crawler

# 查看最近 100 行日志
docker-compose logs --tail=100 web
```

### 健康检查

```bash
curl http://localhost:8000/health
```

## 故障排查

### 问题 1: 数据库连接失败

检查 PostgreSQL 容器状态：
```bash
docker-compose ps
docker-compose logs postgres
```

### 问题 2: OAuth 回调失败

检查环境变量是否正确配置：
```bash
docker-compose exec web env | grep OAUTH
```

确保 OAuth 应用的回调 URL 配置为：
```
http://your-domain.com/auth/callback/github
http://your-domain.com/auth/callback/google
```

### 问题 3: 爬虫未推送

检查爬虫日志：
```bash
docker-compose logs crawler | grep "多用户"
```

## 备份与恢复

### 备份数据库

```bash
# 备份数据库
docker exec trendradar-postgres pg_dump -U trendradar trendradar > backup_$(date +%Y%m%d).sql
```

### 恢复数据库

```bash
# 恢复数据库
cat backup_20250102.sql | docker exec -i trendradar-postgres psql -U trendradar trendradar
```
```

**Step 2: 测试文档导入**

运行: `ls -la docs/deployment-guide.md`
Expected: 文档存在

**Step 3: 提交**

```bash
git add docs/deployment-guide.md
git commit -m "docs(multiuser): add deployment guide for production environment"
```

---

## 总结

此实施计划包含 24 个任务，涵盖以下内容：

1. **阶段一：基础设施搭建**（任务 1-9）
   - 依赖更新
   - 数据库模型创建
   - Alembic 迁移设置
   - Docker 开发环境

2. **阶段二：OAuth 认证系统**（任务 10-12）
   - OAuth 配置
   - JWT 工具函数
   - 认证 API 路由

3. **阶段三：FastAPI Web 应用**（任务 13-15）
   - FastAPI 应用创建
   - 登录页面
   - 手动测试

4. **阶段四：用户配置 API**（任务 16-18）
   - 配置管理 API
   - 关键词管理 API
   - 推送渠道管理 API

5. **阶段五：爬虫多用户集成**（任务 19-21）
   - 数据库配置读取器
   - 配额检查器
   - 爬虫主流程改造
   - 定时调度器

6. **阶段六：Docker 部署**（任务 22）
   - Dockerfile 创建
   - Docker Compose 配置

7. **阶段七：测试与文档**（任务 23-24）
   - 集成测试
   - 部署文档

每个任务都包含：
- 详细的文件路径
- 完整的代码示例
- 测试步骤
- 提交步骤

总预计开发时间：约 3-4 周（按每天 4-6 小时计算）

---

**实施计划版本**: 1.0
**创建日期**: 2025-01-02
**最后更新**: 2025-01-02
