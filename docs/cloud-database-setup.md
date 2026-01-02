# 云数据库配置指南

本文档介绍如何将 TrendRadar 连接到云 PostgreSQL 数据库。

## 支持的云数据库平台

- ✅ 阿里云 RDS PostgreSQL
- ✅ 腾讯云 PostgreSQL
- ✅ AWS RDS PostgreSQL
- ✅ Google Cloud SQL
- ✅ Supabase
- ✅ Neon
- ✅ 任何标准的 PostgreSQL 数据库

## 快速开始

### 步骤 1: 获取数据库连接信息

从你的云数据库提供商获取以下信息：
- 主机地址 (Host)
- 端口 (Port)，默认 5432
- 数据库名称 (Database)
- 用户名 (Username)
- 密码 (Password)

### 步骤 2: 设置环境变量

创建 `.env` 文件（或复制示例）：

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置 `DATABASE_URL`：

```bash
# 格式: postgresql://username:password@host:port/database

# 示例 1: 阿里云 RDS
DATABASE_URL=postgresql://trendradar:your_password@rm-xxxxx.rds.aliyuncs.com:3433/trendradar

# 示例 2: 腾讯云
DATABASE_URL=postgresql://trendradar:your_password@pg-xxxxx.postgres.tencentcdb.com:5432/trendradar

# 示例 3: AWS RDS
DATABASE_URL=postgresql://trendradar:your_password@xxxxx.xxxx.us-east-1.rds.amazonaws.com:5432/trendradar

# 示例 4: Supabase
DATABASE_URL=postgresql://postgres:your_password@db.xxxx.supabase.co:5432/postgres

# 示例 5: Neon
DATABASE_URL=postgresql://trendradar:your_password@xxxxx.neon.tech:5432/neondb
```

### 步骤 3: 初始化数据库表

**方式 1: 使用初始化脚本（推荐）**

```bash
# 设置环境变量
export DATABASE_URL="你的数据库连接字符串"

# 运行初始化脚本
python scripts/init_database.py
```

**方式 2: 使用 Alembic**

```bash
# 安装依赖
pip install -e .

# 运行迁移
alembic upgrade head
```

**方式 3: 使用 Docker**

```bash
# 在 docker-compose.yml 中配置环境变量
# 然后运行
docker-compose exec web alembic upgrade head
```

## 具体云平台配置示例

### 阿里云 RDS PostgreSQL

1. 登录阿里云控制台
2. 进入 RDS 管理控制台
3. 创建 PostgreSQL 实例（或使用现有实例）
4. 创建数据库账号
5. 设置白名单（添加你的 IP 地址或 0.0.0.0/0）
6. 获取连接信息

```bash
DATABASE_URL=postgresql://trendradar:YourPassword@rm-xxxxx.rds.aliyuncs.com:3433/trendradar
```

### 腾讯云 PostgreSQL

1. 登录腾讯云控制台
2. 进入 PostgreSQL 控制台
3. 创建实例
4. 创建数据库和账号
5. 设置安全组（允许外部访问）
6. 获取连接信息

```bash
DATABASE_URL=postgresql://trendradar:YourPassword@pg-xxxxx.postgres.tencentcdb.com:5432/trendradar
```

### Supabase（免费，推荐测试）

1. 访问 https://supabase.com
2. 创建新项目
3. 获取数据库连接信息（Settings > Database > Connection string）
4. 使用 URI 格式的连接字符串

```bash
# Supabase 提供的连接字符串格式
DATABASE_URL=postgresql://postgres.xxxx:PASSWORD@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres
```

### Neon（免费，推荐开发）

1. 访问 https://neon.tech
2. 创建新项目
3. 获取连接字符串
4. 选择 "Connection string" 格式

```bash
DATABASE_URL=postgresql://trendradar:your_password@xxxxx.neon.tech:5432/neondb
```

## 验证连接

运行以下命令验证数据库连接：

```bash
python -c "from trendradar.models.base import engine; print(f'数据库: {engine.url}'); engine.connect()"
```

或者运行健康检查：

```bash
python scripts/init_database.py
```

## 常见问题

### 1. 连接超时

**原因**: 数据库防火墙或安全组未配置允许外部访问

**解决**:
- 阿里云: 在 RDS > 白名单设置 中添加你的 IP
- 腾讯云: 在安全组 中添加入站规则
- AWS: 在 Security Groups 中添加规则

### 2. 认证失败

**原因**: 用户名或密码错误

**解决**:
- 检查 DATABASE_URL 中的用户名和密码
- 确认数据库用户已创建且有足够权限
- 某些云平台要求使用特定格式的密码

### 3. 数据库不存在

**原因**: 数据库未创建

**解决**:
```sql
-- 连接到数据库服务器后执行
CREATE DATABASE trendradar;
```

### 4. SSL 连接问题

某些云数据库要求 SSL 连接，在连接字符串中添加：

```bash
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

## 性能优化建议

### 连接池配置

在 `trendradar/models/base.py` 中已配置连接池：

```python
engine = create_engine(
    DATABASE_URL,
    pool_size=5,         # 连接池大小
    max_overflow=10,     # 最大溢出连接数
    pool_pre_ping=True,  # 检查连接有效性
)
```

对于高并发场景，可以调整这些参数：

```python
pool_size=20,          # 增加连接池大小
max_overflow=40,       # 增加最大溢出连接数
pool_recycle=3600,     # 1小时后回收连接
```

## 安全建议

1. **不要将 .env 文件提交到 Git**
   - .gitignore 已配置忽略 .env 文件

2. **使用强密码**
   ```bash
   # 生成随机密码
   openssl rand -base64 32
   ```

3. **限制数据库访问**
   - 只允许可信 IP 访问
   - 使用最小权限原则

4. **定期备份**
   - 云数据库通常提供自动备份
   - 可以手动创建快照

## 本地开发使用 Docker（可选）

如果不想使用云数据库，仍然可以使用本地 Docker：

```bash
# 启动本地 PostgreSQL
docker-compose -f docker-compose.dev.yml up -d postgres

# 使用本地数据库
DATABASE_URL=postgresql://trendradar:trendradar_dev_password@localhost:5432/trendradar
```

## 从本地迁移到云数据库

如果你已经在本地开发并想迁移到云数据库：

```bash
# 1. 导出本地数据
pg_dump -h localhost -U trendradar trendradar > backup.sql

# 2. 导入到云数据库
psql -h your-cloud-host -U trendradar -d trendradar < backup.sql

# 3. 更新 .env 文件
DATABASE_URL=postgresql://trendradar:password@cloud-host:5432/trendradar
```

## 监控和日志

查看数据库连接日志：

```bash
# 启用 SQL 日志（开发环境）
export SQLALCHEMY_ECHO=true
python scripts/init_database.py
```

监控数据库性能：
- 使用云平台提供的监控工具
- 查看慢查询日志
- 监控连接数使用情况

## 下一步

数据库配置完成后：

1. ✅ 运行数据库初始化脚本
2. ✅ 配置 OAuth（GitHub/Google）
3. ✅ 启动 Web 服务
4. ✅ 访问 http://localhost:8000

详细步骤请参考 [部署指南](deployment-guide.md)。
