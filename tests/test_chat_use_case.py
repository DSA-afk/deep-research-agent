"""应用程序层聊天用例的测试。

测试什么：
- 对于无效问题，execute_chat_turn 会引发 ApplicationError
- 如果没有提供，execute_chat_turn会生成一个新的conversation_id
-execute_chat_turn在后续操作中重用提供的conversation_id
-execute_chat_turn返回带有conversation_id和turn_number的结果
- 第一回合的execute_chat_turn将turn_number设置为1
-execute_chat_turn为后续回合正确设置turn_number
-execute_chat_turn将conversation_history传递给图状态
- 即使 save_run 失败，execute_chat_turn也会返回结果
- _build_chat_initial_state 正确填充对话字段

如何测试：
- 内存中的 SQLite 数据库用于完全集成式
  测试以便存储库调用可以正常工作而无需模拟
- build_graph 使用假图进行了修补，因此没有真正的 LLM 或搜索
  已拨打电话
- get_conversation_history 通过完整的间接测试
  execute_chat_turn流程

为什么它很重要：
- 验证应用层正确线程对话
  数据库和图表之间的上下文
- 确认持久性失败不会破坏研究结果"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

import focused_research_agent.application.chat_use_case as chat_use_case_module
from focused_research_agent.application.chat_use_case import (
    _build_chat_initial_state,
    execute_chat_turn,
)
from focused_research_agent.application.exceptions import ApplicationError
from focused_research_agent.database.models import Base
from focused_research_agent.database.repository import save_run


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


@pytest.fixture
def completed_state() -> dict:
    """返回真实的已完成研究状态以播种数据库。

    返回：
        dict：与规范化研究结果形状匹配的状态字典。"""
    return {
        "run_id": "run-seed-123",
        "question": "What is quantum computing?",
        "status": "completed",
        "scope": "Explain quantum computing clearly",
        "queries": ["quantum computing overview"],
        "sources": [
            {
                "title": "Quantum Overview",
                "url": "https://example.com/quantum",
                "snippet": "Quantum computing uses quantum mechanics.",
                "source": "tavily",
                "score": 0.95,
            }
        ],
        "answer": "Quantum computing uses quantum mechanical phenomena.",
        "citations": ["https://example.com/quantum"],
        "errors": [],
    }


class FakeGraph:
    """返回确定性完成结果的假 LangGraph 图
    无需拨打真正的法学硕士或搜索提供商电话。"""

    def invoke(self, initial_state: dict) -> dict:
        """返回固定的成功图形结果。

        参数：
            初始状态：传递到工作流程中的初始图形状态。

        返回：
            dict：模拟完成的图形结果。"""
        return {
            "run_id": "run-fake-456",
            "question": initial_state["question"],
            "status": "completed",
            "scope": "Explain the topic clearly",
            "assumptions": ["User is a beginner"],
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
            "answer": "This is a synthesized answer.",
            "citations": ["https://example.com/source"],
            "errors": [],
            "debug": None,
            "conversation_id": initial_state.get("conversation_id"),
            "conversation_history": initial_state.get("conversation_history"),
        }


def fake_build_graph():
    """返回一个 FakeGraph 实例进行测试。"""
    return FakeGraph()


# ---------------------------------------------------------------------------
# _build_chat_initial_state 测试
# ---------------------------------------------------------------------------


def test_build_chat_initial_state_sets_conversation_id():
    state = _build_chat_initial_state(
        question="What is AI?",
        conversation_id="conv-abc",
        conversation_history=None,
    )

    assert state["conversation_id"] == "conv-abc"


def test_build_chat_initial_state_sets_conversation_history():
    history = [{"turn": 1, "question": "Q1", "answer": "A1", "scope": "S1"}]

    state = _build_chat_initial_state(
        question="What is AI?",
        conversation_id="conv-abc",
        conversation_history=history,
    )

    assert state["conversation_history"] == history


def test_build_chat_initial_state_sets_none_history():
    state = _build_chat_initial_state(
        question="What is AI?",
        conversation_id="conv-abc",
        conversation_history=None,
    )

    assert state["conversation_history"] is None


def test_build_chat_initial_state_sets_question():
    state = _build_chat_initial_state(
        question="What is AI?",
        conversation_id="conv-abc",
        conversation_history=None,
    )

    assert state["question"] == "What is AI?"


# ---------------------------------------------------------------------------
# execute_chat_turn 验证测试
# ---------------------------------------------------------------------------


def test_execute_chat_turn_raises_for_empty_question(db, monkeypatch):
    monkeypatch.setattr(chat_use_case_module, "build_graph", fake_build_graph)

    with pytest.raises(ApplicationError, match="No user query provided"):
        execute_chat_turn(db=db, conversation_id=None, question="   ")


def test_execute_chat_turn_raises_for_non_string_question(db, monkeypatch):
    monkeypatch.setattr(chat_use_case_module, "build_graph", fake_build_graph)

    with pytest.raises(ApplicationError, match="User query must be a string"):
        execute_chat_turn(db=db, conversation_id=None, question=123)  # type: ignore


def test_execute_chat_turn_raises_for_punctuation_only_question(db, monkeypatch):
    monkeypatch.setattr(chat_use_case_module, "build_graph", fake_build_graph)

    with pytest.raises(ApplicationError):
        execute_chat_turn(db=db, conversation_id=None, question="...")


# ---------------------------------------------------------------------------
# execute_chat_turn 会话 ID 测试
# ---------------------------------------------------------------------------


def test_execute_chat_turn_generates_conversation_id_when_none(db, monkeypatch):
    monkeypatch.setattr(chat_use_case_module, "build_graph", fake_build_graph)

    result = execute_chat_turn(db=db, conversation_id=None, question="What is AI?")

    assert result["conversation_id"] is not None
    assert len(result["conversation_id"]) > 0


def test_execute_chat_turn_reuses_provided_conversation_id(db, monkeypatch):
    monkeypatch.setattr(chat_use_case_module, "build_graph", fake_build_graph)

    result = execute_chat_turn(
        db=db,
        conversation_id="conv-existing-123",
        question="What is AI?",
    )

    assert result["conversation_id"] == "conv-existing-123"


def test_execute_chat_turn_two_calls_with_none_generate_different_ids(db, monkeypatch):
    monkeypatch.setattr(chat_use_case_module, "build_graph", fake_build_graph)

    result1 = execute_chat_turn(db=db, conversation_id=None, question="What is AI?")
    result2 = execute_chat_turn(db=db, conversation_id=None, question="What is ML?")

    assert result1["conversation_id"] != result2["conversation_id"]


# ---------------------------------------------------------------------------
# execute_chat_turn 轮数测试
# ---------------------------------------------------------------------------


def test_execute_chat_turn_sets_turn_number_to_1_for_first_turn(db, monkeypatch):
    monkeypatch.setattr(chat_use_case_module, "build_graph", fake_build_graph)

    result = execute_chat_turn(db=db, conversation_id=None, question="What is AI?")

    assert result["turn_number"] == 1


def test_execute_chat_turn_sets_turn_number_to_2_for_follow_up(
    db, monkeypatch, completed_state
):
    monkeypatch.setattr(chat_use_case_module, "build_graph", fake_build_graph)

    save_run(db, completed_state, conversation_id="conv-abc", turn_number=1)

    result = execute_chat_turn(
        db=db,
        conversation_id="conv-abc",
        question="What are its limitations?",
    )

    assert result["turn_number"] == 2


# ---------------------------------------------------------------------------
# execute_chat_turn 结果形状测试
# ---------------------------------------------------------------------------


def test_execute_chat_turn_returns_expected_result_shape(db, monkeypatch):
    monkeypatch.setattr(chat_use_case_module, "build_graph", fake_build_graph)

    result = execute_chat_turn(db=db, conversation_id=None, question="What is AI?")

    assert "run_id" in result
    assert "question" in result
    assert "status" in result
    assert "answer" in result
    assert "conversation_id" in result
    assert "turn_number" in result


def test_execute_chat_turn_persists_run_to_database(db, monkeypatch):
    monkeypatch.setattr(chat_use_case_module, "build_graph", fake_build_graph)

    result = execute_chat_turn(db=db, conversation_id=None, question="What is AI?")

    from focused_research_agent.database.repository import get_conversation_turns

    turns = get_conversation_turns(db, result["conversation_id"])

    assert len(turns) == 1
    assert turns[0]["question"] == "What is AI?"


def test_execute_chat_turn_returns_result_even_when_save_fails(db, monkeypatch):
    monkeypatch.setattr(chat_use_case_module, "build_graph", fake_build_graph)

    from sqlalchemy.exc import SQLAlchemyError  # ← 添加导入

    def fake_save_run(*args, **kwargs):
        raise SQLAlchemyError(
            "Database write failed"
        )  # ← 将 RuntimeError 更改为 SQLAlchemyError

    monkeypatch.setattr(chat_use_case_module, "save_run", fake_save_run)

    result = execute_chat_turn(db=db, conversation_id=None, question="What is AI?")

    assert result["answer"] is not None
    assert result["status"] == "completed"
