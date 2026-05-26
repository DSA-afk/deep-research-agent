"""Focused Research Agent Streamlit UI 的 HTTP 客户端。

该模块是 UI 层中唯一了解 httpx 的文件。
它调用 FastAPI 后端并向调用者返回纯 Python 字典。
它不包含 Streamlit 代码。

从架构上来说，该模块是 UI 的外部集成适配器
传输层 — 与 search_provider_tavilly.py 所扮演的角色相同
搜索集成，但指向内部 FastAPI 后端
外部 API 的。"""

from typing import TypedDict
import httpx
from focused_research_agent.config.ui_config import get_ui_settings
from focused_research_agent.ui.exceptions import BackendUnavailableError


_HEALTH_ENDPOINT = "/health"
_RESEARCH_ENDPOINT = "/api/v1/research"
_CHAT_ENDPOINT = "/api/v1/chat"
_CONVERSATIONS_ENDPOINT = "/api/v1/conversations"
_REPORT_ENDPOINT = "/api/v1/report"
_REPORTS_ENDPOINT = "/api/v1/reports"

_TIMEOUT_ERROR_MESSAGE = "请求超时 — 研究耗时过长。"


class ResearchCallResult(TypedDict):
    success: bool
    data: dict | None
    error: str | None


def check_health() -> bool:
    """检查FastAPI后端是否可达。

    使用较短的固定超时向 /health 端点发出 GET 请求。
    健康检查失败并不是错误——它意味着后端离线。
    这个函数永远不会引发；它总是返回一个布尔值。

    返回：
        bool：如果后端响应 HTTP 200，则为 True，否则为 False。"""
    settings = get_ui_settings()
    try:
        response = httpx.get(f"{settings.api_base_url}{_HEALTH_ENDPOINT}", timeout=5.0)
        return response.status_code == 200
    except httpx.ConnectError:
        return False


def _parse_post_response(response: httpx.Response) -> ResearchCallResult:
    """
    参数：
        response: The httpx response object from the POST request.

    返回：
        ResearchCallResult: Parsed result with success, data, and
            error fields populated based on the response status code."""
    if response.status_code == 200:
        return {"success": True, "data": response.json(), "error": None}

    if response.status_code == 400:
        return {"success": False, "data": None, "error": response.json()["detail"]}

    if response.status_code == 422:
        return {"success": False, "data": None, "error": "提交的问题无效。"}

    return {
        "success": False,
        "data": None,
        "error": f"未知错误：{response.status_code}",
    }


def call_research(question: str) -> ResearchCallResult:
    """向 FastAPI 后端发送研究问题并返回结果。

    使用用户的地址向版本化研究端点发出 POST 请求
    问题作为 JSON 正文。始终返回带有三个的 ResearchCallResult
    键：成功、数据和错误。形状在所有地方都是一致的
    响应路径，以便 1_🔍_Research.py 和views.py 永远不必猜测什么
    他们正在接收。

    参数：
        Question：用户要发送到后端的研究问题。

    返回：
        ResearchCallResult：具有以下键的键入字典：
            - success (bool): 如果后端返回 HTTP 200，则为 True，
                对于所有其他响应都是错误的。
            - 数据（dict | None）：来自
                成功时返回 True，否则 None。
            - error (str | None)：人类可读的错误消息
                成功为 False，否则为 None。

    加薪：
        BackendUnavailableError：如果无法到达后端
            配置的 UI_API_BASE_URL。提高而不是返回
            一个错误字典，因为完全无法访问的后端是
            失败与不良反应的不同类别——这意味着
            用户需要先启动后端才能重试。"""
    settings = get_ui_settings()
    try:
        response = httpx.post(
            f"{settings.api_base_url}{_RESEARCH_ENDPOINT}",
            json={"question": question},
            timeout=settings.request_timeout,
        )
        return _parse_post_response(response)
    except httpx.ConnectError:
        raise BackendUnavailableError(
            f"无法连接到后端 {settings.api_base_url} — 请确认 FastAPI 是否已启动。"
        )
    except httpx.TimeoutException:
        return {
            "success": False,
            "data": None,
            "error": _TIMEOUT_ERROR_MESSAGE,
        }


def call_chat(question: str, conversation_id: str | None) -> ResearchCallResult:
    """向 FastAPI 后端发送聊天轮次并返回结果。

    使用用户的问题向聊天端点发出 POST 请求
    和可选的对话 ID。返回 ResearchCallResult ，其中
    与 call_research 形状相同，但数据字典还包含
    conversation_id 和turn_number 字段。

    参数：
        Question：用户本轮的研究问题。
        conversation_id：要继续的现有对话 UUID，或者
            没有开始新的对话。

    返回：
        ResearchCallResult：包含成功、数据和错误的类型化字典
            键。成功后，数据包含完整的聊天响应
            包括conversation_id和turn_number。

    加薪：
        BackendUnavailableError：如果无法到达后端。"""
    settings = get_ui_settings()
    try:
        response = httpx.post(
            f"{settings.api_base_url}{_CHAT_ENDPOINT}",
            json={"question": question, "conversation_id": conversation_id},
            timeout=settings.request_timeout,
        )
        return _parse_post_response(response)
    except httpx.ConnectError:
        raise BackendUnavailableError(
            f"无法连接到后端 {settings.api_base_url} — 请确认 FastAPI 是否已启动。"
        )
    except httpx.TimeoutException:
        return {
            "success": False,
            "data": None,
            "error": _TIMEOUT_ERROR_MESSAGE,
        }


def call_report(question: str) -> ResearchCallResult:
    """向 FastAPI 后端发送报告生成请求并
    返回结果。

    使用用户的地址向报告端点发出 POST 请求
    问题。返回具有相同形状的 ResearchCallResult
    call_research，但答案字段包含结构化
    降价报告包含简介、主要发现、分析、
    和结论部分。

    参数：
        问题：用户对报告的研究问题。

    返回：
        ResearchCallResult：包含成功、数据和信息的类型化字典
            错误键。成功后，数据包含完整报告
            在答案字段中使用结构化降价进行响应。

    加薪：
        BackendUnavailableError：如果无法到达后端。"""

    settings = get_ui_settings()
    try:
        response = httpx.post(
            f"{settings.api_base_url}{_REPORT_ENDPOINT}",
            json={"question": question},
            timeout=settings.request_timeout,
        )
        return _parse_post_response(response)
    except httpx.ConnectError:
        raise BackendUnavailableError(
            f"无法连接到后端 {settings.api_base_url} — 请确认 FastAPI 是否已启动。"
        )
    except httpx.TimeoutException:
        return {
            "success": False,
            "data": None,
            "error": _TIMEOUT_ERROR_MESSAGE,
        }


def get_conversations() -> list[dict]:
    """从后端获取所有过去对话的列表。

    向对话端点发出 GET 请求。返回一个
    任何错误都为空列表，以便历史面板故障永远不会发生
    阻止聊天 UI 运行。

    返回：
        list[dict]：包含以下内容的对话摘要字典列表
            对话id、标题和created_at键。
            如果请求因任何原因失败，则列表为空。"""
    settings = get_ui_settings()
    try:
        response = httpx.get(
            f"{settings.api_base_url}{_CONVERSATIONS_ENDPOINT}",
            timeout=settings.request_timeout,
        )

        if response.status_code == 200:
            return response.json()
        else:
            return []
    except httpx.ConnectError:
        return []

    except httpx.TimeoutException:
        return []


def get_conversation(conversation_id: str) -> list[dict]:
    """从后端获取特定对话的所有回合。

    向对话详细信息端点发出 GET 请求。退货
    任何错误的空列表，以便历史加载永远不会失败
    阻止聊天 UI。

    参数：
        conversation_id：标识对话的 UUID 字符串
            获取。

    返回：
        list[dict]：按时间顺序排列的完整字典列表。
            如果请求因任何原因失败，则列表为空。"""
    settings = get_ui_settings()
    try:
        response = httpx.get(
            f"{settings.api_base_url}{_CONVERSATIONS_ENDPOINT}/{conversation_id}",
            timeout=settings.request_timeout,
        )

        if response.status_code == 200:
            return response.json()
        else:
            return []
    except httpx.ConnectError:
        return []

    except httpx.TimeoutException:
        return []


def get_reports() -> list[dict]:
    """从后端获取所有过去运行的报告的列表。

    出现任何错误时返回空列表，因此侧边栏永远不会失败
    阻止报告 UI。

    返回：
        list[dict]：报告摘要字典列表，包含
            对话id、标题和created_at键。
            如果请求因任何原因失败，则列表为空。"""
    settings = get_ui_settings()
    try:
        response = httpx.get(
            f"{settings.api_base_url}{_REPORTS_ENDPOINT}",
            timeout=settings.request_timeout,
        )
        if response.status_code == 200:
            return response.json()
        else:
            return []
    except httpx.ConnectError:
        return []
    except httpx.TimeoutException:
        return []
