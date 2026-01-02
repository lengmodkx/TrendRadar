-- TrendRadar 多用户系统数据库初始化脚本
-- 使用方法: psql -h 103.36.221.226 -U postgres -d trendradar -f scripts/init_schema.sql
-- 或者先连接数据库: psql -h 103.36.221.226 -U postgres -d trendradar
-- 然后执行: \i scripts/init_schema.sql

-- 创建数据库（如果不存在）
-- CREATE DATABASE trendradar;

-- 切换到 trendradar 数据库
\c trendradar

-- 启用 UUID 扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- 1. 创建 users 表（用户表）
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    avatar_url VARCHAR(500),
    provider VARCHAR(20) NOT NULL,
    provider_id VARCHAR(255) NOT NULL,
    tier VARCHAR(20) NOT NULL DEFAULT 'free',
    daily_push_limit INTEGER NOT NULL DEFAULT 10,
    keyword_limit INTEGER NOT NULL DEFAULT 50,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

-- 创建索引
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
CREATE INDEX IF NOT EXISTS ix_users_provider ON users(provider, provider_id);

-- 添加注释
COMMENT ON TABLE users IS '用户表';
COMMENT ON COLUMN users.id IS '用户唯一标识';
COMMENT ON COLUMN users.email IS '用户邮箱';
COMMENT ON COLUMN users.name IS '用户姓名';
COMMENT ON COLUMN users.avatar_url IS '头像URL';
COMMENT ON COLUMN users.provider IS 'OAuth提供商（github/google）';
COMMENT ON COLUMN users.provider_id IS 'OAuth提供商的用户ID';
COMMENT ON COLUMN users.tier IS '用户等级（free/premium）';
COMMENT ON COLUMN users.daily_push_limit IS '每日推送限制';
COMMENT ON COLUMN users.keyword_limit IS '关键词数量限制';
COMMENT ON COLUMN users.is_active IS '账户是否激活';

-- ============================================
-- 2. 创建 user_configs 表（用户配置表）
-- ============================================
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

COMMENT ON TABLE user_configs IS '用户配置表';
COMMENT ON COLUMN user_configs.report_mode IS '报告模式（daily/current/incremental）';
COMMENT ON COLUMN user_configs.timezone IS '时区';
COMMENT ON COLUMN user_configs.push_window_enabled IS '是否启用推送时间窗口';
COMMENT ON COLUMN user_configs.push_window_start IS '推送窗口开始时间（HH:MM）';
COMMENT ON COLUMN user_configs.push_window_end IS '推送窗口结束时间（HH:MM）';

-- ============================================
-- 3. 创建 keywords 表（关键词表）
-- ============================================
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

COMMENT ON TABLE keywords IS '用户关键词表';
COMMENT ON COLUMN keywords.content IS '关键词内容';
COMMENT ON COLUMN keywords.group_order IS '分组序号';
COMMENT ON COLUMN keywords.is_required IS '是否为必须词（+）';
COMMENT ON COLUMN keywords.is_filtered IS '是否为过滤词（!）';
COMMENT ON COLUMN keywords.max_count IS '数量限制（@N），0表示不限制';

-- ============================================
-- 4. 创建 notification_channels 表（推送渠道表）
-- ============================================
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

COMMENT ON TABLE notification_channels IS '推送渠道表';
COMMENT ON COLUMN notification_channels.channel_type IS '渠道类型（feishu/telegram/dingtalk/email等）';
COMMENT ON COLUMN notification_channels.config IS '渠道配置（JSON格式）';

-- ============================================
-- 5. 创建 push_history 表（推送历史表）
-- ============================================
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

COMMENT ON TABLE push_history IS '推送历史表';
COMMENT ON COLUMN push_history.channel_type IS '渠道类型';
COMMENT ON COLUMN push_history.content_count IS '推送内容数量';
COMMENT ON COLUMN push_history.status IS '推送状态（success/failed）';
COMMENT ON COLUMN push_history.error_message IS '错误信息';

-- ============================================
-- 创建更新时间触发器（可选）
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为需要的表添加触发器
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_configs_updated_at BEFORE UPDATE ON user_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_notification_channels_updated_at BEFORE UPDATE ON notification_channels
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 插入测试数据（可选）
-- ============================================
-- 插入一个测试用户（密码测试使用）
INSERT INTO users (email, name, provider, provider_id, tier)
VALUES ('test@example.com', '测试用户', 'github', '12345', 'free')
ON CONFLICT (email) DO NOTHING;

-- 为测试用户创建默认配置
INSERT INTO user_configs (user_id, report_mode, timezone)
SELECT id, 'daily', 'Asia/Shanghai'
FROM users
WHERE email = 'test@example.com'
ON CONFLICT (user_id) DO NOTHING;

-- ============================================
-- 显示创建的表
-- ============================================
SELECT 'Database initialization completed!' AS status;
SELECT 'Tables created:' AS info;

\d users
\d user_configs
\d keywords
\d notification_channels
\d push_history
