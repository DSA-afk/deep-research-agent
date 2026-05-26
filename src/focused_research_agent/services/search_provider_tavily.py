"""搜索提供商合同的实施得到了大利的支持。

该模块提供了 TavillySearchClient 类，它实现了
使用 Tavilly 网络搜索 API 的 SearchProvider 接口。它处理
查询验证、API 调用、响应规范化、URL 重复数据删除、
和图像提取。

关键设计决策：
- search_depth 可以在实例化时被覆盖以支持两者
  基本搜索（快速研究模式）和高级搜索（报告模式）
  无需更改任何其他代码。
- include_images=True 传递给每个 Tavily 调用，因此图像 URL
  可用于 UI 渲染，无需单独的 API 调用。
- 在返回之前，所有查询的结果均通过 URL 进行重复数据删除，
  确保同一来源永远不会被计算两次。

从架构上来说，该模块属于服务层并实现
适配器模式——它在 Tavily API 合约和
整个项目中使用的内部 SearchResult TypedDict。"""

import logging

# noinspection PyPackageRequirements
from tavily import TavilyClient

from focused_research_agent.config.search_config import get_search_config
from focused_research_agent.interfaces.search_interface import (
    SearchProvider,
    SearchResult,
)

logger = logging.getLogger(__name__)


class TavilySearchClient(SearchProvider):
    """搜索提供商合同的实施得到了大利的支持。"""

    def __init__(self, search_depth: str | None = None):
        """使用经过验证的配置初始化 Tavily 搜索客户端。

        参数：
            search_depth：搜索深度的可选覆盖。当提供时，
                覆盖 SEARCH_DEPTH 环境变量。接受
                “基本”或“高级”。"""
        self.search_config = get_search_config()
        self.tavily_client = TavilyClient(api_key=self.search_config["api_key"])

        if search_depth is not None:
            self.search_config["search_depth"] = search_depth

    # ------------------------------------------------------------------
    # 静态辅助函数 — 仅作用于其参数的纯验证函数，不读取或修改任何实例状态。
    # @staticmethod明确表示了这一点，并防止意外耦合到自身。
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_queries(queries: list[str]) -> list[str]:
        """验证并清理传入的搜索查询。

        参数：
            查询：搜索查询的原始列表。

        返回：
            list[str]：清理的非空查询字符串。

        加薪：
            ValueError：如果查询不是非空非空列表
                字符串。"""
        if not isinstance(queries, list):
            raise ValueError("TavilySearchClient: queries must be a list")

        if len(queries) == 0:
            raise ValueError("TavilySearchClient: No queries provided")

        cleaned_queries = []

        for query in queries:
            if not isinstance(query, str):
                raise ValueError("TavilySearchClient: Query must be a string")

            cleaned_query = query.strip()
            if not cleaned_query:
                raise ValueError("TavilySearchClient: Query must not be empty")

            cleaned_queries.append(cleaned_query)

        return cleaned_queries

    @staticmethod
    def _validate_tavily_response(response: object, query: str) -> list[dict]:
        """验证单个查询的 Tavily API 响应形状。

        参数：
            响应：Tavily 返回的原始响应。
            query：用于 Tavily 调用的查询。

        返回：
            list[dict]：原始 Tavily 结果项。

        加薪：
            ValueError：如果响应不是字典或不包含
                有效的“结果”列表。"""
        if not isinstance(response, dict) or "results" not in response:
            raise ValueError(
                f"search_client: Tavily response missing valid results: {query}"
            )

        results = response["results"]

        if not isinstance(results, list):
            raise ValueError(
                f"search_client: Tavily response missing valid results: {query}"
            )

        return results

    # ------------------------------------------------------------------
    # 实例方法 — 这些使用 self.search_config 或
    # self.tavily_client，必须保留为实例方法。
    # ------------------------------------------------------------------

    def _normalize_result(self, item: dict, query: str) -> SearchResult:
        """将一个 Tavilly 结果项标准化为共享的 SearchResult 形状。

        参数：
            item：原始 Tavilly 结果项目。
            query：产生此结果的查询，在错误消息中使用。

        返回：
            SearchResult：与 SearchResult 形状匹配的标准化结果字典。

        加薪：
            ValueError：如果结果项格式错误或缺少必需项
                字段。"""
        if not isinstance(item, dict):
            raise ValueError(
                f"TavilySearchClient: Invalid result item returned for query: {query}"
            )

        title = (item.get("title") or "").strip()
        url = (item.get("url") or "").strip()
        snippet = (item.get("content") or "").strip()[:500]  # 限制摘要长度
        score_raw = item.get("score")

        if not title or not url:
            raise ValueError(
                f"TavilySearchClient: Result missing title or url for query: {query}"
            )

        if score_raw is None:
            raise ValueError(
                f"TavilySearchClient: Result missing score for query: {query}"
            )

        if not isinstance(score_raw, (int, float, str)):
            raise ValueError(
                f"TavilySearchClient: Invalid score type in result for query: {query}"
            )

        try:
            score: float = float(score_raw)
        except ValueError:
            raise ValueError(
                f"TavilySearchClient: Invalid score value in result for query: {query}"
            )

        normalized_result: SearchResult = {
            "title": title,
            "url": url,
            "snippet": snippet,
            "source": self.search_config["provider"],  # 供应商
            "score": score,
        }

        return normalized_result

    def _search_single_query(self, query: str) -> tuple[list[SearchResult], list[str]]:
        """对一个查询运行 Tavilly 搜索并对返回的结果进行标准化。

        参数：
            查询：单个经过验证的搜索查询。

        返回：
            list[SearchResult]：该查询的标准化结果。
            list[str]: 图像列表

        加薪：
            ValueError：如果 Tavilly 响应形状无效或结果
                项目格式错误。"""
        response = self.tavily_client.search(
            query=query,
            search_depth=self.search_config["search_depth"],
            max_results=self.search_config["max_results"],
            include_images=True,
        )

        response_results = self._validate_tavily_response(response, query)
        images = response.get("images") or []

        normalized_results: list[SearchResult] = []
        for item in response_results:
            normalized_results.append(self._normalize_result(item, query))

        logger.debug(  # ← 添加
            "Query completed. query='%s' results=%d images=%d",
            query[:60],
            len(normalized_results),
            len(images),
        )

        return normalized_results, images

    def search(self, queries: list[str]) -> tuple[list[SearchResult], list[str]]:
        """运行 Tavilly 搜索并返回标准化、去重复的结果。

        参数：
            查询：经过验证的搜索查询的列表。

        返回：
            list[SearchResult]：经过重复数据删除和规范化的搜索结果。
            list[str]: 图像列表

        加薪：
            ValueError：如果查询列表无效或Tavilly返回一个
                意外的反应结构。"""
        cleaned_queries = self._validate_queries(queries)
        final_search_results: list[SearchResult] = []
        all_images: list[str] = []
        seen_urls: set[str] = set()

        for query in cleaned_queries:
            query_results, query_images = self._search_single_query(query)
            for result in query_results:
                if result["url"] in seen_urls:
                    continue
                seen_urls.add(result["url"])
                final_search_results.append(result)
            all_images.extend(query_images)

        logger.info(
            "Search completed. queries=%d total_sources=%d total_images=%d",
            len(cleaned_queries),
            len(final_search_results),
            len(all_images),
        )

        return final_search_results, all_images
