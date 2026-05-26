"""Focused Research Agent API 的运行状况检查端点。

该模块定义了用于验证 FastAPI 的轻量级端点
服务正在运行并且可访问。

从架构上来说，路由器是传输适配器。他们应该保持苗条和
处理 HTTP 问题，例如路由、请求/响应映射和状态
代码，同时避免业务逻辑。"""

from fastapi import APIRouter


health_router = APIRouter(tags=["health"])


@health_router.get("/health")
def health() -> dict:
    """返回 API 服务的简单健康状态。

    该端点用于确认FastAPI应用程序已启动
    并能够接收请求。

    返回：
        dict：表示服务正在运行的最小状态负载
            健康。"""
    return {"status": "ok"}
