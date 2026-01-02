# coding=utf-8
"""
TrendRadar Web 应用主入口
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.cors import CORSMiddleware
import os

from trendradar.models.base import engine, Base
from trendradar.web.routers import auth
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
