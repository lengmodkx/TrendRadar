# TrendRadar 多用户系统部署指南

## 前置要求

- Docker 和 Docker Compose
- GitHub OAuth App（[申请地址](https://github.com/settings/developers)）
- Google OAuth Client ID（[申请地址](https://console.cloud.google.com/)

## 快速开始

### 1. 安装依赖

首先安装项目依赖：

```bash
pip install -e .
```

### 2. 准备配置文件

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
JWT_SECRET=your_random_secret_key_change_this_in_production
```

生成 JWT 密钥（可选）：

```bash
openssl rand -hex 32
```

### 3. 启动开发环境

启动 PostgreSQL 数据库：

```bash
docker-compose -f docker-compose.dev.yml up -d postgres
```

等待数据库就绪（约 10 秒），然后运行数据库迁移：

```bash
# 设置环境变量（Windows PowerShell）
$env:DATABASE_URL = "postgresql://trendradar:trendradar_dev_password@localhost:5432/trendradar"

# 设置环境变量（Linux/Mac）
export DATABASE_URL="postgresql://trendradar:trendradar_dev_password@localhost:5432/trendradar"

# 运行迁移
alembic upgrade head
```

### 4. 启动 Web 服务

```bash
python -m uvicorn trendradar.web.app:app --reload --host 0.0.0.0 --port 8000
```

### 5. 访问应用

- Web 服务: http://localhost:8000
- API 文档: http://localhost:8000/api/docs
- 健康检查: http://localhost:8000/health

## 生产环境部署

### 1. 使用 Docker Compose

编辑 `.env` 文件，配置生产环境变量：

```bash
DB_PASSWORD=your_production_password
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
JWT_SECRET=your_production_jwt_secret
```

启动所有服务：

```bash
docker-compose up -d
```

查看日志：

```bash
docker-compose logs -f web
```

停止服务：

```bash
docker-compose down
```

### 2. 初始化数据库

进入 Web 容器并运行迁移：

```bash
docker-compose exec web alembic upgrade head
```

### 3. 配置 OAuth 回调 URL

确保 OAuth 应用的回调 URL 配置为：

```
http://your-domain.com/auth/callback/github
http://your-domain.com/auth/callback/google
```

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
docker-compose exec web env | grep -E "(GITHUB|GOOGLE|CLIENT)"
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

## 多用户模式配置

设置环境变量启用多用户模式：

```bash
MULTIUSER_MODE=true
```

在多用户模式下：
- 爬虫会为每个用户根据其关键词配置过滤新闻
- 推送会根据用户配置的渠道和配额进行
- 用户等级（free/premium）决定推送限制

## 开发说明

### 添加新的 API 路由

1. 在 `trendradar/web/routers/` 创建新文件
2. 定义路由和处理器函数
3. 在 `trendradar/web/app.py` 中注册路由

### 数据库迁移

修改模型后创建新迁移：

```bash
alembic revision --autogenerate -m "描述变更"
alembic upgrade head
```

## 安全建议

1. **生产环境必须使用 HTTPS**
2. **定期更新依赖包**：`pip install --upgrade -e .`
3. **使用强密码**：数据库和 JWT 密钥
4. **定期备份数据库**
5. **监控日志异常**

## 许可证

MIT License
