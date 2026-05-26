"""重点研究代理的查询生成节点。

该模块包含负责生成重点网络搜索的节点
来自范围问题的查询。它使用LLM提供商返回3到6
简短、多样、搜索引擎式的查询，直接支持回答
用户的研究问题。"""

import logging

from focused_research_agent.interfaces.llm_interface import LLMProvider
from focused_research_agent.state import ResearchState

logger = logging.getLogger(__name__)


def _build_generate_queries_prompt(state: ResearchState) -> str:
    """构建用于多查询搜索规划的 LLM 提示。

    参数：
        状态：包含范围问题的当前研究状态，
            原始问题、假设和约束。

    返回：
        str：指示LLM返回3到6重点的提示
            搜索引擎式查询作为严格的 JSON。"""
    scope = (state.get("scope") or "").strip()
    user_query = (state.get("question") or "").strip()
    assumptions = state.get("assumptions") or []
    constraints = state.get("constraints") or {}

    generate_queries_system_prompt = """
        仅返回有效的 JSON 格式。不要包含 markdown 标记、反引号或任何额外文本。
        必须且仅包含一个键："queries"。

        任务：
        - 生成 3 到 6 条搜索引擎风格的查询词（类似 Google 搜索的短语）。
        - 不要将研究范围原封不动地作为查询词。
        - 查询词必须具有多样性：每条查询应针对主题的不同方面。
        - 每条查询必须直接有助于回答用户的具体问题。
        - 不要生成与用户实际问题无关的泛主题查询。

        方面覆盖规则：
        - 首先，内部识别 4 到 6 个与研究范围和用户问题相关的关键方面。
        - 然后生成查询词，使每条查询聚焦于一个不同的方面。

        使用提供的输入信息：
        - 如果约束条件中包含地理或时间信息，请在相关查询词中包含这些限定词。
        - 保持每条查询词简短（通常 5 到 15 个词）。

        输出 JSON 格式：
        {
          "queries": ["查询词1", "查询词2", "查询词3"]
        }
        """.strip()

    inputs = f"研究范围：{scope}\n假设条件：{assumptions}\n约束条件：{constraints}"

    question_scope = f"""
        {generate_queries_system_prompt}

        {inputs}

        用户问题：
        {user_query}
        """.strip()

    return question_scope


def _clean_generated_queries(llm_queries: object) -> list[str]:
    """验证并清理 LLM 返回的原始查询列表。

    确保 LLM 响应是非空字符串列表，删除空白条目，
    强制执行至少 3 个有效查询，并限制6 个查询的结果。

    参数：
        llm_queries：从 LLM JSON 响应中提取的原始值
            “查询”键。

    返回：
        list[str]：清理后的 3 到 6 个非空查询字符串列表。

    加薪：
        ValueError：如果 llm_queries 不是列表，则包含非字符串
            项，或清理后产生少于 3 个有效查询。"""
    if not isinstance(llm_queries, list):
        raise ValueError("generate_queries: 'queries' must be a list")

    cleaned_list = []

    for item in llm_queries:
        if not isinstance(item, str):
            raise ValueError("generate_queries: Query item must be a string")

        item = item.strip()
        if item:
            cleaned_list.append(item)

    if len(cleaned_list) < 3:
        raise ValueError("generate_queries: LLM returned fewer than 3 valid queries")

    return cleaned_list[:6]


def generate_queries(state: ResearchState, llm_provider: LLMProvider) -> dict:
    """从范围内的问题生成有针对性的网络搜索查询。

    该节点使用LLM提供者产生3到6个短查询，
    直接支持回答的搜索引擎式查询
    用户的问题。

    参数：
        state：当前的研究状态。
        llm_provider：活动的 LLM 提供商实例。

    返回：
        dict：包含生成的查询和的部分状态更新
            状态，或错误字段（如果生成失败）。"""
    base = (state.get("scope") or state.get("question") or "").strip()
    run_id = state.get("run_id", "unknown")

    if not base:
        logger.error(
            "generate_queries: No scope or question available. run_id=%s", run_id
        )
        return {"errors": ["generate_queries: No scope or question available"]}

    question_scope = _build_generate_queries_prompt(state)

    try:
        response = llm_provider.generate_json(question_scope)
    except Exception as e:
        logger.exception("generate_queries failed. run_id=%s error=%s", run_id, e)
        return {"errors": [f"generate_queries failed: {e}"]}

    if not isinstance(response, dict) or "queries" not in response:
        return {"errors": ["generate_queries: Invalid response received from LLM"]}

    llm_queries = response["queries"]

    try:
        cleaned_list = _clean_generated_queries(llm_queries)
    except ValueError as e:
        logger.warning(
            "generate_queries: Query validation failed. run_id=%s error=%s", run_id, e
        )
        return {"errors": [str(e)]}

    logger.info("Queries generated. run_id=%s count=%d", run_id, len(cleaned_list))
    return {
        "queries": cleaned_list,
        "status": "planned",
    }
