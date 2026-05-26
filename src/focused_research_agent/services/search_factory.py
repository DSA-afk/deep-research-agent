"""搜索重点研究代理的提供商工厂。

该模块包含负责实例化的工厂函数
基于 SEARCH_PROVIDER 的正确搜索提供程序实现
环境变量。

添加新的搜索提供程序需要：
- 实现SearchProvider接口
- 在 get_search_provider 中添加新分支

不需要更改其他文件——所有调用者都经过这个工厂。

从架构上来说，该模块属于服务层并实现
工厂模式。它将提供商选择逻辑保留在一处，并且
将应用程序的其余部分与具体的提供程序类解耦。"""

from focused_research_agent.config.search_config import get_search_config
from focused_research_agent.interfaces.search_interface import SearchProvider
from focused_research_agent.services.search_provider_tavily import TavilySearchClient


def get_search_provider(search_depth: str | None = None) -> SearchProvider:
    """返回活动的搜索提供程序实现。

    参数：
        search_depth：搜索深度的可选覆盖。当提供时，
            覆盖 SEARCH_DEPTH 环境变量。接受
            “基本”或“高级”。

    返回：
        SearchProvider：配置的搜索提供程序实例。

    加薪：
        ValueError：如果配置的提供程序不受支持。"""
    search_config = get_search_config()
    provider = search_config["provider"]

    if provider == "tavily":
        return TavilySearchClient(search_depth=search_depth)
    else:
        raise ValueError(f"Unsupported search provider: {provider}")
