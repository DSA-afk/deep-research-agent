"""运行重点研究代理的初始化节点。

该模块包含 LangGraph 研究工作流程的入口节点。
它生成一个唯一的运行 ID 并验证用户问题是否存在
在任何其他节点执行之前。如果没有找到问题，则出现错误
记录在状态中，并且图表路由到handle_error。"""

import logging
import uuid

from focused_research_agent.state import ResearchState

logger = logging.getLogger(__name__)


def initialize_state(state: ResearchState) -> dict:
    """启动新的研究运行。生成唯一的运行 ID
    并验证是否已提供问题。"""
    run_id = str(uuid.uuid4())
    user_query = (state.get("question") or "").strip()
    errors = []

    if not user_query:
        logger.error("init_run: No question provided")
        errors.append("init_run: No question provided")
    else:
        logger.info(
            "Research run started. run_id=%s question='%s'", run_id, user_query[:50]
        )

    return {
        "run_id": run_id,
        "status": "started",
        "errors": errors,
    }
