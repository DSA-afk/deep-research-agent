"""重点研究代理的研究 API 端点。

该模块公开了研究用例的 HTTP 端点。它接收
验证API输入，通过以下方式将执行转发到应用层
FastAPI 依赖关系连接，并将结果响应作为
HTTP 响应。

从架构上来说，该模块属于传输层。路由器是
传输适配器并应保持薄型。它们不应包含工作流程
编排或特定于提供商的逻辑。"""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, status

from focused_research_agent.api.dependencies import get_research_use_case
from focused_research_agent.api.schemas.research import research as research_schema


research_router = APIRouter(tags=["research"])


@research_router.post(
    "/research",
    status_code=status.HTTP_200_OK,
    response_model=research_schema.ResearchResponse,
)
def research(
    search: research_schema.ResearchRequest,
    run_research_use_case: Annotated[
        Callable[[str], dict],
        Depends(get_research_use_case),
    ],
) -> dict:
    """通过 API 处理研究请求。

    该端点接受经过验证的研究请求，获取
    通过依赖注入应用层研究用例，
    根据用户的问题执行该用例，并返回
    结构化的研究结果。

    参数：
        搜索：经过验证的研究请求有效负载。
        run_research_use_case：执行的注入可调用
            研究用例。

    返回：
        dict：应用程序返回的结构化研究响应
        层。"""
    search_result = run_research_use_case(search.question)
    return search_result
