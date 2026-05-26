"""聊天 API 的 Pydantic 请求和响应模式。

该模块定义聊天端点的 API 合约。它
将研究模式扩展到对话线程领域。

SourceResponse 是从研究模式导入的，而不是
重复 - 两个端点的源形状相同。"""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, StringConstraints

from focused_research_agent.api.schemas.research.research import SourceResponse
from focused_research_agent.application.question_validation import (
    validate_and_clean_question,
)


class ChatRequest(BaseModel):
    """通过 API 提交聊天回合的请求架构。

    包含用户的问题和可选的对话 ID。
    当conversation_id为None时，后端开始一个新的对话
    并在响应中返回生成的 ID。当提供时，
    后端将问题串入现有对话中。

    属性：
        Question：用户本轮的研究问题。
        conversation_id：要继续的现有对话 UUID，或者
            没有开始新的对话。"""

    question: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, strict=True),
        AfterValidator(validate_and_clean_question),
    ]

    conversation_id: str | None = None


class ChatResponse(BaseModel):
    """聊天 API 端点返回的响应架构。

    通过对话元数据扩展标准研究响应。
    Conversation_id 必须由客户端存储并发回
    并提出后续问题以继续对话。

    属性：
        run_id：本次研究运行的唯一标识符。
        Question：用户本轮提出的问题。
        状态：研究运行的最终状态。
        范围：问题的范围解释。
        查询：生成的网络搜索查询。
        来源：综合中使用的标准化源条目。
        答案：最终综合答案。
        引用：支持答案的引用 URL。
        错误：收集的工作流程错误。总是一个清单。
        conversation_id：将此回合链接到其对话的 UUID。
            保存好并将其连同后续问题一起发回。
        turn_number：本回合在对话中的位置。"""

    run_id: str
    question: str
    status: str
    scope: str | None
    queries: list[str] | None
    sources: list[SourceResponse] | None
    answer: str | None
    citations: list[str] | None
    errors: list[str]
    conversation_id: str
    turn_number: int
    images: list[str] | None
