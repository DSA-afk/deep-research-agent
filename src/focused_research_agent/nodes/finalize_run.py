"""运行重点研究代理的最终确定节点。

该模块包含 LangGraph 工作流程的终端成功节点。
它评估最终状态并将运行标记为已完成或
错误基于是否产生答案并且没有记录错误。

仅当两个条件都为真时，运行才会被标记为完成：
- 答案字段是一个非空字符串
- 错误列表为空

任何其他组合都会导致错误状态。该节点始终
成功的图形运行中执行的最后一个节点。"""

import logging
from focused_research_agent.state import ResearchState

logger = logging.getLogger(__name__)


def finalize_run(state: ResearchState) -> dict:
    """根据最终状态将运行标记为已完成或失败。

    参数：
    state：当前的研究状态。

    返回：
    dict：包含最终状态的部分状态更新。"""
    errors = state.get("errors") or []
    answer = (state.get("answer") or "").strip()
    run_id = state.get("run_id", "unknown")

    if errors or not answer:
        logger.error(
            "Run finalized with error. run_id=%s errors=%s",
            run_id,
            errors,
        )
        return {"status": "error"}
    logger.info("Run completed successfully. run_id=%s", run_id)
    return {"status": "completed"}
