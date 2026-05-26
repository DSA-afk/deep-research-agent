"""测试共享应用程序层研究用例。

这些测试验证初始状态创建、应用程序级输入
验证和标准化图形结果处理。"""

import pytest

import focused_research_agent.application.research_use_case as use_case_module
from focused_research_agent.application.exceptions import ApplicationError


class FakeGraph:
    """用于测试应用程序层用例的简单假图，无需
    调用真实的 LangGraph 工作流程。"""

    def invoke(self, initial_state: dict) -> dict:
        """返回固定的成功图形结果。

        参数：
            初始状态：传递到工作流程中的初始图形状态。

        返回：
            dict：模拟图结果。"""
        return {
            "run_id": "run-456",
            "question": initial_state["question"],
            "status": "completed",
            "scope": "Explain the topic clearly",
            "queries": ["query one", "query two", "query three"],
            "sources": [
                {
                    "title": "Test Source",
                    "url": "https://example.com/source",
                    "snippet": "A test source snippet.",
                    "source": "mock",
                    "score": 0.9,
                }
            ],
            "answer": "This is a synthesized answer.",
            "citations": ["https://example.com/source"],
            "errors": [],
        }


def fake_build_graph():
    """返回一个假图实例进行测试。

    返回：
        FakeGraph：假工作流对象。"""
    return FakeGraph()


def test_make_initial_state_returns_expected_shape():
    """验证初始研究状态是否包含预期的默认值
    价值观。"""
    result = use_case_module.make_initial_state("test question")

    assert result["run_id"] == ""
    assert result["question"] == "test question"
    assert result["scope"] is None
    assert result["assumptions"] is None
    assert result["constraints"] is None
    assert result["queries"] is None
    assert result["sources"] is None
    assert result["answer"] is None
    assert result["citations"] is None
    assert result["status"] == "started"
    assert result["errors"] == []
    assert result["debug"] is None
    assert result["conversation_id"] is None
    assert result["conversation_history"] is None


def test_research_question_raises_when_question_is_not_string():
    """当问题是时，验证用例是否引发 ApplicationError
    不是字符串。"""
    with pytest.raises(ApplicationError, match="User query must be a string"):
        use_case_module.research_question(123)  # type: ignore[arg-type]


def test_research_question_raises_when_question_is_blank():
    """当问题是时，验证用例是否引发 ApplicationError
    修剪空白后为空。"""
    with pytest.raises(ApplicationError, match="No user query provided"):
        use_case_module.research_question("   ")


def test_research_question_returns_normalized_graph_result(monkeypatch):
    """验证用例执行后是否返回标准化结果
    图表成功。"""
    monkeypatch.setattr(use_case_module, "build_graph", fake_build_graph)

    result = use_case_module.research_question("   test question   ")

    assert result["run_id"] == "run-456"
    assert result["question"] == "test question"
    assert result["status"] == "completed"
    assert result["scope"] == "Explain the topic clearly"
    assert result["queries"] == ["query one", "query two", "query three"]
    assert len(result["sources"]) == 1
    assert result["answer"] == "This is a synthesized answer."
    assert result["citations"] == ["https://example.com/source"]
    assert result["errors"] == []
