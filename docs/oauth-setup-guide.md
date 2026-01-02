# TrendRadar OAuth 和数据库配置指南

## 第一部分：数据库初始化

### 方法 1：使用 pgAdmin（推荐）

1. 打开 pgAdmin 并连接到服务器 103.36.221.226
2. 右键点击 "Databases" → "Create" → "Database"
3. 输入数据库名称：`TrendRadar`
4. 点击 "Save"

然后运行 SQL 脚本：

```sql
-- 启用 UUID 扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 创建 users 表
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    avatar_url VARCHAR(500),
    provider VARCHAR(20) NOT NULL,
    provider_id VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255),
    is_superuser BOOLEAN NOT NULL DEFAULT false,
    email_verified BOOLEAN NOT NULL DEFAULT false,
    tier VARCHAR(20) NOT NULL DEFAULT 'free',
    daily_push_limit INTEGER NOT NULL DEFAULT 10,
    keyword_limit INTEGER NOT NULL DEFAULT 50,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
CREATE INDEX IF NOT EXISTS ix_users_provider ON users(provider, provider_id);

-- 创建 user_configs 表
CREATE TABLE IF NOT EXISTS user_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    report_mode VARCHAR(20) NOT NULL DEFAULT 'daily',
    timezone VARCHAR(50) NOT NULL DEFAULT 'Asia/Shanghai',
    push_window_enabled BOOLEAN NOT NULL DEFAULT false,
    push_window_start VARCHAR(5),
    push_window_end VARCHAR(5),
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_user_configs_user_id ON user_configs(user_id);

-- 创建 keywords 表
CREATE TABLE IF NOT EXISTS keywords (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content VARCHAR(500) NOT NULL,
    group_order INTEGER NOT NULL DEFAULT 0,
    is_required BOOLEAN NOT NULL DEFAULT false,
    is_filtered BOOLEAN NOT NULL DEFAULT false,
    max_count INTEGER DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_keywords_user_id ON keywords(user_id);
CREATE INDEX IF NOT EXISTS ix_keywords_group_order ON keywords(user_id, group_order);

-- 创建 notification_channels 表
CREATE TABLE IF NOT EXISTS notification_channels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel_type VARCHAR(20) NOT NULL,
    config JSONB NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_notification_channels_user_id ON notification_channels(user_id);

-- 创建 push_history 表
CREATE TABLE IF NOT EXISTS push_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel_type VARCHAR(50) NOT NULL,
    content_count INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_push_history_user_id_created ON push_history(user_id, created_at);

-- 创建超级管理员账号
-- 密码: lemon2judy (bcrypt 哈希)
INSERT INTO users (email, name, provider, provider_id, password_hash, is_superuser, email_verified, tier, daily_push_limit, keyword_limit, is_active)
VALUES (
    'lengmodkx@gmail.com',
    'Super Admin',
    'email',
    'lengmodkx@gmail.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzpWMe78Uq',
    true,
    true,
    'premium',
    9999,
    9999,
    true
)
ON CONFLICT (email) DO NOTHING;

-- 为超级管理员创建默认配置
INSERT INTO user_configs (user_id, report_mode, timezone)
SELECT id, 'daily', 'Asia/Shanghai'
FROM users
WHERE email = 'lengmodkx@gmail.com'
ON CONFLICT (user_id) DO NOTHING;
```

### 方法 2：使用命令行

如果你安装了 PostgreSQL 客户端工具：

```bash
# Windows (PowerShell)
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -h 103.36.221.226 -U postgres -d postgres -c "CREATE DATABASE TrendRadar;"
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -h 103.36.221.226 -U postgres -d TrendRadar -f scripts/init_schema.sql
```

## 第二部分：OAuth 配置

### GitHub OAuth 配置

1. 访问 https://github.com/settings/developers
2. 点击 "OAuth Apps" → "New OAuth App"
3. 填写以下信息：
   - **Application name**: `TrendRadar Dev`
   - **Homepage URL**: `http://localhost:8000`
   - **Authorization callback URL**: `http://localhost:8000/auth/callback/github`
   - **Application description**: `TrendRadar Development Environment`
4. 点击 "Register application"
5. 复制 **Client ID**
6. 点击 "Generate a new client secret" 并复制 **Client Secret**

### Google OAuth 配置

1. 访问 https://console.cloud.google.com/
2. 创建新项目或选择现有项目
3. 在左侧菜单中选择 "APIs & Services" → "Credentials"
4. 点击 "Create Credentials" → "OAuth client ID"
5. 如果提示配置同意屏幕，先配置：
   - OAuth consent screen → External → Create
   - 填写应用名称：`TrendRadar Dev`
   - 添加你的邮箱作为测试用户
   - 保存并继续
6. 回到 Credentials 页面，创建 OAuth client ID：
   - **Application type**: Web application
   - **Name**: `TrendRadar Dev`
   - **Authorized redirect URIs**: `http://localhost:8000/auth/callback/google`
7. 点击 "Create"
8. 复制 **Client ID** 和 **Client Secret**

### 更新 .env 文件

将获取的凭据添加到 `.env` 文件：

\`\`\`bash
# GitHub OAuth
GITHUB_CLIENT_ID=your_github_client_id_here
GITHUB_CLIENT_SECRET=your_github_client_secret_here

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
\`\`\`

## 第三部分：测试登录

1. **邮箱登录（超级管理员）**：
   - 邮箱: `lengmodkx@gmail.com`
   - 密码: `lemon2judy`

2. **邮箱注册**：
   - 访问 http://localhost:8000/login
   - 点击 "立即注册"
   - 填写邮箱、姓名和密码

3. **GitHub 登录**：
   - 点击 "使用 GitHub 登录/注册"
   - 授权后自动创建账号

4. **Google 登录**：
   - 点击 "使用 Google 登录/注册"
   - 选择 Google 账号授权

## 常见问题

### Q1: 数据库连接失败
**A**: 检查 `.env` 文件中的 `DATABASE_URL` 是否正确

### Q2: OAuth 回调失败
**A**: 确保 OAuth 应用中的回调 URL 完全匹配，包括协议和端口

### Q3: GitHub OAuth 返回 404
**A**: 检查 `.env` 中的 `GITHUB_CLIENT_ID` 和 `GITHUB_CLIENT_SECRET` 是否已填写

### Q4: Google OAuth 提示缺少 client_id
**A**: 确保 `.env` 中的 `GOOGLE_CLIENT_ID` 已正确填写

### Q5: 无法登录超级管理员账号
**A**: 确保数据库中已创建管理员账号，使用以下 SQL 查询：
\`\`\`sql
SELECT email, is_superuser FROM users WHERE email = 'lengmodkx@gmail.com';
\`\`\`

## 下一步

完成配置后：
1. 重启 TrendRadar 服务
2. 访问 http://localhost:8000/login
3. 使用超级管理员账号登录
4. 测试邮箱注册功能
5. 配置并测试 OAuth 登录
