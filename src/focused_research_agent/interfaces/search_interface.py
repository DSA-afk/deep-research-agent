from abc import ABC, abstractmethod
from typing import TypedDict


class SearchResult(TypedDict):
    """单个搜索结果的标准化架构。"""

    title: str
    url: str
    snippet: str
    source: str
    score: float


class SearchProvider(ABC):
    """研究代理使用的搜索提供商的抽象合同。"""

    @abstractmethod
    def search(self, queries: list[str]) -> tuple[list[SearchResult], list[str]]:
        """运行网络搜索并返回标准化结果。

        参数：
            查询：要执行的搜索查询的列表。

        返回：
            tuple：元组包含：
                - list[SearchResult]：规范化搜索结果
                - list[str]: 搜索过程中找到的图像 URL"""
        ...
