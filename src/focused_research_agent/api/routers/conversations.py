"""Focused Research Agent API 的对话历史记录端点。

该模块公开用于获取对话的只读 HTTP 端点
历史。聊天 UI 使用它来填充侧边栏历史记录
面板并在选择时重新加载完整对话。

从架构上来说，该模块属于传输层。它留下来
瘦——没有业务逻辑，没有图形调用。它从数据库中读取
通过依赖注入会话通过存储库层。"""

from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from focused_research_agent.database.database import get_db
from focused_research_agent.database.repository import (
    get_all_conversations,
    get_conversation_turns,
)

conversations_router = APIRouter(tags=["conversations"])


@conversations_router.get("/conversations", status_code=status.HTTP_200_OK)
def get_conversations(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    """返回所有对话的摘要列表。

    每个对话返回一个条目，显示对话 ID，
    来自第一个问题的标题和创建时间戳。
    先订购最新的。

    参数：
        db：注入的 SQLAlchemy 数据库会话。

    返回：
        list[dict]：包含以下内容的对话摘要字典列表
            对话id、标题和created_at键。"""
    return get_all_conversations(db)


@conversations_router.get(
    "/conversations/{conversation_id}", status_code=status.HTTP_200_OK
)
def get_conversation(
    conversation_id: str, db: Annotated[Session, Depends(get_db)]
) -> list[dict]:
    """按时间顺序返回特定对话的所有回合。

    返回每个回合的完整研究数据，包括反序列化的
    查询、来源、引用和错误。用于重新加载完整的
    对话进入聊天 UI。

    参数：
        Conversation_id：标识会话的 UUID 字符串。
        db：注入的 SQLAlchemy 数据库会话。

    返回：
        list[dict]：按时间顺序排列的完整字典列表。
            如果对话不存在，则列表为空。"""
    return get_conversation_turns(db, conversation_id)


@conversations_router.get(
    "/reports",
    status_code=status.HTTP_200_OK,
)
def get_reports(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    """返回报告历史记录的所有报告运行的摘要列表
    侧边栏。

    参数：
        db：注入的 SQLAlchemy 数据库会话。

    返回：
        list[dict]：报告摘要字典列表，包含
            对话id、标题和created_at键。"""
    from focused_research_agent.database.repository import get_all_reports

    return get_all_reports(db)
