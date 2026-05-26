"""Focused Research Agent API 的集中式 FastAPI 异常处理程序。

该模块包含 API 的 HTTP 特定异常处理逻辑
层。它转换共享应用程序异常和意外运行时
将异常转化为一致的 HTTP JSON 错误响应。

从架构上来说，该模块属于 API 层，因为格式化
异常，因为 HTTP 响应是一个传输问题，而不是应用程序或
工作流程问题。"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from focused_research_agent.application.exceptions import ApplicationError

logger = logging.getLogger("focused_research_agent.api.exception_handlers")


def _build_error_response(
    status_code: int,
    error: str,
    detail: str,
    path: str,
) -> JSONResponse:
    """为 API 层构建一致的 JSON 错误响应。

    参数：
        status_code：要返回的 HTTP 状态代码。
        错误：短错误类别标签。
        详细信息：人类可读的错误详细信息。
        path：发生错误的请求路径。

    返回：
        JSONResponse：结构化 JSON 错误响应。"""
    return JSONResponse(
        status_code=status_code,
        content={
            "status_code": status_code,
            "error": error,
            "detail": detail,
            "path": path,
        },
    )


def handle_application_error(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """将应用程序层错误转换为 HTTP 400 响应。

    该处理程序是专门为 ApplicationError 注册的，即使
    异常参数类型为 Exception 以满足 FastAPI 更广泛的要求
    异常处理程序输入期望。

    参数：
        request：传入FastAPI请求对象。
        exc：应用程序/用例执行期间引发的异常。

    返回：
        JSONResponse：描述处理的结构化 HTTP 400 响应
        应用程序错误。"""
    return _build_error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        error="application_error",
        detail=str(exc),
        path=str(request.url.path),
    )


def handle_unexpected_exception(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """将意外的服务器端异常转换为 HTTP 500 响应。

    参数：
        request：传入FastAPI请求对象。
        exc：意外的异常冒泡到 API 边界。

    返回：
        JSONResponse：带有安全一般错误的结构化 HTTP 500 响应
        消息。"""
    logger.exception("Unexpected API error on path %s", request.url.path)

    return _build_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error="internal_server_error",
        detail="An unexpected internal error occurred",
        path=str(request.url.path),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """在 FastAPI 应用程序上注册集中式异常处理程序。

    参数：
        app：FastAPI应用程序实例。

    返回：
        无"""
    app.add_exception_handler(ApplicationError, handle_application_error)
    app.add_exception_handler(Exception, handle_unexpected_exception)
