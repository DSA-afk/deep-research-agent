"""重点研究代理的答案合成节点。

该模块包含负责合成最终答案的节点
来自收集和排名的网络资源。它支持两种模式：

- 研究：使用 1 至 3 次引用得出简洁的答案
  排名靠前的来源。包括可用的对话历史记录上下文
  用于多轮聊天会话。

- 报告：生成结构化的长格式 Markdown 报告，其中包含四个内容
  部分（简介、主要发现、分析、结论）和 3 至 5
  使用更大的源集的引用。

来源之前经过域信任分数的验证、标准化和排名
正在被传递到LLM。 LLM 返回的引文 URL 已验证
在存储在状态之前，根据允许的源集进行标准化。"""

import logging
from urllib.parse import urlparse

from focused_research_agent.interfaces.llm_interface import LLMProvider
from focused_research_agent.state import ResearchState

logger = logging.getLogger(__name__)

INVALID_LLM_RESPONSE_ERROR_MESSAGE = "Invalid response obtained from LLM"
_REPORT_MAX_SOURCES = 15
_RESEARCH_MAX_SOURCES = 6

# 这是一种轻量级排序启发式方法，而不是完整的信任系统
_DOMAIN_BONUSES = {
    "britannica.com": 3.0,
    "timeanddate.com": 3.0,
    "metoffice.gov.uk": 3.0,
    "weather.gov": 3.0,
    "noaa.gov": 3.0,
}

_DOMAIN_PENALTIES = {
    "youtube.com": -3.0,
    "medium.com": -3.0,
    "reddit.com": -3.0,
    "quora.com": -3.0,
    "facebook.com": -3.0,
    "tiktok.com": -3.0,
    "instagram.com": -3.0,
}


def _extract_domain(url: str) -> str:
    """从 URL 中提取并规范化域名。"""
    domain = urlparse(url).netloc.lower().strip()

    if domain.startswith("www."):
        domain = domain[4:]

    return domain


def _matches_domain(domain: str, target: str) -> bool:
    """返回域是否匹配目标或者是目标的子域。"""
    return domain == target or domain.endswith("." + target)


def _get_domain_bonus(domain: str) -> float:
    """返回域名的轻量级排名奖励或惩罚。

    这是一个简单的启发式，用于稍微喜欢更强的
    参考风格的领域和稍微降级的较弱的领域。"""
    if domain.endswith(".gov"):
        return 4.0

    if domain.endswith(".edu"):
        return 3.5

    for trusted_domain, bonus in _DOMAIN_BONUSES.items():
        if _matches_domain(domain, trusted_domain):
            return bonus

    for weak_domain, penalty in _DOMAIN_PENALTIES.items():
        if _matches_domain(domain, weak_domain):
            return penalty

    return 0.0


def _get_rank_score(source: dict) -> float:
    """计算源的最终排名分数。

    该分数将提供商分数与基于小型域的分数相结合
    启发式的。"""
    domain = _extract_domain(source["url"])
    bonus = _get_domain_bonus(domain)
    return source["score"] + bonus


def _collect_valid_sources(sources: list[dict]) -> list[dict]:
    """验证、规范化和排序候选源以进行综合。

    参数：
        来源：来自研究状态的原始来源项目。

    返回：
        list[dict]: 包含标题、url、的排名源词典
        片段、来源和分数。"""

    valid_sources = []

    for item in sources:
        if not isinstance(item, dict):
            continue

        title = (item.get("title") or "").strip()
        url = (item.get("url") or "").strip()
        snippet = (item.get("snippet") or "").strip()
        source_name = (item.get("source") or "").strip()
        score = item.get("score", 0.0)

        if not title or not url or not snippet:
            continue

        try:
            score = float(score)
        except (TypeError, ValueError):
            score = 0.0

        valid_sources.append(
            {
                "title": title,
                "url": url,
                "snippet": snippet,
                "source": source_name,
                "score": score,
            }
        )

    if not valid_sources:
        return []

    return sorted(valid_sources, key=_get_rank_score, reverse=True)


def _build_synthesis_prompt(
    question: str, sources: list[dict], conversation_history: list[dict] | None
) -> str:
    """构建 LLM 提示以进行最终答案综合。

    包括可用的对话历史记录上下文，以便法学硕士
    回答后续问题时可以参考之前的回合。当
    conversation_history 为 None 或为空，提示与
    单轮研究流程。

    参数：
        问题：原始用户问题。
        来源：选择用于合成的排名源词典。
        conversation_history：之前的对话从
            应用层，或无用于单轮研究。
            每个项目都包含回合、问题、答案和范围键。

    返回：
        str：指示LLM返回简洁答案的提示
            以及 1 到 3 个严格 JSON 形式的精确引用 URL。"""

    source_blocks = []

    for index, source in enumerate(sources, start=1):
        source_block = (
            f"来源 {index}\n"
            f"标题：{source['title']}\n"
            f"链接：{source['url']}\n"
            f"摘要：{source['snippet']}\n"
        )
        source_blocks.append(source_block)

    joined_sources = "\n".join(source_blocks)

    conversation_context = ""
    if conversation_history:
        context_lines = ["对话历史："]
        for turn in conversation_history:
            context_lines.append(f"第 {turn['turn']} 轮 — 问：{turn['question']}")
            context_lines.append(f"         答：{turn['answer']}")
        context_lines.append(
            "\n请在上述对话历史的上下文中回答当前问题（如相关）。"
        )
        conversation_context = "\n".join(context_lines) + "\n\n"

    return f"""{conversation_context}仅返回有效的 JSON 格式。不要包含 markdown 标记、反引号或任何额外文本。

            JSON 必须包含以下键：
            - answer（字符串）：对用户问题的回答
            - citations（列表，包含 1 到 3 个 URL）：引用来源

            规则：
            - 在第一句话中直接回答用户的问题。
            - 然后补充 2 到 3 句简短的支撑说明。
            - 保持回答清晰、自然、简洁。
            - 避免重复表述。
            - 优先选择最权威、最可信的来源。
            - 优先使用官方、教育、科学或知名参考来源（如有）。
            - 仅使用下方提供的资料来源。
            - 不要编造事实。
            - 不要编造引用链接。
            - 每个引用 URL 必须与下方提供的资料来源 URL 完全匹配。
            - 选择最佳的 2 到 3 个引用，而非随意选择。
            - 不要在回答中提及"来源"、"摘要"或"引用"等字眼。

            JSON 输出示例：
            {{
                "answer": "二分日是昼夜几乎等长的日子，而至日是太阳到达天空最高或最低点的日子，形成一年中最长或最短的白天。二分日标志着春季和秋季的开始。至日标志着夏季和冬季的开始。",
                "citations": [
                "https://example.com/source1",
                "https://example.com/source2"
                ]
            }}

用户问题：
{question}

资料来源：
{joined_sources}
""".strip()


def _build_report_prompt(question: str, sources: list[dict]) -> str:
    """构建 LLM 提示以生成结构化报告。

    指示法学硕士制作一份长篇研究报告
    四个部分：简介、主要发现、分析和
    结论。使用所有可用来源进行全面覆盖。

    参数：
        问题：原始用户问题。
        来源：选择用于合成的排名源词典。

    返回：
        str：指示 LLM 返回结构化的提示
            markdown 报告和 3 到 5 个引用 URL 作为严格的 JSON。"""
    source_blocks = []

    for index, source in enumerate(sources, start=1):
        source_block = (
            f"来源 {index}\n"
            f"标题：{source['title']}\n"
            f"链接：{source['url']}\n"
            f"摘要：{source['snippet']}\n"
        )
        source_blocks.append(source_block)

    joined_sources = "\n".join(source_blocks)

    return f"""仅返回有效的 JSON 格式，必须包含以下键：
    - answer（字符串）：一份完整的结构化研究报告，使用 markdown 格式，包含以下章节：
    ## 引言
    ## 主要发现
    ## 分析
    ## 结论
    - citations（列表，包含 3 到 5 个 URL）：引用来源

    规则：
    - 每个章节必须恰好写 3 个实质性段落
    - 每段至少 4 句话
    - 不同章节之间绝不能重复相同的句子或观点
    - 每个章节必须包含不同类型的内容：
        * 引言：仅包含背景介绍和上下文信息
        * 主要发现：仅包含具体发现和数据要点
        * 分析：仅包含影响分析、对比和批判性审视
        * 结论：仅包含重要性总结和未来展望
    - 内容要全面详尽
    - 使用所有提供的资料来源
    - 每个论点都必须有资料来源支持
    - 不要编造事实或引用链接
    - 每个引用 URL 必须与提供的资料来源 URL 完全匹配
    - 不要在回答中提及"来源"、"摘要"或"引用"等字眼


    JSON 输出示例：
    {{
      "answer": "## 引言\\n\\n二分日和至日是地球公转轨道上的重要天文现象...\\n\\n## 主要发现\\n\\n...",
      "citations": [
        "https://example.com/source1",
        "https://example.com/source2"
      ]
    }}

    用户问题：
    {question}

    资料来源：
    {joined_sources}
    """.strip()


def _validate_synthesis_response(response: object) -> tuple[str, list]:
    """验证原始 LLM 综合响应。

    参数：
        响应：LLM 提供商返回的原始对象。

    返回：
        tuple[str, list]：经过验证的答案字符串和原始引用列表。

    加薪：
        ValueError：如果响应形状无效或为必填字段
            缺失/为空。"""

    if not isinstance(response, dict):
        raise ValueError(INVALID_LLM_RESPONSE_ERROR_MESSAGE)

    answer = response.get("answer")
    citations = response.get("citations")

    if not isinstance(answer, str) or not answer.strip():
        raise ValueError(INVALID_LLM_RESPONSE_ERROR_MESSAGE)

    if not isinstance(citations, list) or not citations:
        raise ValueError(INVALID_LLM_RESPONSE_ERROR_MESSAGE)
    return (answer, citations)


def _normalize_url(url: str) -> str:
    """通过去除尾部斜杠来标准化 URL 以进行比较。"""
    return url.strip().rstrip("/").lower()


def _clean_citations(citations: list, allowed_urls: set[str]) -> list[str]:
    """验证、删除重复并过滤返回的引文。

    参数：
        引用：法学硕士返回的原始引用。
        allowed_urls：允许 LLM 引用的源 URL 集。

    返回：
        list[str]：清理后的引用最多仅限 3 项。

    加薪：
        ValueError：如果引用格式错误、为空或包含 URL
            在允许的源集之外。"""

    normalized_allowed = {}
    for url in allowed_urls:
        normalized_allowed[_normalize_url(url)] = url
    cleaned_citations = []
    seen_citations = set()

    for citation in citations:
        if not isinstance(citation, str):
            raise ValueError("Citation must be a string")

        citation = citation.strip()

        if not citation:
            raise ValueError("Empty citation returned by LLM")

        normalized_citation = _normalize_url(citation)
        if normalized_citation not in normalized_allowed:
            raise ValueError(
                f"synthesize_answer: LLM returned unknown citation URL: {citation}"
            )

        original_url = normalized_allowed[normalized_citation]
        if original_url not in seen_citations:
            seen_citations.add(original_url)
            cleaned_citations.append(original_url)

    if not cleaned_citations:
        raise ValueError("No valid citations found")
    return cleaned_citations


def synthesize_answer(state: ResearchState, llm_provider: LLMProvider) -> dict:
    """从收集的来源中综合最终答案和引文。

    该节点验证可用源，构建综合提示，
    向法学硕士请求结构化输出，并验证所有返回的内容
    引用来自提供的源集。

    参数：
        state：当前的研究状态。
        llm_provider：活动的 LLM 提供商实例。

    返回：
        dict：部分状态更新，包含答案、引文和
        状态，或者如果综合失败则显示错误字段。"""
    mode = state.get("mode")
    question = (state.get("question") or "").strip()
    sources = state.get("sources")
    conversation_history = state.get("conversation_history")
    run_id = state.get("run_id", "unknown")

    if not question:
        logger.error("synthesize_answer: No question found. run_id=%s", run_id)
        return {"errors": ["synthesize_answer: No question found"]}

    if not isinstance(sources, list) or not sources:
        logger.error("synthesize_answer: No sources found. run_id=%s", run_id)
        return {"errors": ["synthesize_answer: No sources found"]}

    valid_sources = _collect_valid_sources(sources)

    if not valid_sources:
        logger.warning(
            "synthesize_answer: No valid sources after filtering. run_id=%s", run_id
        )
        return {"errors": ["synthesize_answer: No valid sources found"]}

    if mode == "report":
        synthesis_sources = valid_sources[:_REPORT_MAX_SOURCES]
    else:
        synthesis_sources = valid_sources[:_RESEARCH_MAX_SOURCES]

    allowed_urls = {source["url"] for source in synthesis_sources}

    if mode == "report":
        prompt = _build_report_prompt(question, synthesis_sources)
    else:
        prompt = _build_synthesis_prompt(
            question, synthesis_sources, conversation_history
        )

    try:
        response = llm_provider.generate_json(prompt)
    except Exception as e:
        logger.exception("synthesize_answer failed. run_id=%s error=%s", run_id, e)
        return {"errors": [f"synthesize_answer failed: {e}"]}

    try:
        answer, citations = _validate_synthesis_response(response)
        cleaned_citations = _clean_citations(citations, allowed_urls)
    except ValueError as e:
        logger.exception(
            "synthesize_answer: Validation failed. run_id=%s error=%s", run_id, e
        )
        return {"errors": [str(e)]}

    logger.info(  # ← 添加
        "Synthesis completed. run_id=%s mode=%s citations=%d",
        run_id,
        mode,
        len(cleaned_citations),
    )
    max_citations = 5 if mode == "report" else 3
    return {
        "answer": answer.strip(),
        "citations": cleaned_citations[:max_citations],
        "status": "synthesized",
    }
