"""Focused Research Agent API 的 FastAPI 依赖项提供程序。

该模块包含 API 路由器使用的依赖函数来获取
应用程序层用例和其他可注入组件。

从架构上来说，这个模块属于API层。它有助于保持路由器
通过将依赖关系连接与端点定义分开来精简。"""

from collections.abc import Callable
from focused_research_agent.application import chat_use_case, report_use_case
from focused_research_agent.application import research_use_case


def get_research_use_case() -> Callable[[str], dict]:
    """向 API 路由提供应用层研究用例。

    此依赖项返回负责执行的可调用函数
    研究用例。路由器可以使用返回的可调用对象，而无需
    直接导入具体实现。

    返回：
        Callable[[str], dict]：接受用户问题的可调用对象
        并返回结构化的研究结果。"""
    return research_use_case.research_question


def get_chat_use_case() -> Callable:
    """向 API 路由提供应用层聊天用例。

    返回：
        Callable：可调用，接受 db、conversation_id 和
            问题并返回结构化的聊天结果。"""
    return chat_use_case.execute_chat_turn


def get_report_use_case() -> Callable:
    """向 API 路由提供应用层报告用例。

    返回：
        Callable：接受问题和数据库并返回的可调用对象
            结构化报告结果。"""
    return report_use_case.execute_report
