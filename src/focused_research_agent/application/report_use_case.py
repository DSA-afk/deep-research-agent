"""重点研究代理的应用层报告用例。

该模块包含用于执行的应用程序级逻辑
报告生成用例。它位于 Research_use_case.py 旁边
和 chat_use_case.py — 相同的层，相同的模式，但配置为
深入的研究和结构化的长篇输出。

与 Research_use_case.py 的主要区别：
- 在初始状态下设置 mode='report'
- 调用 build_graph(search_depth='advanced') 进行更深入的 Tavily 搜索
- 将完成的报告保存到 SQLite

与 chat_use_case.py 的主要区别：
- 仅单轮 - 无会话线程
- 没有conversation_id管理
- 没有历史记录获取

从架构上来说，该模块属于应用层。它
协调用例执行，同时保持传输、数据库、
和图表关注点完全分开。"""

import logging
import uuid

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
from focused_research_agent.database.repository import save_run
from focused_research_agent.graph import build_graph

logger = logging.getLogger(__name__)


def execute_report(question: str, db: Session) -> dict:
    """执行深入的研究报告生成运行。

    验证问题，构建具有高级搜索深度的图表，
    在报告模式下调用研究工作流程，保留结果，
    并返回标准化结果字典。

    持久化失败不失败报告结果——已完成
    即使保存到数据库失败，也始终返回报告。

    参数：
        问题：报告的用户研究问题。
        db：活动 SQLAlchemy 数据库会话。

    返回：
        dict：带有结构化降价答案的标准化研究结果。

    加薪：
        ApplicationError：如果问题验证失败。"""
    try:
        user_query = validate_and_clean_question(question)
    except ValueError as exc:
        raise ApplicationError(str(exc)) from exc

    logger.info("Report use case started. question='%s'", user_query[:50])

    initial_state = make_initial_state(user_query)
    initial_state["mode"] = "report"

    graph = build_graph(search_depth="advanced")
    final_state = graph.invoke(initial_state)

    result = normalize_state(final_state, user_query)

    try:
        conversation_id = str(uuid.uuid4())
        save_run(db, result, conversation_id, turn_number=1, mode="report")
    except SQLAlchemyError:
        logger.exception("Failed to save report run to database")

    logger.info(  # ← 添加
        "Report use case completed. status=%s run_id=%s",
        result.get("status"),
        result.get("run_id"),
    )
    return result
