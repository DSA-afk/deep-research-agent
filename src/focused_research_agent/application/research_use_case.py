"""重点研究代理的应用层研究用例。

该模块包含用于执行研究的应用程序级逻辑
用例。它位于 CLI、FastAPI 等传输层之间
Streamlit 和底层 LangGraph 工作流程。

从架构上讲，应用程序层包含用例/业务逻辑。
它协调研究执行，同时保持终端、HTTP 和其他
将关注点传输到核心执行路径之外。"""

import logging
from focused_research_agent.application.exceptions import ApplicationError
from focused_research_agent.application.question_validation import (
    validate_and_clean_question,
)
from focused_research_agent.graph import build_graph
from focused_research_agent.state import ResearchState

logger = logging.getLogger(__name__)


def _is_list_of_strings(value: object) -> bool:
    """检查值是否是仅包含字符串的列表。

    参数：
        value：要验证的值。

    返回：
        bool：如果值是字符串列表，则为 True，否则为 False。"""
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _is_list_of_dicts(value: object) -> bool:
    """检查值是否是仅包含字典的列表。

    参数：
        value：要验证的值。

    返回：
        bool：如果值是字典列表，则为 True，否则为 False。"""
    return isinstance(value, list) and all(isinstance(item, dict) for item in value)


def normalize_state(final_state: ResearchState, user_query: str) -> dict:
    """将原始图状态标准化为稳定的面向传输的结果形状。

    该函数确保应用层返回一个可预测的
    CLI 和 API 使用者的结构，即使原始图状态
    缺少可选字段或包含格式错误的列表值。

    参数：
        Final_state：LangGraph 工作流程返回的最终状态。
        user_query：已清理的用户问题用作后备值。

    返回：
        dict：规范化的研究结果，包含预期的字段
            传输层。"""
    normalized_state = {
        "run_id": final_state.get("run_id") or "",
        "question": final_state.get("question") or user_query,
        "status": final_state.get("status") or "error",
        "scope": final_state.get("scope"),
        "queries": None,
        "sources": None,
        "answer": final_state.get("answer"),
        "citations": None,
        "errors": [],
        "images": final_state.get("images"),
    }

    queries = final_state.get("queries")
    if _is_list_of_strings(queries):
        normalized_state["queries"] = queries

    sources = final_state.get("sources")
    if _is_list_of_dicts(sources):
        normalized_state["sources"] = sources

    citations = final_state.get("citations")
    if _is_list_of_strings(citations):
        normalized_state["citations"] = citations

    errors = final_state.get("errors")
    if _is_list_of_strings(errors):
        normalized_state["errors"] = errors

    return normalized_state


def make_initial_state(question: str) -> ResearchState:
    """创建研究运行的起始图状态。

    参数：
        问题：清理的用户研究问题。

    返回：
        ResearchState：LangGraph 预期的初始共享状态
            工作流程。"""
    initial_state: ResearchState = {
        "run_id": "",
        "question": question,
        "scope": None,
        "assumptions": None,
        "constraints": None,
        "queries": None,
        "sources": None,
        "answer": None,
        "citations": None,
        "status": "started",
        "errors": [],
        "debug": None,
        "conversation_id": None,
        "conversation_history": None,
        "mode": "research",
        "images": None,
    }

    return initial_state


def research_question(question: str) -> dict:
    """执行用户问题的研究用例。

    该函数验证传入的问题，准备初始问题
    图形状态，构建 LangGraph 工作流程，调用它，并返回
    调用传输层的标准化结果。

    共享问题验证器会引发 ValueError，因此可以重用它
    Pydantic/FastAPI 请求验证。在应用层边界，
    ValueError 被转换为 ApplicationError 所以传输层
    能够一致地处理预期的用例故障。

    参数：
        问题：用户研究问题。

    返回：
        dict：工作流程产生的标准化研究结果。

    加薪：
        ApplicationError：如果问题对于研究用途无效
            案例。"""
    try:
        user_query = validate_and_clean_question(question)
    except ValueError as exc:
        raise ApplicationError(str(exc)) from exc

    logger.info("Research use case started. question='%s'", user_query[:50])

    graph = build_graph()
    initial_state = make_initial_state(user_query)
    final_state = graph.invoke(initial_state)

    result = normalize_state(final_state, user_query)

    logger.info(
        "Research use case completed. status=%s run_id=%s",
        result.get("status"),
        result.get("run_id"),
    )
    return result
