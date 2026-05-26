"""重点研究代理的问题范围节点。

该模块包含负责解释和范围界定的节点
用户的研究问题。它使用 LLM 提供商来生成
重点范围字符串、假设列表和约束字典
指导研究工作流程的其余部分。

如果 LLM 响应无效或缺少必需的密钥，则会出现错误
记录在状态中，并且图表路由到handle_error。"""

import logging

from focused_research_agent.interfaces.llm_interface import LLMProvider
from focused_research_agent.state import ResearchState


logger = logging.getLogger(__name__)


def scope_question(state: ResearchState, llm_provider: LLMProvider) -> dict:

    user_query = (state.get("question") or "").strip()
    run_id = state.get("run_id", "unknown")

    if not user_query:
        logger.error("scope_question: No user query provided. run_id=%s", run_id)
        return {"errors": ["scope_question: No user query provided"]}

    scope_question_system_prompt = """
    仅返回有效的 JSON 格式。不要包含 markdown 标记、反引号或任何额外文本。

    JSON 必须包含以下键：
    - scope（字符串）：对用户问题的聚焦解读和界定
    - assumptions（列表，包含 2 到 5 个简短字符串）：回答该问题所需的基本假设
    - constraints（字典，可以为空 {}）：回答时需要遵循的约束条件

    JSON 输出示例：
    {
      "scope": "解释加拿大的 RESP（注册教育储蓄计划）运作方式：供款、政府补贴、提款规则及常见误区",
      "assumptions": ["用户对 RESP 不熟悉", "加拿大背景"],
      "constraints": {"geography": "加拿大", "time_range": "当前", "depth": "入门级"}
    }
    """.strip()

    question_scope = f"""
    {scope_question_system_prompt}

    用户问题：
    {user_query}
    """.strip()

    try:
        response = llm_provider.generate_json(question_scope)
    except Exception as e:
        logger.exception("scope_question failed. run_id=%s error=%s", run_id, e)
        return {"errors": [f"scope_question failed: {e}"]}

    if not isinstance(response, dict):
        return {"errors": ["scope_question: Invalid response type received from LLM"]}

    if not all(key in response for key in ("scope", "assumptions", "constraints")):
        return {"errors": ["scope_question: Missing required keys in LLM response"]}

    scope = response.get("scope")
    assumptions = response.get("assumptions")
    constraints = response.get("constraints")

    if not isinstance(scope, str) or not scope.strip():
        return {"errors": ["scope_question: 'scope' must be a non-empty string"]}

    if not isinstance(assumptions, list):
        return {"errors": ["scope_question: 'assumptions' must be a list"]}

    cleaned_assumptions = []

    for item in assumptions:
        if not isinstance(item, str) or not item.strip():
            return {
                "errors": ["scope_question: Assumptions must contain non-empty strings"]
            }

        cleaned_assumptions.append(item.strip())

    if len(cleaned_assumptions) < 2 or len(cleaned_assumptions) > 5:
        return {"errors": ["scope_question: 'assumptions' must contain 2 to 5 items"]}

    if not isinstance(constraints, dict):
        return {"errors": ["scope_question: 'constraints' must be a dict"]}

    logger.info("Scope generated. run_id=%s scope='%s'", run_id, scope.strip()[:60])
    return {
        "scope": scope.strip(),
        "assumptions": cleaned_assumptions,
        "constraints": constraints,
        "status": "scoped",
    }
