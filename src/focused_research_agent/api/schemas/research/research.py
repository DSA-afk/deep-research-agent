"""研究 API 的 Pydantic 请求和响应模式。

该模块定义研究端点的 API 合约。这些模式
描述FastAPI路由接受的请求体和结构化的
返回给 API 客户端的响应。

这些模型属于 API 边界，应该代表传输级别
数据形状，而不是内部图形状态或特定于提供者的模型。"""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, StringConstraints

from focused_research_agent.application.question_validation import (
    validate_and_clean_question,
)


class ResearchRequest(BaseModel):
    """通过 API 提交研究问题的请求架构。

    该模型代表触发研究所需的客户端有效负载
    用例。它包含经过验证的非空用户问题和拒绝
    空白、仅空白、仅标点符号或无意义的超短
    输入。

    属性：
        Question：用户的研究问题。"""

    question: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, strict=True),
        AfterValidator(validate_and_clean_question),
    ]


class SourceResponse(BaseModel):
    """代表研究响应中返回的一个来源的模式。

    该模型定义了标准化源项目的传输级形状
    包含在 API 响应中。

    属性：
        title：人类可读的源标题。
        url：源 URL。
        snippet：来源的简短摘录或摘要。
        来源：原始来源提供商的名称。
        分数：搜索期间分配的相关性分数。"""

    title: str
    url: str
    snippet: str
    source: str
    score: float


class ResearchResponse(BaseModel):
    """研究 API 端点返回的响应架构。

    该模型代表供研究使用的结构化 API 响应
    案例。它反映了通过暴露的主图输出字段
    应用层并提供稳定的传输级响应形状
    为客户。

    错误字段的类型为 list[str] — 而不是 list[str] |没有——因为
    应用层的normalize_state总是以列表的形式返回错误，
    当没有发生错误时默认为空列表。这使得
    契约显式：调用者始终可以安全地迭代错误，而无需
    无检查。

    属性：
        run_id：研究运行的唯一标识符。
        问题：原始用户问题。
        状态：研究运行的最终状态。
        范围：对用户问题的范围解释。
        查询：生成的网络搜索查询。
        来源：综合中使用的标准化源条目。
        答案：最终综合答案。
        引用：支持答案的引用 URL。
        错误：收集的工作流程错误。总是一个清单；无时为空。"""

    run_id: str
    question: str
    status: str
    scope: str | None
    queries: list[str] | None
    sources: list[SourceResponse] | None
    answer: str | None
    citations: list[str] | None
    errors: list[str]
    images: list[str] | None
