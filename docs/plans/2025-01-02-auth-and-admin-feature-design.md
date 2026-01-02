# 认证增强和管理功能设计文档

**日期**: 2025-01-02
**版本**: 1.0
**作者**: TrendRadar Team

## 目标

1. 修复 OAuth 登录功能（GitHub/Google）
2. 添加邮箱注册/登录功能
3. 实现超级管理员功能（superadmin 账号）

---

## 第一部分：数据库模型修改

### users 表新增字段

```python
password_hash: Column(String(255), nullable=True)  # 密码哈希
is_superuser: Column(Boolean, default=False, nullable=False)  # 超级管理员标识
email_verified: Column(Boolean, default=False, nullable=False)  # 邮箱验证状态
```

### 超级管理员账号

- **账号**: `superadmin@trendradar.local`
- **密码**: `lemon2judy`（bcrypt 哈希）
- **创建方式**: Alembic 迁移脚本自动创建
- **权限**:
  - 查看所有用户列表
  - 禁用/启用用户账户
  - 修改用户等级（free/premium）
  - 查看系统统计信息

### 用户类型

1. **OAuth 用户**
   - provider: 'github' 或 'google'
   - provider_id: OAuth 用户 ID
   - password_hash: NULL

2. **邮箱用户**
   - provider: 'email'
   - provider_id: 邮箱地址
   - password_hash: bcrypt 哈希

---

## 第二部分：Session 中间件和 OAuth 修复

### Session 中间件配置

```python
from starlette.middleware.sessions import SessionMiddleware

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("JWT_SECRET"),
    max_age=None,
    session_cookie="session_id",
)
```

### GitHub OAuth 修复

**问题**: 404 错误 - GitHub 不支持 OpenID Connect Discovery

**解决方案**:
```python
oauth.register(
    name='github',
    client_id=GITHUB_CLIENT_ID,
    client_secret=GITHUB_CLIENT_SECRET,
    # 移除 server_metadata_url
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    client_kwargs={'scope': 'user:email'}
)
```

**用户信息获取**:
- API: `https://api.github.com/user`
- API: `https://api.github.com/user/emails`

### Google OAuth 修复

**问题**: SessionMiddleware 错误

**解决方案**:
- 添加 SessionMiddleware 后自动解决
- 保持现有 OpenID Connect Discovery 配置
- Session 存储 OAuth state 参数，防止 CSRF 攻击

---

## 第三部分：用户注册功能

### 注册方式：双轨制

**方式 1: OAuth 注册**
- 用户首次使用 GitHub/Google 登录时自动创建账户
- 回调中已有"查找或创建用户"逻辑

**方式 2: 邮箱注册**
- API: `POST /auth/register`
- 请求体:
  ```json
  {
    "email": "user@example.com",
    "password": "password123",
    "name": "User Name"
  }
  ```

### 验证规则

- 邮箱：唯一性验证，格式验证
- 密码：最少 8 个字符
- 姓名：2-100 字符

### 密码加密

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
hashed_password = pwd_context.hash(password)
```

### 自动登录

- 注册成功后创建 JWT token
- 设置 HttpOnly Cookie
- 重定向到 dashboard

---

## 第四部分：超级管理员功能

### 权限验证

```python
async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="需要超级管理员权限")
    return current_user
```

### 管理 API 端点

#### 1. 查看所有用户
- **路由**: `GET /api/admin/users`
- **权限**: superuser
- **参数**: page, page_size, search, tier, is_active
- **返回**: 分页用户列表

#### 2. 禁用/启用用户
- **路由**: `PUT /api/admin/users/{user_id}/status`
- **权限**: superuser
- **请求体**: `{"is_active": true/false}`
- **限制**: 不能修改其他超级管理员

#### 3. 修改用户等级
- **路由**: `PUT /api/admin/users/{user_id}/tier`
- **权限**: superuser
- **请求体**: `{"tier": "premium"}` 或 `{"tier": "free"}`
- **影响**: 自动更新配额限制

#### 4. 系统统计
- **路由**: `GET /api/admin/stats`
- **权限**: superuser
- **返回**:
  - 总用户数
  - 今日新增用户
  - Free/Premium 分布
  - 今日推送数量
  - 7天活跃用户

---

## 第五部分：登录/注册页面 UI

### 页面布局

```
┌─────────────────────────────┐
│     TrendRadar               │
│   热点新闻聚合与分析工具      │
├─────────────────────────────┤
│                             │
│  [GitHub 登录/注册]         │
│  [Google 登录/注册]         │
│                             │
│  ─── 或 ───                  │
│                             │
│  邮箱: [_______________]     │
│  密码: [_______________]     │
│  姓名: [_______________]     │
│                             │
│  [注册]                      │
│  已有账户？[登录]            │
│                             │
└─────────────────────────────┘
```

### 交互功能

- 使用 Alpine.js 切换登录/注册表单
- 客户端表单验证
- API 错误提示
- 注册成功自动跳转

### 样式

- Tailwind CSS
- 响应式设计
- 现代简洁 UI

---

## 第六部分：密码功能

### 邮箱登录 API

- **路由**: `POST /auth/login`
- **请求**: `{"email": "xxx", "password": "xxx"}`
- **验证**: bcrypt.verify(password, password_hash)
- **返回**: JWT token

### 密码重置（可选扩展）

**流程**:
1. `POST /auth/password/forgot` - 请求重置
   - 输入邮箱
   - 生成重置 token
   - 发送重置链接（跳过邮件，直接返回 token）

2. `POST /auth/password/reset` - 重置密码
   - 输入: token, new_password
   - 验证 token 有效性和过期时间
   - 更新密码

**数据模型**:
```python
password_reset_token: Column(String(255))
password_reset_expires: Column(DateTime)
```

---

## 第七部分：实施计划

### 优先级

#### 阶段一：核心修复（最高优先级）
1. 添加 SessionMiddleware
2. 修复 GitHub OAuth 配置
3. 修复 Google OAuth 配置
4. 测试 OAuth 流程

#### 阶段二：数据库和超级管理员
5. 更新数据库模型
6. 创建 Alembic 迁移
7. 自动创建 superadmin 账号

#### 阶段三：邮箱注册/登录
8. 实现注册 API
9. 实现登录 API
10. 更新登录页面 UI
11. 添加表单验证

#### 阶段四：管理功能
12. 创建管理员依赖
13. 实现用户管理 API
14. 实现统计 API
15. 创建管理后台页面（可选）

### 时间估算

- 阶段一：30-45 分钟
- 阶段二：20-30 分钟
- 阶段三：30-45 分钟
- 阶段四：45-60 分钟

**总计**: 约 2-3 小时

---

## 技术栈

- **认证**: FastAPI + Authlib + JWT
- **密码**: bcrypt (passlib)
- **Session**: Starlette SessionMiddleware
- **前端**: Tailwind CSS + Alpine.js
- **数据库**: PostgreSQL + SQLAlchemy

---

## 安全考虑

1. **密码安全**
   - bcrypt 哈希，工作因子 12
   - 不存储明文密码
   - 密码最少 8 位

2. **OAuth 安全**
   - Session 存储 state 参数
   - State 验证防止 CSRF
   - HttpOnly Cookie

3. **API 安全**
   - 超级管理员权限检查
   - 限流防止暴力破解
   - 输入验证和清理

---

## 后续扩展（可选）

1. **邮箱验证**
   - 发送验证邮件
   - 验证链接

2. **密码重置邮件**
   - SMTP 配置
   - 邮件模板

3. **双因素认证**
   - TOTP
   - 短信验证

4. **OAuth 提供商扩展**
   - GitLab
   - 微信
   - 企业微信

---

## 文件清单

### 需要修改的文件
1. `trendradar/models/user.py` - 添加字段
2. `trendradar/web/app.py` - 添加 SessionMiddleware
3. `trendradar/web/auth/config.py` - 修复 OAuth 配置
4. `trendradar/web/routers/auth.py` - 添加注册/登录 API
5. `trendradar/web/templates/login.html` - 更新 UI
6. `alembic/versions/xxx_add_superuser_and_password.py` - 迁移脚本

### 需要创建的文件
1. `trendradar/web/routers/admin.py` - 管理员 API
2. `trendradar/web/templates/dashboard.html` - 管理后台
3. `trendradar/web/auth/permissions.py` - 权限检查

---

## 总结

本设计方案实现了：
✅ OAuth 登录修复（GitHub + Google）
✅ 邮箱注册/登录功能
✅ 超级管理员账号（superadmin）
✅ 用户管理功能
✅ 系统统计功能

**下一步**: 准备实施了吗？
