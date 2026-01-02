# 数据库初始化指南

## 数据库连接信息

- **主机地址**: 103.36.221.226
- **端口**: 5432
- **用户名**: postgres
- **密码**: lemon2judy
- **数据库名**: trendradar

## 方式一：使用批处理脚本（Windows - 推荐）

**前置条件**: 需要安装 PostgreSQL 客户端工具（psql）

1. 下载安装 PostgreSQL: https://www.postgresql.org/download/windows/
2. 双击运行 `scripts\init_db.bat`
3. 输入密码: lemon2judy
4. 等待脚本执行完成

## 方式二：使用 Shell 脚本（Linux/Mac - 推荐）

```bash
# 给脚本添加执行权限
chmod +x scripts/init_db.sh

# 运行脚本
./scripts/init_db.sh
```

## 方式三：使用 psql 命令手动执行

### 1. 首先创建数据库

如果数据库 `trendradar` 还不存在，先创建：

```bash
psql -h 103.36.221.226 -U postgres -d postgres
```

输入密码后，在 psql 命令行中执行：

```sql
CREATE DATABASE trendradar;
\q
```

### 2. 执行初始化脚本

```bash
# Windows
psql -h 103.36.221.226 -U postgres -d trendradar -f scripts\init_schema.sql

# Linux/Mac
psql -h 103.36.221.226 -U postgres -d trendradar -f scripts/init_schema.sql
```

## 方式四：使用数据库管理工具（图形界面）

如果你使用图形化数据库管理工具：

### DBeaver

1. 新建连接
   - 主机: 103.36.221.226
   - 端口: 5432
   - 数据库: postgres
   - 用户名: postgres
   - 密码: lemon2judy

2. 打开 SQL 编辑器
3. 复制 `scripts/init_schema.sql` 的内容
4. 点击执行按钮

### pgAdmin

1. 右键 "Databases" -> "Create" -> "Database"
   - 名称: trendradar

2. 选择 trendradar 数据库 -> "Tools" -> "Query Tool"

3. 复制 `scripts/init_schema.sql` 的内容

4. 点击 "Execute/Refresh"

### Navicat / DataGrip / 其他工具

连接信息：
```
Host: 103.36.221.226
Port: 5432
User: postgres
Password: lemon2judy
Database: trendradar
```

然后执行 SQL 脚本。

## 方式五：使用 Python（需要安装依赖）

如果你已经安装了 Python 依赖：

```bash
# 设置环境变量（Windows PowerShell）
$env:DATABASE_URL = "postgresql://postgres:lemon2judy@103.36.221.226:5432/trendradar"

# 设置环境变量（Linux/Mac）
export DATABASE_URL="postgresql://postgres:lemon2judy@103.36.221.226:5432/trendradar"

# 安装依赖
pip install sqlalchemy psycopg2-binary

# 运行初始化脚本
python scripts/init_database.py
```

## 验证表创建

连接到数据库验证表是否创建成功：

```bash
psql -h 103.36.221.226 -U postgres -d trendradar
```

在 psql 中执行：

```sql
-- 查看所有表
\dt

-- 应该看到以下表:
-- users
-- user_configs
-- keywords
-- notification_channels
-- push_history

-- 查看表结构
\d users

-- 查看表数据
SELECT * FROM users;
```

## 常见问题

### 问题 1: 连接超时

```
could not connect to server: Connection timed out
```

**解决**:
1. 检查数据库服务器是否运行
2. 检查防火墙是否开放 5432 端口
3. 检查云服务器安全组是否允许外部访问

### 问题 2: 认证失败

```
FATAL: password authentication failed
```

**解决**:
1. 确认用户名: postgres
2. 确认密码: lemon2judy
3. 检查 pg_hba.conf 配置是否允许密码认证

### 问题 3: 数据库不存在

```
FATAL: database "trendradar" does not exist
```

**解决**: 先创建数据库

```sql
CREATE DATABASE trendradar;
```

### 问题 4: 权限不足

如果执行 SQL 脚本时出现权限错误，确保 postgres 用户有足够权限：

```sql
-- 授予所有权限
GRANT ALL PRIVILEGES ON DATABASE trendradar TO postgres;
```

## 测试数据

脚本会自动插入一个测试用户：

```sql
-- 查看测试用户
SELECT * FROM users WHERE email = 'test@example.com';
```

## 下一步

数据库初始化完成后：

1. ✅ 安装 Python 依赖: `pip install -e .`
2. ✅ 配置 OAuth (GitHub/Google) - 可选
3. ✅ 启动 Web 服务: `python -m uvicorn trendradar.web.app:app --reload`
4. ✅ 访问应用: http://localhost:8000

## 联系方式

如果遇到问题：
1. 检查数据库日志
2. 确认网络连接
3. 查看防火墙设置
