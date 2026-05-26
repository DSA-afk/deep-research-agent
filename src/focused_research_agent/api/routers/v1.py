"""重点研究代理的版本化 API 路由器分组。

该模块定义了 version-1 API 命名空间并附加了版本控制
共享前缀下的功能路由器。它将 API 版本控制作为一种传输
层关注并避免直接将版本前缀硬编码到每个层中
特色路线。

从架构上来说，该模块属于 API 层，因为版本化的路由
分组是一个 HTTP/API 契约问题，而不是一个应用程序、工作流程或
提供商的关注。"""

from fastapi import APIRouter

from focused_research_agent.api.routers.research import research_router
from focused_research_agent.api.routers.chat import chat_router
from focused_research_agent.api.routers.conversations import conversations_router
from focused_research_agent.api.routers.report import report_router


def create_v1_router() -> APIRouter:
    """构建版本 1 API 路由器组。

    此函数创建一个具有共享“/api/v1”前缀的 API 路由器，并且
    在该命名空间下安装版本化的功能路由器。

    返回：
        APIRouter：版本 1 分组 API 路由器。"""
    router = APIRouter(prefix="/api/v1")
    router.include_router(research_router)
    router.include_router(chat_router)
    router.include_router(conversations_router)
    router.include_router(report_router)
    return router


api_v1_router = create_v1_router()
