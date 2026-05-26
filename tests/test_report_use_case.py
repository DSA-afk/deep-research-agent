"""应用层报告用例的测试。

测试什么：
- 对于无效问题，execute_report 会引发 ApplicationError
-execute_report 在图形状态下将模式设置为“报告”
-execute_report 使用 search_depth='advanced' 调用 build_graph
-execute_report 返回标准化结果字典
-execute_report 将运行持久保存到数据库
- 即使 save_run 失败，execute_report也会返回结果

如何测试：
- 内存中的 SQLite 数据库用于集成式测试
- build_graph 使用返回确定性结果的假图进行了修补
- 假图捕获了初始状态，因此我们可以断言模式和搜索深度

为什么它很重要：
- 验证报告用例正确配置图表
- 确认在图形调用之前设置了 mode='report'
- 确认使用高级搜索深度
- 确认非阻塞持久性正常工作"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

import focused_research_agent.application.report_use_case as report_use_case_module
from focused_research_agent.application.exceptions import ApplicationError
from focused_research_agent.application.report_use_case import execute_report
from focused_research_agent.database.models import Base


# ---------------------------------------------------------------------------
# 测试夹具
# ---------------------------------------------------------------------------


@pytest.fixture
def db() -> Session:
    """为每个测试创建一个新的内存中 SQLite 数据库和会话。

    产量：
        会话：连接到的活动 SQLAlchemy 会话
            内存数据库。"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# 用于测试的假图
# ---------------------------------------------------------------------------


class FakeGraph:
    """捕获初始状态并返回的假 LangGraph 图
    确定性的完成结果，无需进行真正的法学硕士或
    搜索提供商的电话。"""

    def __init__(self):
        self.captured_initial_state = None

    def invoke(self, initial_state: dict) -> dict:
        """捕获初始状态并返回固定的成功结果。

        参数：
            初始状态：传递到工作流程中的初始图形状态。

        返回：
            dict：模拟完成的图形结果。"""
        self.captured_initial_state = initial_state
        return {
            "run_id": "run-report-fake-456",
            "question": initial_state["question"],
            "status": "completed",
            "scope": "A detailed report on the topic",
            "assumptions": [],
            "constraints": {},
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
            "answer": (
                "## Introduction\nThis is the introduction.\n"
                "## Key Findings\nThese are the key findings.\n"
                "## Analysis\nThis is the analysis.\n"
                "## Conclusion\nThis is the conclusion."
            ),
            "citations": ["https://example.com/source"],
            "errors": [],
            "debug": None,
            "conversation_id": None,
            "conversation_history": None,
            "mode": initial_state.get("mode"),
        }


_fake_graph_instance = None


def fake_build_graph(search_depth: str | None = None):
    """返回一个FakeGraph实例并记录使用的search_深度。

    参数：
        search_depth：用例传递的搜索深度。

    返回：
        FakeGraph: A fake graph instance."""
    global _fake_graph_instance
    _fake_graph_instance = FakeGraph()
    _fake_graph_instance.search_depth_used = search_depth
    return _fake_graph_instance


# ---------------------------------------------------------------------------
# 验证测试
# ---------------------------------------------------------------------------


def test_execute_report_raises_for_empty_question(db, monkeypatch):
    monkeypatch.setattr(report_use_case_module, "build_graph", fake_build_graph)

    with pytest.raises(ApplicationError, match="No user query provided"):
        execute_report(question="   ", db=db)


def test_execute_report_raises_for_non_string_question(db, monkeypatch):
    monkeypatch.setattr(report_use_case_module, "build_graph", fake_build_graph)

    with pytest.raises(ApplicationError, match="User query must be a string"):
        execute_report(question=123, db=db)  # type: ignore


def test_execute_report_raises_for_punctuation_only_question(db, monkeypatch):
    monkeypatch.setattr(report_use_case_module, "build_graph", fake_build_graph)

    with pytest.raises(ApplicationError):
        execute_report(question="...", db=db)


# ---------------------------------------------------------------------------
# 模式和搜索深度测试
# ---------------------------------------------------------------------------


def test_execute_report_sets_mode_to_report(db, monkeypatch):
    """验证execute_report在初始状态下设置mode='report'
    在调用图表之前。"""
    monkeypatch.setattr(report_use_case_module, "build_graph", fake_build_graph)

    execute_report(question="What is quantum computing?", db=db)

    assert _fake_graph_instance is not None
    assert _fake_graph_instance.captured_initial_state["mode"] == "report"


def test_execute_report_uses_advanced_search_depth(db, monkeypatch):
    """验证execute_report是否调用build_graph
    search_depth='高级'。"""
    monkeypatch.setattr(report_use_case_module, "build_graph", fake_build_graph)

    execute_report(question="What is quantum computing?", db=db)

    assert _fake_graph_instance is not None
    assert _fake_graph_instance.search_depth_used == "advanced"


# ---------------------------------------------------------------------------
# 结果形状测试
# ---------------------------------------------------------------------------


def test_execute_report_returns_expected_result_shape(db, monkeypatch):
    monkeypatch.setattr(report_use_case_module, "build_graph", fake_build_graph)

    result = execute_report(question="What is quantum computing?", db=db)

    assert "run_id" in result
    assert "question" in result
    assert "status" in result
    assert "answer" in result
    assert "citations" in result
    assert "errors" in result


def test_execute_report_answer_contains_report_sections(db, monkeypatch):
    """验证报告答案是否包含预期的结构化
    节标题。"""
    monkeypatch.setattr(report_use_case_module, "build_graph", fake_build_graph)

    result = execute_report(question="What is quantum computing?", db=db)

    assert "## Introduction" in result["answer"]
    assert "## Key Findings" in result["answer"]
    assert "## Analysis" in result["answer"]
    assert "## Conclusion" in result["answer"]


# ---------------------------------------------------------------------------
# 持久性测试
# ---------------------------------------------------------------------------


def test_execute_report_persists_run_to_database(db, monkeypatch):
    """验证execute_report是否将完成的报告运行保存到
    数据库。"""
    monkeypatch.setattr(report_use_case_module, "build_graph", fake_build_graph)

    execute_report(question="What is quantum computing?", db=db)

    from focused_research_agent.database.models import ConversationRun

    count = db.query(ConversationRun).count()
    assert count == 1


def test_execute_report_returns_result_even_when_save_fails(db, monkeypatch):
    """验证即使数据库存在，execute_report 也返回结果
    坚持失败。"""
    monkeypatch.setattr(report_use_case_module, "build_graph", fake_build_graph)

    from sqlalchemy.exc import SQLAlchemyError

    def fake_save_run(*args, **kwargs):
        raise SQLAlchemyError("Database write failed")

    monkeypatch.setattr(report_use_case_module, "save_run", fake_save_run)

    result = execute_report(question="What is quantum computing?", db=db)

    assert result["answer"] is not None
    assert result["status"] == "completed"
