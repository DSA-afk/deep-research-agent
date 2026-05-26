from typing import TypedDict


class ResearchState(TypedDict):
    run_id: str                              # 本次研究的唯一ID
    conversation_id: str | None              # 对话ID（多轮对话用）

    question: str                            # 用户的研究问题
    scope: str | None                        # 研究范围限定
    assumptions: list[str] | None            # 用户给定的假设条件
    constraints: dict | None                 # 约束条件
    mode: str                                # 模式（快速/深度等）

    queries: list[str] | None                # 搜索查询词列表
    sources: list[dict] | None               # 搜索到的信息来源
    images: list[str] | None                 # 相关图片

    answer: str | None                       # 最终答案
    citations: list[str] | None              # 引用列表

    status: str                              # 当前状态（进行中/完成/失败）
    errors: list[str]                        # 错误信息列表
    debug: dict | None                       # 调试信息
    conversation_history: list[dict] | None  # 对话历史