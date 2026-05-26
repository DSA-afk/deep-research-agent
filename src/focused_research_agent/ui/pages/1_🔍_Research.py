"""Streamlit application entrypoint for the Focused Research Agent UI.

This module wires together the api_client and views layers.它管理
session state, reads user input, calls the backend through api_client,
并将所有渲染委托给视图。

Architecturally, this module is the UI transport entrypoint — the same
cli.py 在终端传输中扮演的角色。它不应包含 HTTP
logic and no direct st.* rendering beyond layout and input widgets."""

import streamlit as st
from focused_research_agent.ui.api_client import call_research, check_health
from focused_research_agent.ui.views import (
    render_research_details,
    render_error,
    render_sources,
    render_answer,
    render_health_status,
    render_metrics,
)
from focused_research_agent.ui.exceptions import BackendUnavailableError


def _init_session_state() -> None:
    """初始化重新运行时使用的会话状态密钥。

    使用保护模式以避免每次重新运行时重置状态。
    必须在任何小部件之前在脚本顶部调用一次
    依赖于会话状态的渲染。

    返回：
        无"""
    if "history" not in st.session_state:
        st.session_state.history = []

    if "last_result" not in st.session_state:
        st.session_state.last_result = None


def _render_sidebar() -> None:
    """渲染所有侧边栏内容，包括设置标题、健康状态、
    和过去的研究会议历史。

    返回：
        无"""
    st.sidebar.title("⚙️ 设置")
    is_online = check_health()
    render_health_status(is_online)

    if st.session_state.history:
        st.sidebar.subheader("📋 历史记录")
        for item in reversed(st.session_state.history):
            with st.sidebar.expander(item["question"][:60]):
                st.write(item["answer"])
                st.caption(f"运行 ID：{item['run_id']}")


def _render_input() -> str:
    """渲染研究问题输入区域并返回当前值。

    返回：
        str: The current text entered by the user.如果什么都没有则为空字符串
            尚未进入。"""
    user_query = st.text_area(
        "你想研究什么问题？",
        placeholder="例如：量子计算领域有哪些最新进展？",
        height=100,
    )
    return user_query


def _handle_research(question: str) -> None:
    """渲染研究按钮并处理研究请求。

    单击按钮并提出有效问题时调用后端
    提供。将结果存储在会话状态中，以便它持续存在
    跨重播。如果后端正在运行，则立即停止脚本
    无法到达。

    参数：
        Question：问题输入区域的当前值。

    返回：
        无"""
    if st.button("🔍 开始 Research"):
        if not question.strip():
            st.warning("请先输入问题。")
        else:
            try:
                with st.spinner("正在研究中... 可能需要 2 分钟左右。"):
                    result = call_research(question)
                    st.session_state.last_result = result
                if result["success"]:
                    st.session_state.history.append(
                        {
                            "question": question,
                            "answer": result["data"]["answer"],
                            "run_id": result["data"]["run_id"],
                        }
                    )
            except BackendUnavailableError as e:
                st.error(str(e))
                st.stop()


def _render_results() -> None:
    """渲染会话状态的最新研究结果。

    从会话状态读取last_result并将渲染委托给
    意见。如果尚不存在结果，则不渲染任何内容。

    返回：
        无"""
    if st.session_state.last_result is not None:
        result = st.session_state.last_result

        if result["success"]:
            render_answer(result["data"])
            render_metrics(result["data"])
            render_research_details(result["data"])
            render_sources(result["data"]["sources"], result["data"].get("images") )
        else:
            render_error(result["error"])

        st.divider()
        if st.checkbox("🛠️ 显示原始响应"):
            st.json(result)


st.set_page_config(page_title="Focused Research Agent", layout="centered")
st.title("🔍 Focused Research Agent")

_init_session_state()
_render_sidebar()
question = _render_input()
_handle_research(question)
_render_results()
