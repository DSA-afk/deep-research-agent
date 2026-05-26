"""重点研究代理的报告生成 API 端点。

该模块公开了深度研究报告的 HTTP 端点
一代。它接收经过验证的报告请求，获取
数据库会话并通过以下方式执行报告用例
依赖注入，并返回结构化报告响应。

从架构上来说，该模块属于传输层。它
保持精简——没有业务逻辑，没有数据库查询，没有图表
来电。它将一切委托给应用层
执行报告。"""

from typing import Annotated, Callable
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from focused_research_agent.api.dependencies import get_report_use_case
from focused_research_agent.api.schemas.report.report import (
    ReportRequest,
    ReportResponse,
)
from focused_research_agent.database.database import get_db


report_router = APIRouter(tags=["report"])


@report_router.post(
    "/report", status_code=status.HTTP_200_OK, response_model=ReportResponse
)
def report(
    request: ReportRequest,
    db: Annotated[Session, Depends(get_db)],
    run_report_use_case: Annotated[Callable, Depends(get_report_use_case)],
) -> dict:
    """通过 API 处理报告生成请求。

    接受包含问题的经过验证的报告请求，
    执行深度研究报告用例，并返回
    结构化结果，答案字段中包含完整的降价报告。

    参数：
        请求：经过验证的报告请求负载。
        db：注入的 SQLAlchemy 数据库会话。
        run_report_use_case：注入的报告用例可调用。

    返回：
        dict：应用程序返回的结构化报告响应
            层。答案字段包含结构化降价
            简介、主要发现、分析和结论。"""

    return run_report_use_case(
        question=request.question,
        db=db,
    )
