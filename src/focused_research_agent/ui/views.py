"""Focused Research Agent UI 的 Streamlit 渲染功能。

该模块是UI层中唯一导入streamlit的文件。
它采用纯 Python 数据并呈现 Streamlit 小部件。它包含
没有 HTTP 逻辑，也没有对 api_client 的调用。

从架构上来说，该模块是UI的表示层
Transport — 与 cli.py 中 format_* 函数扮演的角色相同，但是
渲染小部件而不是构建终端字符串。"""

import streamlit as st


def render_health_status(is_online: bool) -> None:
    """在侧边栏渲染后端健康状态。

    当后端可访问时显示绿色成功横幅并且
    如果不是，则显示红色错误横幅。在每个页面加载时调用，以便
    用户始终知道后端是否正在运行。

    参数：
        is_online：如果后端响应 HTTP 200，则为 True，
            否则为假。

    返回：
        无"""
    if is_online:
        st.sidebar.success("✅ API 在线")
    else:
        st.sidebar.error("❌ API 离线 — 请先启动 FastAPI")


def render_error(message: str) -> None:
    """在主区域中呈现面向用户的错误消息。

    显示带有所提供消息的红色错误横幅。调用时间
    研究请求因后端以外的任何原因失败
    完全无法到达。

    参数：
        message：要显示的人类可读的错误消息。

    返回：
        无"""
    st.error(message)


def render_answer(data: dict) -> None:
    """给出主要领域的研究答案。

    显示成功横幅，后跟合成的答案文本。
    仅当研究请求成功时调用。

    参数：
        data：后端返回的完整研究响应字典。
            预计至少包含一个“答案”键。

    返回：
        无"""
    st.success("✅ Research 完成！")
    st.markdown(data["answer"])
    st.divider()


def render_research_details(data: dict) -> None:
    """在可折叠扩展器中渲染研究细节。

    显示折叠内的范围、查询、引文和运行 ID
    扩展器，以便在不占据页面的情况下提供这些详细信息。
    仅当后端为其返回数据时，每个部分才会呈现。

    参数：
        data：后端返回的完整研究响应字典。

    返回：
        无"""
    with st.expander("🔍 Research 详情", expanded=False):
        if data["scope"] is not None:
            st.subheader("研究范围")
            st.markdown(data["scope"])

        if data["queries"] is not None:
            st.subheader("搜索查询")
            for query in data["queries"]:
                st.write(f"- {query}")

        if data["citations"] is not None:
            st.subheader("引用来源")
            for citation in data["citations"]:
                st.write(citation)
        st.caption(f"运行 ID：{data['run_id']}")
    st.divider()


def _extract_image_urls(sources: list[dict]) -> list[str]:
    """从源字典列表中提取图像 URL。

    扫描源 URL 中的已知图像文件扩展名并返回
    任何匹配的。用于渲染下面的视觉图像部分
    研究答案。

    参数：
        来源：来自后端响应的源字典列表。

    返回：
        list[str]：在源中找到的图像 URL 列表。
            如果未找到图像 URL，则列表为空。"""
    image_extensions = (".jpg", ".jpeg", ".png", ".gif", ".webp")
    image_urls = []

    for source in sources:
        url = source.get("url", "").lower()
        if url.endswith(image_extensions):
            image_urls.append(source["url"])

    return image_urls


def render_sources(sources: list[dict], images: list[str] | None = None) -> None:
    """将研究源列表呈现为可折叠扩展器。
    如果可用，则在源上方呈现图像 URL。

    参数：
        来源：后端返回的源字典列表。
        images：搜索结果中的图像 URL 的可选列表。

    返回：
        无"""

    if images:
        st.subheader("🖼️ 相关图片")
        cols = st.columns(min(len(images), 3))
        for index, url in enumerate(images):
            with cols[index % 3]:
                try:
                    st.image(url, use_container_width=True)
                except Exception:
                    pass


    st.subheader("📚 资料来源")
    if not sources:
        st.info("暂无可用来源。")
        return

    for source in sources:
        with st.expander(source["title"]):
            st.write(source["url"])
            st.caption(source["snippet"])


def render_metrics(data: dict) -> None:
    """呈现显示研究运行统计数据的摘要指标行。

    将查询计数、来源计数和引用计数显示为指标
    三列布局中的小部件。给用户一个即时的
    在阅读答案之前先了解一下研究的深度。

    参数：
        data：后端返回的完整研究响应字典。

    返回：
        无"""
    # | 📋 5 个查询 | 🔗 8 个来源 | ✅ 3 个引用 |
    if data["queries"] is not None:
        queries_count = len(data["queries"])
    else:
        queries_count = 0

    if data["sources"] is not None:
        sources_count = len(data["sources"])
    else:
        sources_count = 0

    if data["citations"] is not None:
        citations_count = len(data["citations"])
    else:
        citations_count = 0

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("📋 搜索查询", queries_count)

    with col2:
        st.metric("🔗 资料来源", sources_count)

    with col3:
        st.metric("✅ 引用数量", citations_count)

    st.divider()
