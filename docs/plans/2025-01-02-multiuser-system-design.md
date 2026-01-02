# TrendRadar 多用户系统设计方案

**日期**: 2025-01-02
**版本**: 1.0
**作者**: Claude Code

## 概述

本文档描述了 TrendRadar 从单用户系统改造为多用户系统的完整设计方案。新系统支持用户通过 GitHub/Google 账号登录，在可视化界面中配置个人关键词和推送渠道，并根据用户等级提供不同的服务配额。

## 目标

- 支持多用户注册和登录（GitHub、Google OAuth）
- 提供可视化配置界面（关键词、推送渠道、报告设置）
- 实现用户数据隔离和配额管理
- 保持现有爬虫和推送功能，最小化代码改动
- 支持小规模部署（1-100 用户）

---

## 1. 系统架构

### 1.1 整体架构

系统采用微服务架构，分为三个核心模块：

**Web 服务模块** (`trendradar/web/`)
- 使用 FastAPI 提供 REST API 和 Web 页面
- 负责用户认证、配置管理、前端页面渲染
- 使用 Jinja2 模板引擎 + Tailwind CSS 构建可视化界面
- 通过 `authlib` 实现 GitHub 和 Google OAuth 登录

**爬虫服务模块** (`trendradar/crawler/` - 现有)
- 保持现有架构，继续抓取新闻数据
- 新增用户配置读取逻辑，从数据库获取所有用户的关键词配置
- 根据每个用户的关键词过滤新闻，调用推送服务

**推送服务模块** (`trendradar/notification/` - 现有，增强)
- 扩展现有的多渠道推送能力
- 新增用户配额检查机制
- 记录推送历史，支持每日配额统计

### 1.2 数据流

```
1. 爬虫抓取新闻 → 存储到 PostgreSQL（共享新闻数据）
2. 爬虫读取用户配置 → 按用户关键词过滤 → 调用推送服务
3. 用户通过 Web 页面配置 → 存储到 PostgreSQL（用户隔离）
```

### 1.3 部署架构

使用 Docker Compose 编排三个容器：
- **PostgreSQL 容器**：存储用户数据、新闻数据
- **Web 容器**：FastAPI + Nginx（反向代理）
- **Crawler 容器**：定时执行爬虫任务

---

## 2. 数据库设计

### 2.1 核心表结构

#### users 表（用户信息）

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    avatar_url TEXT,
    provider VARCHAR(20) NOT NULL,  -- 'github' or 'google'
    provider_id VARCHAR(255) NOT NULL,
    tier VARCHAR(20) DEFAULT 'free',  -- 'free' or 'premium'
    daily_push_limit INTEGER DEFAULT 10,  -- 免费10次，付费100次
    keyword_limit INTEGER DEFAULT 50,  -- 免费50个，付费500个
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_provider ON users(provider, provider_id);
```

#### user_configs 表（用户配置）

```sql
CREATE TABLE user_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    report_mode VARCHAR(20) DEFAULT 'daily',  -- 'daily', 'current', 'incremental'
    timezone VARCHAR(50) DEFAULT 'Asia/Shanghai',
    push_window_enabled BOOLEAN DEFAULT false,
    push_window_start TIME,
    push_window_end TIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

CREATE INDEX idx_user_configs_user_id ON user_configs(user_id);
```

#### keywords 表（用户关键词）

```sql
CREATE TABLE keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    group_order INTEGER DEFAULT 0,
    is_required BOOLEAN DEFAULT false,  -- 是否为必须词（+）
    is_filtered BOOLEAN DEFAULT false,  -- 是否为过滤词（!）
    max_count INTEGER DEFAULT 0,  -- 数量限制（@N）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_keywords_user_id ON keywords(user_id);
CREATE INDEX idx_keywords_group_order ON keywords(user_id, group_order);
```

#### notification_channels 表（推送渠道）

```sql
CREATE TABLE notification_channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel_type VARCHAR(20) NOT NULL,  -- 'feishu', 'telegram', 'dingtalk', 'email', etc.
    config JSONB NOT NULL,  -- 存储不同渠道的配置
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notification_channels_user_id ON notification_channels(user_id);
```

#### push_history 表（推送历史）

```sql
CREATE TABLE push_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel_type VARCHAR(50) NOT NULL,
    content_count INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL,  -- 'success' or 'failed'
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_push_history_user_id_created ON push_history(user_id, created_at);
```

#### news_data 表（新闻数据，共享）

```sql
CREATE TABLE news_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    platform VARCHAR(50) NOT NULL,
    url TEXT,
    rank INTEGER,
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date DATE NOT NULL
);

CREATE INDEX idx_news_data_date ON news_data(date);
CREATE INDEX idx_news_data_platform ON news_data(platform, date);
```

### 2.2 数据库迁移

使用 Alembic 进行数据库版本管理和迁移：

```bash
# 初始化 Alembic
alembic init alembic

# 创建迁移脚本
alembic revision --autogenerate -m "Initial schema"

# 执行迁移
alembic upgrade head
```

---

## 3. 用户认证与授权

### 3.1 OAuth 认证流程

使用 `authlib` 集成 GitHub 和 Google OAuth：

**认证流程**：
1. 用户点击"GitHub 登录"或"Google 登录"
2. 重定向到 OAuth 提供商授权页面
3. 用户授权后，回调到 `/auth/callback/{provider}`
4. 验证 OAuth token，获取用户信息
5. 检查用户是否存在：
   - 新用户：创建账户，默认为 free 等级
   - 老用户：更新登录时间和用户信息
6. 生成 JWT token，设置到 HttpOnly Cookie
7. 重定向到用户配置页面

### 3.2 JWT Token 设计

```python
payload = {
    "user_id": str(user.id),
    "email": user.email,
    "tier": user.tier,
    "exp": datetime.utcnow() + timedelta(days=7)
}
```

### 3.3 会话管理

- Token 存储在 HttpOnly Cookie（防止 XSS）
- 有效期 7 天，过期后需要重新登录
- 提供 `/auth/logout` 退出登录

### 3.4 依赖注入中间件

```python
# FastAPI 依赖注入
async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(401, "未登录")
    payload = decode_jwt(token)
    user = db.get(User, payload["user_id"])
    if not user or not user.is_active:
        raise HTTPException(401, "用户不存在或已禁用")
    return user
```

### 3.5 权限控制

```python
# 保护需要登录的路由
@app.get("/api/config")
async def get_config(user: User = Depends(get_current_user)):
    return {"mode": user.config.report_mode}

# 等级检查
def require_tier(tier: str):
    async def check_tier(user: User = Depends(get_current_user)):
        if user.tier != tier:
            raise HTTPException(403, "需要升级账户")
    return check_tier
```

---

## 4. Web API 与用户界面

### 4.1 REST API 设计

**认证相关**
```
GET  /auth/login/{provider}    # 重定向到 OAuth 授权页
GET  /auth/callback/{provider}  # OAuth 回调
POST /auth/logout              # 退出登录
GET  /api/me                   # 获取当前用户信息
```

**用户配置**
```
GET    /api/config              # 获取用户配置
PUT    /api/config              # 更新用户配置
```

**关键词管理**
```
GET    /api/keywords            # 获取关键词列表
POST   /api/keywords            # 添加关键词
PUT    /api/keywords/{id}       # 更新关键词
DELETE /api/keywords/{id}       # 删除关键词
POST   /api/keywords/import     # 批量导入
```

**推送渠道管理**
```
GET    /api/channels            # 获取推送渠道列表
POST   /api/channels            # 添加推送渠道
PUT    /api/channels/{id}       # 更新渠道配置
DELETE /api/channels/{id}       # 删除渠道
POST   /api/channels/{id}/test  # 测试推送
```

**使用统计**
```
GET    /api/stats/usage         # 获取使用统计
GET    /api/stats/history       # 获取推送历史
```

### 4.2 用户界面设计

**页面结构**（使用 Jinja2 + Tailwind CSS）：

**登录页** (`/login`)
- GitHub 和 Google 登录按钮
- 简洁的引导文案

**配置首页** (`/` - 需要登录)
- 顶部导航栏：用户信息、配额显示、退出登录
- 标签页式布局：
  - **关键词配置**
  - **推送渠道**
  - **报告设置**
  - **使用统计**

**关键词配置页**
- 词组卡片展示
- 拖拽排序
- 实时预览匹配效果
- 语法提示（+、!、@ 符号说明）

**推送渠道页**
- 渠道卡片（Feishu、Telegram 等）
- 添加渠道时的模态框表单
- 一键测试按钮

**前端交互**（使用 Alpine.js 或 HTMX）：
- 表单提交使用 AJAX，无需刷新
- 实时验证
- 友好的错误提示

---

## 5. 爬虫服务多用户集成

### 5.1 配置读取层

新增数据库配置读取器 (`trendradar/core/database_config.py`)：

```python
class DatabaseConfigReader:
    """从数据库读取所有用户的配置"""

    def get_all_active_users(self, db: Session) -> List[UserConfig]:
        """获取所有激活用户的配置"""
        return db.query(User).filter(User.is_active == True).all()

    def get_user_keywords(self, user_id: UUID, db: Session) -> List[Keyword]:
        """获取用户的关键词配置"""
        return db.query(Keyword).filter(
            Keyword.user_id == user_id
        ).order_by(Keyword.group_order).all()

    def get_user_channels(self, user_id: UUID, db: Session) -> List[NotificationChannel]:
        """获取用户的推送渠道"""
        return db.query(NotificationChannel).filter(
            NotificationChannel.user_id == user_id,
            NotificationChannel.enabled == True
        ).all()
```

### 5.2 多用户过滤引擎

扩展 `trendradar/core/analyzer.py`：

```python
def filter_news_for_users(
    news_data: List[News],
    user_configs: List[UserConfig],
    db: Session
) -> Dict[UUID, List[News]]:
    """为每个用户过滤新闻"""
    results = {}

    for user_config in user_configs:
        keywords = db.query(Keyword).filter(
            Keyword.user_id == user_config.user_id
        ).all()

        word_groups = parse_keywords_to_groups(keywords)
        filtered = filter_news_by_keywords(
            news_data, word_groups, user_config.report_mode
        )

        results[user_config.user_id] = filtered

    return results
```

### 5.3 配额检查中间件

新增 `trendradar/notification/quota.py`：

```python
class QuotaChecker:
    """配额检查器"""

    def can_push(self, user_id: UUID, db: Session) -> bool:
        """检查用户是否可以推送"""
        user = db.get(User, user_id)

        if user.tier == "premium":
            return True

        today_start = datetime.now().replace(hour=0, minute=0, second=0)
        count = db.query(PushHistory).filter(
            PushHistory.user_id == user_id,
            PushHistory.created_at >= today_start,
            PushHistory.status == "success"
        ).count()

        return count < user.daily_push_limit

    def record_push(self, user_id: UUID, channel_type: str, count: int, db: Session):
        """记录推送历史"""
        history = PushHistory(
            user_id=user_id,
            channel_type=channel_type,
            content_count=count,
            status="success"
        )
        db.add(history)
```

### 5.4 爬虫执行流程改造

原流程（单用户）：
```python
results = fetch_news()
keywords = load_from_file("frequency_words.txt")
filtered = filter_by_keywords(results, keywords)
send_notification(filtered, config_from_yaml())
```

新流程（多用户）：
```python
results = fetch_news()
user_configs = db_reader.get_all_active_users(db)

for user_config in user_configs:
    if not quota_checker.can_push(user_config.user_id, db):
        continue

    keywords = db_reader.get_user_keywords(user_config.user_id, db)
    channels = db_reader.get_user_channels(user_config.user_id, db)

    filtered = filter_news_by_keywords(results, keywords, user_config.report_mode)

    if filtered:
        dispatcher.dispatch_to_channels(filtered, channels)
        quota_checker.record_push(user_config.user_id, channels[0].type, len(filtered), db)
```

### 5.5 性能优化

- **批量查询**：一次性查询所有用户配置，避免 N+1 查询
- **异步推送**：使用 `asyncio` 并发推送到不同渠道
- **缓存机制**：缓存用户配置 5 分钟，避免频繁查询数据库

---

## 6. 部署与运维

### 6.1 Docker Compose 配置

```yaml
services:
  postgres:
    image: postgres:16
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

  web:
    build: .
    command: uvicorn trendradar.web.app:app --host 0.0.0.0 --port 8000
    environment:
      DATABASE_URL: postgresql://trendradar:${DB_PASSWORD}@postgres/trendradar
      GITHUB_CLIENT_ID: ${GITHUB_CLIENT_ID}
      GITHUB_CLIENT_SECRET: ${GITHUB_CLIENT_SECRET}
      GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID}
      GOOGLE_CLIENT_SECRET: ${GOOGLE_CLIENT_SECRET}
      JWT_SECRET: ${JWT_SECRET}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  crawler:
    build: .
    command: python -m trendradar.crawler.scheduler
    environment:
      DATABASE_URL: postgresql://trendradar:${DB_PASSWORD}@postgres/trendradar
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./output:/app/output

volumes:
  postgres_data:
```

### 6.2 环境变量

创建 `.env` 文件：
```bash
# 数据库
DB_PASSWORD=your_secure_password

# OAuth
GITHUB_CLIENT_ID=xxx
GITHUB_CLIENT_SECRET=xxx
GOOGLE_CLIENT_ID=xxx
GOOGLE_CLIENT_SECRET=xxx
OAUTH_REDIRECT_URI=http://localhost:8000/auth/callback

# JWT
JWT_SECRET=your_random_secret_key

# 应用
TZ=Asia/Shanghai
LOG_LEVEL=INFO
```

### 6.3 错误处理

**API 错误处理**
```python
@app.exception_handler(AuthException)
async def auth_exception_handler(request: Request, exc: AuthException):
    return JSONResponse(
        status_code=401,
        content={"error": exc.message}
    )

@app.exception_handler(QuotaExceededException)
async def quota_exception_handler(request: Request, exc: QuotaExceededException):
    return JSONResponse(
        status_code=429,
        content={"error": "今日推送配额已用完"}
    )
```

**爬虫错误处理**
- 单个用户推送失败不影响其他用户
- 失败记录到 `push_history`，status = 'failed'
- 重试机制：失败后 5 分钟重试一次，最多 3 次

### 6.4 日志系统

**日志分级**：
- INFO: 用户登录、配置修改、推送成功
- WARNING: 配额接近上限、推送重试
- ERROR: 推送失败、数据库错误
- CRITICAL: 服务无法启动

**日志输出**：
- 控制台：INFO 及以上（Docker logs）
- 文件：ERROR 及以上（`logs/error.log`）

### 6.5 数据备份

- 每天凌晨 3 点自动备份到 `backups/` 目录
- 保留最近 7 天的备份
- 提供恢复脚本 `restore_backup.sh`

---

## 7. 依赖更新

### 7.1 新增依赖

更新 `pyproject.toml`：
```toml
dependencies = [
    # ... 现有依赖
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.12.0",
    "psycopg2-binary>=2.9.0",
    "authlib>=1.2.0",
    "requests-oauthlib>=1.3.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.0",
    "jinja2>=3.1.0",
    "alpinejs>=3.12.0",
]
```

---

## 8. 实施计划

### 8.1 开发阶段

1. **阶段一：基础设施**（2周）
   - 设置 PostgreSQL 数据库
   - 实现用户认证系统（OAuth + JWT）
   - 创建数据库模型和迁移脚本

2. **阶段二：Web 服务**（2周）
   - 实现 REST API 端点
   - 创建用户界面（Jinja2 模板）
   - 实现关键词和渠道管理功能

3. **阶段三：爬虫集成**（1周）
   - 改造爬虫支持多用户配置
   - 实现配额检查机制
   - 批量推送功能

4. **阶段四：测试与部署**（1周）
   - 单元测试和集成测试
   - Docker Compose 部署测试
   - 性能优化

### 8.2 文件结构

```
trendradar/
├── web/                          # 新增 Web 服务
│   ├── __init__.py
│   ├── app.py                    # FastAPI 应用
│   ├── routers/                  # API 路由
│   ├── templates/                # Jinja2 模板
│   └── static/                   # 静态文件
├── core/
│   ├── database_config.py        # 新增：数据库配置读取
│   └── ...
├── notification/
│   └── quota.py                  # 新增：配额检查
├── crawler/
│   └── scheduler.py              # 新增：定时调度器
└── models/                       # 新增：数据库模型
    ├── __init__.py
    ├── user.py
    ├── keyword.py
    └── ...
```

---

## 9. 风险与挑战

### 9.1 技术风险

- **OAuth 集成复杂度**：需要正确处理回调、token 管理
- **数据库性能**：多用户并发查询可能影响性能
- **爬虫稳定性**：单个用户配置错误不应影响其他用户

### 9.2 缓解措施

- 使用成熟的 `authlib` 库简化 OAuth 集成
- 实现数据库连接池和查询缓存
- 完善的错误处理和隔离机制
- 充分的日志记录便于排查问题

---

## 10. 后续优化

### 10.1 功能扩展

- 支持更多 OAuth 提供商（如微信、QQ）
- 实现支付集成（支持升级到 premium）
- 添加邮件通知功能
- 实现用户数据导出功能

### 10.2 性能优化

- 实现 Redis 缓存层
- 数据库读写分离
- 爬虫分布式部署

### 10.3 监控与运维

- 实现 Prometheus 监控
- 添加 Grafana 可视化面板
- 自动化部署脚本（CI/CD）

---

## 附录

### A. 参考资料

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Authlib 文档](https://docs.authlib.org/)
- [Alembic 文档](https://alembic.sqlalchemy.org/)
- [Tailwind CSS 文档](https://tailwindcss.com/)

### B. OAuth 申请指南

**GitHub OAuth**
1. 访问 https://github.com/settings/developers
2. 新建 OAuth App
3. 设置回调 URL：`http://localhost:8000/auth/callback/github`

**Google OAuth**
1. 访问 https://console.cloud.google.com/
2. 创建 OAuth 2.0 客户端 ID
3. 设置回调 URL：`http://localhost:8000/auth/callback/google`

---

**文档版本**: 1.0
**最后更新**: 2025-01-02
