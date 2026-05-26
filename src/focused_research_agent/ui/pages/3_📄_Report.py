"""重点研究代理 UI 的 Streamlit 报告页面。

该模块实现了深度研究报告生成接口。
它使用 Streamlit 的多页面约定 - 将其放在页面/中
带有 3_ 前缀的文件夹使其在侧边栏导航中显示为第三个。

报告页面使用先进的 Tavilly 搜索深度和结构化的
生成包含简介、主要发现、
分析和结论部分。报告生成时间长于
快速研究——用户可以通过标题和旋转器得知这一点。

从架构上来说，该模块是一个 UI 传输入口点
Home.py 和其他页面。它遵循相同的细布线图案。"""

import streamlit as st
from focused_research_agent.ui.exceptions import BackendUnavailableError
from focused_research_agent.ui.views import render_health_status
from focused_research_agent.ui.api_client import (
    call_report,
    check_health,
    get_conversation,
    get_reports,
)


def _init_session_state() -> None:
    """初始化报告页面的会话状态密钥。
    ..."""
    if "report_result" not in st.session_state:
        st.session_state.report_result = None

    if "report_question" not in st.session_state:
        st.session_state.report_question = ""

    if "report_generating" not in st.session_state:
        st.session_state.report_generating = False


def _render_sidebar() -> None:
    """呈现报告页面的侧边栏内容。

    显示页面标题、API 健康状态和列表
    过去的报告使用加载按钮运行。

    返回：
        无"""
    st.sidebar.title("📄 Report")
    render_health_status(check_health())

    reports = get_reports()
    if reports:
        st.sidebar.subheader("📋 历史报告")
        for report in reports:
            with st.sidebar.expander(report["title"] or "无标题"):
                if st.button("加载", key=report["conversation_id"]):
                    turns = get_conversation(report["conversation_id"])
                    if turns:
                        st.session_state.report_result = {
                            "success": True,
                            "data": turns[0],
                        }
                    st.rerun()


def _render_report_input() -> str | None:
    question = st.text_area(
        "你想生成什么主题的报告？",
        height=100,
        placeholder="例如：量子计算对人工智能的影响",
    )
    if st.button("📄 生成报告"):
        return question
    return None


def _render_report_success(data: dict) -> None:
    """渲染成功的报表内容。

    参数：
        data：来自后端的完整报告响应字典。

    返回：
        无"""
    st.success("✅ 报告生成成功！")
    st.divider()
    st.markdown(data["answer"])
    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📋 搜索查询", len(data.get("queries") or []))
    with col2:
        st.metric("🔗 资料来源", len(data.get("sources") or []))
    with col3:
        st.metric("✅ 引用数量", len(data.get("citations") or []))

    st.divider()

    images = data.get("images") or []
    if images:
        st.subheader("🖼️ 相关图片")
        cols = st.columns(min(len(images), 3))
        for index, url in enumerate(images):
            with cols[index % 3]:
                try:
                    st.image(url, use_container_width=True)
                except Exception:
                    pass
        st.divider()

    if data.get("sources"):
        st.subheader("📚 资料来源")
        for source in data["sources"]:
            with st.expander(source["title"]):
                st.write(source["url"])
                st.caption(source["snippet"])

    st.divider()

    if st.checkbox("🛠️ 显示原始响应"):
        st.json(data)


def _render_report_result() -> None:
    """呈现会话状态的最新报告结果。

    返回：
        无"""
    if st.session_state.report_result is None:
        return

    result = st.session_state.report_result

    # 处理传输层故障 — 422、500、连接错误
    # 在这些情况下 result["data"] 为 None
    if not result["success"] and result["data"] is None:    # ← 添加此代码块
        st.error(result["error"] or "发生错误。")
        return

    data = result["data"]

    if data.get("status") == "error" or data.get("answer") is None:
        errors = data.get("errors") or ["发生未知错误。"]
        st.error(f"Research 失败：{errors[0]}")
        if st.checkbox("🛠️ 显示原始响应"):
            st.json(result)
        return

    if result["success"]:
        _render_report_success(data)
    else:
        st.error(result["error"] or "发生错误。")


st.set_page_config(page_title="Research Report", layout="centered")
st.title("📄 Research Report")
st.caption("深度研究与结构化分析 — 比快速 Research 耗时更长。")

_init_session_state()
_render_sidebar()

question = _render_report_input()

if question is not None:
    try:
        with st.spinner("正在生成报告 — 可能需要几分钟..."):
            result = call_report(question)
        st.session_state.report_result = result
    except BackendUnavailableError as e:
        st.error(str(e))
        st.stop()

_render_report_result()
