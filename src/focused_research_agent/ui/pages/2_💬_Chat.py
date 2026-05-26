"""Focused Research Agent UI 的 Streamlit 聊天页面。

该模块实现了对话式研究界面。它使用
Streamlit 的多页面约定 - 将其放在pages/文件夹中
使其在侧边栏导航中显示为单独的页面。

从架构上来说，该模块是一个 UI 传输入口点
1_🔍_研究.py。它遵循相同的模式：调用的薄布线层
api_client 用于数据并将渲染委托给视图和内联
st.* 需要特定于聊天的小部件。"""

import streamlit as st
from focused_research_agent.ui.api_client import (
    call_chat,
    check_health,
    get_conversations,
    get_conversation,
)
from focused_research_agent.ui.exceptions import BackendUnavailableError
from focused_research_agent.ui.views import render_health_status


def _init_session_state() -> None:
    """初始化聊天页面的会话状态密钥。

    使用保护模式以避免每次重新运行时重置状态。

    返回：
        无"""
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = None

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []


def _render_sidebar() -> None:
    """渲染聊天页面的所有侧边栏内容。

    显示健康状态、新对话按钮和
    过去与加载按钮的对话列表。

    返回：
        无"""
    st.sidebar.title("💬 Chat")
    api_health = check_health()
    render_health_status(api_health)

    if st.sidebar.button("新建对话"):
        st.session_state.conversation_id = None
        st.session_state.messages = []
        st.rerun()

    conversations = get_conversations()

    if conversations:
        st.sidebar.subheader("📋 历史对话")
        for convo in conversations:
            with st.sidebar.expander(convo["title"] or "无标题"):
                if st.button("加载", key=convo["conversation_id"]):
                    st.session_state.conversation_id = convo["conversation_id"]
                    turns = get_conversation(convo["conversation_id"])
                    st.session_state.messages = []
                    for turn in turns:
                        st.session_state.messages.append(
                            {
                                "role": "user",
                                "content": turn["question"],
                            }
                        )
                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "content": turn["answer"] or "",
                            }
                        )
                    st.rerun()


def _render_chat_history() -> None:
    """渲染当前对话线程中的所有消息。

    从会话状态读取并使用渲染每条消息
    st.chat_message 使用户和助理消息可视化
    杰出的。

    返回：
        无"""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def _handle_chat_input() -> None:
    """处理聊天输入并将问题发送到后端。

    渲染聊天输入栏，将用户消息附加到会话中
    状态，调用后端，并呈现助手响应。
    更新会话状态中的conversation_id，以便后续问题
    都被纳入同一个对话中。

    返回：
        无"""

    question = st.chat_input("输入研究问题...")
    if question is not None:
        st.session_state.messages.append({"role": "user", "content": question})

        with st.chat_message("user"):
            st.markdown(question)

        try:
            with st.spinner("正在研究中..."):
                result = call_chat(question, st.session_state.conversation_id)
        except BackendUnavailableError as e:
            st.error(str(e))
            st.stop()

        if result["success"]:
            data = result["data"]
            st.session_state.conversation_id = data["conversation_id"]
            answer = data.get("answer") or "未返回答案。"
            st.session_state.messages.append({"role": "assistant", "content": answer})
            with st.chat_message("assistant"):
                st.markdown(answer)
        else:
            error_message = result["error"] or "发生错误。"
            st.session_state.messages.append(
                {"role": "assistant", "content": f"❌ {error_message}"}
            )
            with st.chat_message("assistant"):
                st.error(error_message)


st.set_page_config(page_title="Research Chat", layout="centered")
st.title("💬 Research Chat")

_init_session_state()
_render_sidebar()
_render_chat_history()
_handle_chat_input()
