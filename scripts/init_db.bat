@echo off
REM ============================================
REM TrendRadar 数据库初始化脚本 (Windows)
REM ============================================

echo ============================================
echo  TrendRader 数据库初始化
echo ============================================
echo.
echo 正在连接到数据库: 103.36.221.226
echo 用户: postgres
echo 数据库: TrendRadar
echo.

REM 检查是否安装了 psql
where psql >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到 psql 命令
    echo.
    echo 请先安装 PostgreSQL 客户端工具：
    echo 1. 下载 PostgreSQL: https://www.postgresql.org/download/windows/
    echo 2. 安装后 psql 会自动添加到系统 PATH
    echo.
    pause
    exit /b 1
)

echo [提示] 如果数据库 'TrendRadar' 不存在，请先创建：
echo   CREATE DATABASE TrendRadar;
echo.
echo 按任意键继续初始化数据库...
pause >nul

echo.
echo 正在执行数据库初始化脚本...
echo.

REM 执行 SQL 脚本
psql -h 103.36.221.226 -U postgres -d postgres -f scripts\init_schema.sql

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo  成功！数据库初始化完成
    echo ============================================
    echo.
    echo 已创建的表:
    echo   - users (用户表)
    echo   - user_configs (用户配置表)
    echo   - keywords (关键词表)
    echo   - notification_channels (推送渠道表)
    echo   - push_history (推送历史表)
    echo.
    echo 下一步:
    echo   1. 配置 OAuth (GitHub/Google)
    echo   2. 启动 Web 服务
    echo   3. 访问 http://localhost:8000
    echo.
) else (
    echo.
    echo ============================================
    echo  失败！数据库初始化出错
    echo ============================================
    echo.
    echo 可能的原因:
    echo   1. 数据库服务器不可达
    echo   2. 用户名或密码错误
    echo   3. 数据库 'TrendRadar' 不存在
    echo.
    echo 请检查:
    echo   - 数据库地址: 103.36.221.226
    echo   - 用户名: postgres
    echo   - 密码: lemon2judy
    echo.
)

pause
