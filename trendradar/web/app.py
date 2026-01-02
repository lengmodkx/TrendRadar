# coding=utf-8
"""
TrendRadar Web 应用主入口
"""

from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import os

from trendradar.models.base import engine, Base
from trendradar.web.routers import auth, admin
from trendradar.web.auth.dependencies import get_current_user, get_optional_user
from trendradar.models.user import User

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

# Session 中间件 (用于 OAuth 流程)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("JWT_SECRET", "your-secret-key-change-this"),
    max_age=None,
    session_cookie="session_id",
)

# 包含路由
app.include_router(auth.router)
app.include_router(admin.router)

# 静态文件和模板
templates = Jinja2Templates(directory="trendradar/web/templates")
app.mount("/static", StaticFiles(directory="trendradar/web/static"), name="static")


# 事件处理器
@app.on_event("startup")
async def startup_event():
    """应用启动时创建数据库表"""
    import sys
    try:
        # Test bcrypt at startup
        import bcrypt
        print(f"DEBUG startup: bcrypt module = {bcrypt}", file=sys.stderr)
        print(f"DEBUG startup: bcrypt.hashpw = {bcrypt.hashpw}", file=sys.stderr)
        test_hash = bcrypt.hashpw(b'test', bcrypt.gensalt())
        print(f"DEBUG startup: bcrypt test successful", file=sys.stderr)
    except Exception as e:
        print(f"DEBUG startup: bcrypt test failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)

    try:
        Base.metadata.create_all(bind=engine)
        print("数据库表创建完成")
    except Exception as e:
        print(f"警告: 数据库连接失败，服务将以无数据库模式启动: {e}")
        print("提示: 请检查数据库配置或稍后初始化数据库表")


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "message": "TrendRadar Web 服务运行正常"
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, current_user: User = Depends(get_optional_user)):
    """首页"""
    if not current_user:
        # 未登录，显示登录页
        return templates.TemplateResponse("login.html", {"request": request})

    # 已登录，显示配置页（稍后实现）
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": current_user})


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    import traceback
    import sys
    import os
    import bcrypt as bc

    # Print full traceback to stderr
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
    print(f"Request URL: {request.url}", file=sys.stderr)
    print(f"Request Method: {request.method}", file=sys.stderr)
    print(f"bcrypt module: {bc}", file=sys.stderr)
    print(f"bcrypt has hashpw: {hasattr(bc, 'hashpw')}", file=sys.stderr)
    print(f"bcrypt file: {bc.__file__ if hasattr(bc, '__file__') else 'N/A'}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    print(f"{'='*60}\n", file=sys.stderr)

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
