"""Focused Research Agent 的聊天 API 端点。

本模块公开面向对话感知研究的 HTTP 端点。
它接收经过验证的聊天请求，获取数据库会话，
通过依赖注入执行聊天示例，并返回重构的聊天响应。

从架构层面看，本模块属于传输层。它保持专业 —
不包含业务逻辑、不执行数据库查询，也不调用图工作流程。
它通过execute_chat_turn将所有工作委托给应用层。"""

from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from focused_research_agent.api.schemas.chat.chat import ChatRequest, ChatResponse
from focused_research_agent.database.database import get_db
from focused_research_agent.api.dependencies import get_chat_use_case
from collections.abc import Callable

chat_router = APIRouter(tags=["chat"])


@chat_router.post("/chat", status_code=status.HTTP_200_OK, response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Annotated[Session, Depends(get_db)],
    run_chat_use_case: Annotated[Callable, Depends(get_chat_use_case)],
) -> dict:
    """通过API处理聊天研究请求。

    接受包含问题和可选对话id的经过验证的聊天请求，
    执行对话采集研究示例，并返回包含会话元数据的格式化结果。

    参数：
        request: 已验证的聊天请求负载。
        db:注入的SQLAlchemy数据库会话。

    返回：
        dict：应用层返回的协商响应。"""
    return run_chat_use_case(
        db=db,
        conversation_id=request.conversation_id,
        question=request.question,
    )
