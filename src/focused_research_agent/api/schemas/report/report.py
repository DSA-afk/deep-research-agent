"""报告 API 的 Pydantic 请求和响应架构。

该模块定义了报告生成的API合约
端点。响应形状与 ResearchResponse 相同 -
结构化报告内容位于答案字段内，如下所示
格式化的降价。

SourceResponse 是从研究模式导入的，而不是
重复 - 所有端点的源形状都是相同的。"""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, StringConstraints

from focused_research_agent.api.schemas.research.research import SourceResponse
from focused_research_agent.application.question_validation import (
    validate_and_clean_question,
)


class ReportRequest(BaseModel):
    """通过 API 生成研究报告的请求架构。

    仅包含用户的问题。报告是单轮的——
    没有用于生成报告的对话线程。

    属性：
        问题：用户对报告的研究问题。"""

    question: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, strict=True),
        AfterValidator(validate_and_clean_question),
    ]


class ReportResponse(BaseModel):
    """报告 API 端点返回的响应架构。

    答案字段包含一个结构化的 Markdown 报告
    简介、主要发现、分析和结论部分。
    引文最多包含 5 个支持该报告的源 URL。

    属性：
        run_id：本次研究运行的唯一标识符。
        Question：用户对此报告提出的问题。
        状态：研究运行的最终状态。
        范围：问题的范围解释。
        查询：生成的网络搜索查询。
        来源：综合中使用的标准化源条目。
        答案：完整的结构化降价报告。
        引用：支持报告的引用 URL。最多 5 个。
        错误：收集的工作流程错误。总是一个清单。"""

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
