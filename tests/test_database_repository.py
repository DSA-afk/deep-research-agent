"""数据库存储库层的测试。

测试什么：
- _serialize 和 _deserialize 辅助函数
- save_run 创建正确的 ConversationRun 行
- save_run仅在第1回合设置conversation_title
- get_conversation_history 按时间顺序返回回合
- get_conversation_history 尊重 max_turns 限制
- get_conversation_history 返回未知对话的空列表
- get_all_conversations 返回每个对话的一个条目
- get_all_conversations 首先返回最新的
- 当不存在数据时，get_all_conversations 返回空列表
- get_conversation_turns 返回带有反序列化字段的所有回合
- get_conversation_turns 返回未知对话的空列表

如何测试：
- 使用以下命令为每个测试全新创建内存中的 SQLite 数据库
  pytest 装置。这避免了对真实数据库文件的任何依赖
  并保证测试隔离——每个测试都从头开始。

为什么它很重要：
- 验证序列化、反序列化和所有 CRUD
  在应用层依赖之前操作就可以正常工作
  在他们身上。"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from focused_research_agent.database.models import Base, ConversationRun
from focused_research_agent.database.repository import (
    _deserialize,
    _serialize,
    get_all_conversations,
    get_conversation_history,
    get_conversation_turns,
    save_run,
)


# ---------------------------------------------------------------------------
# 测试夹具
# ---------------------------------------------------------------------------


@pytest.fixture
def db() -> Session:
    """为每个测试创建一个新的内存中 SQLite 数据库和会话。

    使用 SQLite 内存模式 (sqlite:///:memory:)，因此没有文件
    在磁盘上创建，数据库在以下情况下会自动销毁
    测试结束。在测试之前创建所有表并产生
    准备使用的会话。

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
def sample_state() -> dict:
    """返回一个现实的标准化研究状态字典进行测试。

    返回：
        dict：与返回的形状匹配的状态字典
            应用层的normalize_state函数。"""
    return {
        "run_id": "run-test-123",
        "question": "What is quantum computing?",
        "status": "completed",
        "scope": "Explain quantum computing clearly",
        "queries": [
            "quantum computing overview",
            "quantum computing applications",
            "quantum computing limitations",
        ],
        "sources": [
            {
                "title": "Quantum Computing Overview",
                "url": "https://example.com/quantum",
                "snippet": "Quantum computing uses quantum mechanics.",
                "source": "tavily",
                "score": 0.95,
            }
        ],
        "answer": "Quantum computing uses quantum mechanical phenomena.",
        "citations": ["https://example.com/quantum"],
        "errors": [],
        "images": [  # ← 添加此项
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg",
        ],
    }


@pytest.fixture
def sample_followup_state() -> dict:
    """返回真实的后续研究状态字典以进行测试
    多轮对话。

    返回：
        dict：对话中后续问题的状态字典。"""
    return {
        "run_id": "run-test-456",
        "question": "What are its limitations?",
        "status": "completed",
        "scope": "Explain quantum computing limitations",
        "queries": [
            "quantum computing limitations",
            "quantum computing challenges",
        ],
        "sources": [
            {
                "title": "Quantum Limitations",
                "url": "https://example.com/limits",
                "snippet": "Quantum computers face decoherence issues.",
                "source": "tavily",
                "score": 0.91,
            }
        ],
        "answer": "Quantum computing faces challenges like decoherence.",
        "citations": ["https://example.com/limits"],
        "errors": [],
    }


# ---------------------------------------------------------------------------
# 序列化助手测试
# ---------------------------------------------------------------------------


def test_serialize_returns_json_string_for_list():
    result = _serialize(["query one", "query two"])

    assert result == '["query one", "query two"]'


def test_serialize_returns_none_for_none():
    result = _serialize(None)

    assert result is None


def test_deserialize_returns_list_for_json_string():
    result = _deserialize('["query one", "query two"]')

    assert result == ["query one", "query two"]


def test_deserialize_returns_none_for_none():
    result = _deserialize(None)

    assert result is None


def test_serialize_then_deserialize_roundtrip():
    original = ["query one", "query two", "query three"]

    assert _deserialize(_serialize(original)) == original


# ---------------------------------------------------------------------------
# save_run 测试
# ---------------------------------------------------------------------------


def test_save_run_creates_row_in_database(db, sample_state):
    save_run(
        db, sample_state, conversation_id="conv-abc", turn_number=1, mode="research"
    )

    count = db.query(ConversationRun).count()

    assert count == 1


def test_save_run_returns_conversation_run_with_id(db, sample_state):
    result = save_run(
        db, sample_state, conversation_id="conv-abc", turn_number=1, mode="research"
    )

    assert isinstance(result, ConversationRun)
    assert result.id is not None


def test_save_run_stores_correct_field_values(db, sample_state):
    result = save_run(
        db, sample_state, conversation_id="conv-abc", turn_number=1, mode="research"
    )

    assert result.run_id == "run-test-123"
    assert result.question == "What is quantum computing?"
    assert result.status == "completed"
    assert result.scope == "Explain quantum computing clearly"
    assert result.answer == "Quantum computing uses quantum mechanical phenomena."
    assert result.conversation_id == "conv-abc"
    assert result.turn_number == 1


def test_save_run_sets_conversation_title_on_turn_1(db, sample_state):
    result = save_run(
        db, sample_state, conversation_id="conv-abc", turn_number=1, mode="research"
    )

    assert result.conversation_title == "What is quantum computing?"


def test_save_run_does_not_set_conversation_title_after_turn_1(
    db, sample_followup_state
):
    result = save_run(
        db,
        sample_followup_state,
        conversation_id="conv-abc",
        turn_number=2,
        mode="research",
    )

    assert result.conversation_title is None


def test_save_run_truncates_title_to_60_characters(db):
    long_question_state = {
        "run_id": "run-long",
        "question": "A" * 100,
        "status": "completed",
        "scope": None,
        "queries": None,
        "sources": None,
        "answer": None,
        "citations": None,
        "errors": [],
    }

    result = save_run(
        db,
        long_question_state,
        conversation_id="conv-abc",
        turn_number=1,
        mode="research",
    )

    assert len(result.conversation_title) == 60


def test_save_run_serializes_list_fields(db, sample_state):
    result = save_run(
        db, sample_state, conversation_id="conv-abc", turn_number=1, mode="research"
    )

    assert (
        result.queries
        == '["quantum computing overview", "quantum computing applications", "quantum computing limitations"]'
    )
    assert result.citations == '["https://example.com/quantum"]'
    assert result.errors == "[]"


def test_save_run_handles_none_list_fields(db):
    minimal_state = {
        "run_id": "run-minimal",
        "question": "What is AI?",
        "status": "error",
        "scope": None,
        "queries": None,
        "sources": None,
        "answer": None,
        "citations": None,
        "errors": ["init_run: No question provided"],
    }

    result = save_run(
        db, minimal_state, conversation_id="conv-xyz", turn_number=1, mode="research"
    )

    assert result.queries is None
    assert result.sources is None
    assert result.citations is None


def test_save_run_sets_created_at_and_updated_at(db, sample_state):
    result = save_run(
        db, sample_state, conversation_id="conv-abc", turn_number=1, mode="research"
    )

    assert result.created_at is not None
    assert result.updated_at is not None


# ---------------------------------------------------------------------------
# get_conversation_history 测试
# ---------------------------------------------------------------------------


def test_get_conversation_history_returns_turns_in_chronological_order(
    db, sample_state, sample_followup_state
):
    save_run(
        db, sample_state, conversation_id="conv-abc", turn_number=1, mode="research"
    )
    save_run(
        db,
        sample_followup_state,
        conversation_id="conv-abc",
        turn_number=2,
        mode="research",
    )

    history = get_conversation_history(db, conversation_id="conv-abc", max_turns=5)

    assert len(history) == 2
    assert history[0]["turn"] == 1
    assert history[1]["turn"] == 2


def test_get_conversation_history_returns_correct_fields(db, sample_state):
    save_run(
        db, sample_state, conversation_id="conv-abc", turn_number=1, mode="research"
    )

    history = get_conversation_history(db, conversation_id="conv-abc", max_turns=5)

    assert history[0]["question"] == "What is quantum computing?"
    assert (
        history[0]["answer"] == "Quantum computing uses quantum mechanical phenomena."
    )
    assert history[0]["scope"] == "Explain quantum computing clearly"


def test_get_conversation_history_respects_max_turns_limit(
    db, sample_state, sample_followup_state
):
    save_run(
        db, sample_state, conversation_id="conv-abc", turn_number=1, mode="research"
    )
    save_run(
        db,
        sample_followup_state,
        conversation_id="conv-abc",
        turn_number=2,
        mode="research",
    )

    history = get_conversation_history(db, conversation_id="conv-abc", max_turns=1)

    assert len(history) == 1
    assert history[0]["turn"] == 2


def test_get_conversation_history_returns_empty_list_for_unknown_conversation(
    db,
):
    history = get_conversation_history(
        db, conversation_id="conv-does-not-exist", max_turns=5
    )

    assert history == []


def test_get_conversation_history_only_returns_turns_for_given_conversation(
    db, sample_state, sample_followup_state
):
    save_run(
        db, sample_state, conversation_id="conv-abc", turn_number=1, mode="research"
    )
    save_run(
        db,
        sample_followup_state,
        conversation_id="conv-xyz",
        turn_number=1,
        mode="research",
    )

    history = get_conversation_history(db, conversation_id="conv-abc", max_turns=5)

    assert len(history) == 1
    assert history[0]["question"] == "What is quantum computing?"


# ---------------------------------------------------------------------------
# get_all_conversations 测试
# ---------------------------------------------------------------------------


def test_get_all_conversations_returns_empty_list_when_no_data(db):
    result = get_all_conversations(db)

    assert result == []


def test_get_all_conversations_returns_one_entry_per_conversation(
    db, sample_state, sample_followup_state
):
    save_run(
        db, sample_state, conversation_id="conv-abc", turn_number=1, mode="research"
    )
    save_run(
        db,
        sample_followup_state,
        conversation_id="conv-abc",
        turn_number=2,
        mode="research",
    )
    save_run(
        db, sample_state, conversation_id="conv-xyz", turn_number=1, mode="research"
    )

    result = get_all_conversations(db)

    assert len(result) == 2


def test_get_all_conversations_returns_correct_fields(db, sample_state):
    save_run(
        db, sample_state, conversation_id="conv-abc", turn_number=1, mode="research"
    )

    result = get_all_conversations(db)

    assert result[0]["conversation_id"] == "conv-abc"
    assert result[0]["title"] == "What is quantum computing?"
    assert "created_at" in result[0]


def test_get_all_conversations_returns_newest_first(
    db, sample_state, sample_followup_state
):
    save_run(
        db, sample_state, conversation_id="conv-first", turn_number=1, mode="research"
    )
    save_run(
        db,
        sample_followup_state,
        conversation_id="conv-second",
        turn_number=1,
        mode="research",
    )

    result = get_all_conversations(db)

    assert result[0]["conversation_id"] == "conv-second"
    assert result[1]["conversation_id"] == "conv-first"


# ---------------------------------------------------------------------------
# get_conversation_turns 测试
# ---------------------------------------------------------------------------


def test_get_conversation_turns_returns_empty_list_for_unknown_conversation(
    db,
):
    result = get_conversation_turns(db, conversation_id="conv-unknown")

    assert result == []


def test_get_conversation_turns_returns_all_turns_in_order(
    db, sample_state, sample_followup_state
):
    save_run(
        db, sample_state, conversation_id="conv-abc", turn_number=1, mode="research"
    )
    save_run(
        db,
        sample_followup_state,
        conversation_id="conv-abc",
        turn_number=2,
        mode="research",
    )

    result = get_conversation_turns(db, conversation_id="conv-abc")

    assert len(result) == 2
    assert result[0]["turn_number"] == 1
    assert result[1]["turn_number"] == 2


def test_get_conversation_turns_deserializes_list_fields(db, sample_state):
    save_run(
        db, sample_state, conversation_id="conv-abc", turn_number=1, mode="research"
    )

    result = get_conversation_turns(db, conversation_id="conv-abc")

    assert result[0]["queries"] == [
        "quantum computing overview",
        "quantum computing applications",
        "quantum computing limitations",
    ]
    assert result[0]["citations"] == ["https://example.com/quantum"]
    assert result[0]["errors"] == []


def test_get_conversation_turns_returns_correct_fields(db, sample_state):
    save_run(
        db, sample_state, conversation_id="conv-abc", turn_number=1, mode="research"
    )

    result = get_conversation_turns(db, conversation_id="conv-abc")

    assert result[0]["run_id"] == "run-test-123"
    assert result[0]["question"] == "What is quantum computing?"
    assert result[0]["status"] == "completed"
    assert result[0]["answer"] == "Quantum computing uses quantum mechanical phenomena."
    assert "created_at" in result[0]


def test_save_run_stores_mode_field(db, sample_state):
    result = save_run(
        db, sample_state, conversation_id="conv-abc", turn_number=1, mode="report"
    )
    assert result.mode == "report"


def test_get_all_reports_returns_empty_list_when_no_data(db):
    from focused_research_agent.database.repository import get_all_reports

    result = get_all_reports(db)
    assert result == []


def test_get_all_reports_returns_only_report_mode_runs(db, sample_state):
    from focused_research_agent.database.repository import get_all_reports

    save_run(
        db, sample_state, conversation_id="conv-chat", turn_number=1, mode="research"
    )
    save_run(
        db, sample_state, conversation_id="conv-report", turn_number=1, mode="report"
    )
    result = get_all_reports(db)
    assert len(result) == 1
    assert result[0]["conversation_id"] == "conv-report"


def test_get_all_reports_returns_correct_fields(db, sample_state):
    from focused_research_agent.database.repository import get_all_reports

    save_run(
        db, sample_state, conversation_id="conv-report", turn_number=1, mode="report"
    )
    result = get_all_reports(db)
    assert result[0]["conversation_id"] == "conv-report"
    assert result[0]["title"] == "What is quantum computing?"
    assert "created_at" in result[0]


def test_save_run_stores_and_retrieves_images(db, sample_state):
    """验证图像在保存和反序列化时是否已序列化
    检索转弯时正确。"""
    save_run(db, sample_state, conversation_id="conv-img", turn_number=1)

    turns = get_conversation_turns(db, "conv-img")

    assert turns[0]["images"] == [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg",
    ]


def test_save_run_handles_none_images(db, sample_state):
    """验证无图像是否得到妥善处理 - 存储为
    null 并返回为 None。"""
    sample_state["images"] = None
    save_run(db, sample_state, conversation_id="conv-no-img", turn_number=1)

    turns = get_conversation_turns(db, "conv-no-img")

    assert turns[0]["images"] is None

def test_get_all_conversations_excludes_report_runs(db, sample_state):
    save_run(db, sample_state, conversation_id="conv-chat", turn_number=1, mode="research")
    save_run(db, sample_state, conversation_id="conv-report", turn_number=1, mode="report")

    result = get_all_conversations(db)

    assert len(result) == 1
    assert result[0]["conversation_id"] == "conv-chat"