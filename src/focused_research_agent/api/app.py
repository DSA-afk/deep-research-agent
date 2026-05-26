"""重点研究代理的 FastAPI 应用程序入口点。

该模块创建 FastAPI 应用程序实例，注册 API 路由器，以及
注册集中式异常处理程序。它充当 HTTP 入口点
项目并保持应用程序组装逻辑集中。

从架构上来说，这个文件属于传输层。应该重点
应用程序构建和布线，同时将请求处理委托给路由器
以及应用层的用例执行。"""

import logging
from fastapi import FastAPI

from focused_research_agent.api.api_exception_handlers import (
    register_exception_handlers,
)
from focused_research_agent.api.routers.health import health_router
from focused_research_agent.api.routers.v1 import api_v1_router
from focused_research_agent.config.api_config import get_api_settings
from focused_research_agent.database.database import init_db

logger = logging.getLogger(__name__)


def register_routers(app: FastAPI) -> None:
    """在 FastAPI 应用程序上注册所有 API 路由器。

    该函数直接挂载`/health`等操作路由
    通过版本化 API 命名空间挂载业务/API 合约路由。

    参数：
        app：FastAPI应用程序实例。

    返回：
        无"""
    app.include_router(health_router)
    app.include_router(api_v1_router)


def create_app() -> FastAPI:
    """构建并配置 FastAPI 应用程序实例。

    返回：
        FastAPI：配置的 FastAPI 应用程序。"""
    settings = get_api_settings()

    app = FastAPI(
        title=settings.title,
        version=settings.version,
        debug=settings.debug,
    )

    init_db()
    logger.info(
        "Application started. title=%s version=%s debug=%s",
        settings.title,
        settings.version,
        settings.debug,
    )

    register_routers(app)
    register_exception_handlers(app)

    logger.info("Routers and exception handlers registered.")

    return app
