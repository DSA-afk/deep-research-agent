"""重点研究代理的 Web 搜索节点。

该模块包含负责执行网络搜索的节点
使用生成的查询。它接收注入的搜索提供程序
通过 graph.py 的闭包 — 相同的依赖注入模式
用于LLM节点。

搜索结果由搜索提供商进行重复数据删除和标准化
在存储在状态之前。提供者返回的图像是
上限为 _NUMBER_OF_IMAGES 并单独存储以供 UI 渲染。

如果搜索提供程序引发异常，则会在中记录错误
状态和图路由到handle_error。"""

import logging

from focused_research_agent.interfaces.search_interface import SearchProvider
from focused_research_agent.state import ResearchState

logger = logging.getLogger(__name__)

_NUMBER_OF_IMAGES = 12


def search_web(state: ResearchState, search_provider: SearchProvider) -> dict:
    """使用生成的查询搜索网络。

    该节点从工厂检索活动搜索提供程序，
    执行查询，并将标准化源存储在状态中。

    参数：
        state：当前的研究状态。
        search_provider：活动搜索提供程序实例。

    返回：
        dict：包含源和状态的部分状态更新，
        如果搜索失败，则显示错误字段。"""
    queries = state.get("queries")
    run_id = state.get("run_id", "unknown")

    if not isinstance(queries, list):
        logger.error("search_web: queries must be a list. run_id=%s", run_id)
        return {"errors": ["search_web: queries must be a list"]}

    if not queries:
        logger.error("search_web: No queries found. run_id=%s", run_id)
        return {"errors": ["search_web: No queries found"]}

    try:
        search_results, images = search_provider.search(queries)
    except Exception as e:
        logger.exception("search_web failed. run_id=%s error=%s", run_id, e)
        return {"errors": [f"search_web failed: {e}"]}

    logger.info(
        "Search completed. run_id=%s sources=%d images=%d",
        run_id,
        len(search_results),
        len(images),
    )

    return {
        "sources": search_results,
        "images": images[:_NUMBER_OF_IMAGES],
        "status": "searched",
    }
