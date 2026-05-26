"""重点研究代理的错误处理节点。

该模块包含 LangGraph 工作流程的终端错误节点。
每当任何上游节点记录时，都会通过条件路由到达它
状态错误。它记录所有收集的错误并设置最终状态
到“错误”，以便应用程序层可以返回结构化错误响应
到传输层。

该节点永远不会引发 - 它总是返回部分状态更新，因此
无论哪个节点发生故障，图都可以干净地完成。"""

import logging

from focused_research_agent.state import ResearchState

logger = logging.getLogger(__name__)


def handle_error(state: ResearchState) -> dict:
    """终端错误节点。记录所有记录的错误和标记
    运行失败。通过条件路由到达
    任何上游节点都会记录错误。"""
    errors = state.get("errors") or []
    for error in errors:
        logger.error(error)
    return {"status": "error"}
