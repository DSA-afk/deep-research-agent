"""重点研究代理的应用程序层聊天用例。

该模块包含用于执行的应用程序级逻辑
对话感知研究用例。它坐在旁边
Research_use_case.py — 同一层，相同模式，但具有
在图执行之前和之后添加对话线程。

在调用图表之前，它会从以下位置获取之前的对话轮次：
SQLite 并在初始状态下填充对话历史记录。
图表返回后，它会将已完成的运行持久保存到 SQLite。

该图本身与单轮研究流程相同。
对话意识完全存在于这一层中
Synthesize_answer 的提示构建 - 不在图形结构中。

从架构上来说，该模块属于应用层。它
协调用例执行，同时保持终端、HTTP 和
数据库关注点不在核心执行路径之外。"""

import uuid
import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from focused_research_agent.application.exceptions import ApplicationError
from focused_research_agent.application.question_validation import (
    validate_and_clean_question,
)
from focused_research_agent.application.research_use_case import (
    make_initial_state,
    normalize_state,
)
from focused_research_agent.database.repository import (
    get_conversation_history,
    save_run,
)
from focused_research_agent.graph import build_graph
from focused_research_agent.state import ResearchState

logger = logging.getLogger(__name__)
MAX_HISTORY_TURNS = 5


def _build_chat_initial_state(
    question: str, conversation_id: str, conversation_history: list[dict] | None
) -> ResearchState:
    """为对话感知的研究运行构建初始图形状态。

    使用对话 ID 和扩展基本初始状态
    上下文线程所需的对话历史字段。

    参数：
        问题：清理的用户研究问题。
        Conversation_id：标识会话的 UUID 字符串。
        对话历史记录：从数据库中获取的先前轮次，
            或无（None）用于新对话的第一轮。

    返回：
        ResearchState：填充对话上下文的初始状态。"""
    state = make_initial_state(question)
    state["conversation_id"] = conversation_id
    state["conversation_history"] = conversation_history
    state["mode"] = "research"
    return state


def execute_chat_turn(db: Session, conversation_id: str | None, question: str) -> dict:
    """执行一轮对话感知研究会话。

    验证问题、解决或创建对话 ID，
    从数据库中获取先前的回合以进行上下文线程，
    调用研究图，保留结果并返回
    附有对话元数据的标准化结果。

    坚持失败并不代表研究成果失败——
    即使保存到
    数据库失败。

    参数：
        问题：本轮的用户研究问题。
        conversation_id：要继续的现有对话 UUID，或者
            没有开始新的对话。
        db：活动 SQLAlchemy 数据库会话。

    返回：
        dict：带有conversation_id和的规范化研究结果
            将turn_number添加到标准研究结果形状中。

    加薪：
        ApplicationError：如果问题验证失败。"""
    try:
        user_query = validate_and_clean_question(question)
    except ValueError as exc:
        raise ApplicationError(str(exc)) from exc

    if conversation_id is None:
        conversation_id = str(uuid.uuid4())  # type: ignore[attr-defined]

    logger.info(
        "Chat turn started. conversation_id=%s turn question='%s'",
        conversation_id,
        user_query[:50],
    )

    conversation_history = get_conversation_history(
        db, conversation_id, MAX_HISTORY_TURNS
    )

    if conversation_history:
        history = conversation_history
    else:
        history = None

    if history is not None:
        turn_number = len(history) + 1
    else:
        turn_number = 1

    graph = build_graph()
    initial_state = _build_chat_initial_state(user_query, conversation_id, history)
    final_state = graph.invoke(initial_state)
    result = normalize_state(final_state, user_query)

    try:
        save_run(db, result, conversation_id, turn_number)
    except SQLAlchemyError:
        logger.exception("Failed to save chat run to database")

    result["conversation_id"] = conversation_id
    result["turn_number"] = turn_number

    logger.info(
        "Chat turn completed. conversation_id=%s turn=%d status=%s",
        conversation_id,
        turn_number,
        result.get("status"),
    )

    return result
