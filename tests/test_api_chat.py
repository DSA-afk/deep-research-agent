"""测试 FastAPI 聊天和对话端点。

测试什么：
- POST /api/v1/chat 返回结构化成功响应
- POST /api/v1/chat 返回图形错误的错误响应形状
- POST /api/v1/chat 拒绝 422 无效问题
- POST /api/v1/chat 对于应用程序错误返回 400
- POST /api/v1/chat 对于意外异常返回 500
- POST /api/v1/chat 接受可选的conversation_id
- GET /api/v1/conversations 返回对话列表
- GET /api/v1/conversations/{id} 返回对话轮次

如何测试：
- FastAPI 依赖覆盖用 fakes 替换 get_chat_use_case
- get_db 被内存中的 SQLite 会话覆盖
- 直接调用存储库函数来种子测试数据
- 这里使用与 test_api_research.py 中使用的相同的 TestClient 模式

为什么它很重要：
- 验证聊天传输层正确处理所有响应路径
- 确认回复中存在conversation_id和turn_number
- 确认对话端点返回正确形状的数据"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from focused_research_agent.api.app import create_app
from focused_research_agent.api.dependencies import get_chat_use_case
from focused_research_agent.application.exceptions import ApplicationError
from focused_research_agent.database.database import get_db
from focused_research_agent.database.models import Base
from focused_research_agent.database.repository import save_run

app = create_app()
client = TestClient(app)


# ---------------------------------------------------------------------------
# 面向会话端点测试的内存数据库测试
# ---------------------------------------------------------------------------


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite:///file::memory:?cache=shared&uri=true",
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
        # 在每个测试后清理所有行以防止交叉污染
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)


@pytest.fixture
def sample_state() -> dict:
    """返回真实的已完成研究状态以播种数据库。

    返回：
        dict：规范化的研究结果字典。"""
    return {
        "run_id": "run-test-123",
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


# ---------------------------------------------------------------------------
# 用于聊天端点测试的假用例函数
# ---------------------------------------------------------------------------


def fake_success_chat_turn(
    db: Session,
    conversation_id: str | None,
    question: str,
) -> dict:
    """返回成功的模拟聊天响应。"""
    return {
        "run_id": "run-chat-123",
        "question": question.strip(),
        "status": "completed",
        "scope": "Explain the topic clearly",
        "queries": ["query one", "query two", "query three"],
        "sources": [
            {
                "title": "Test Source",
                "url": "https://example.com/source",
                "snippet": "A test source snippet.",
                "source": "mock",
                "score": 0.95,
            }
        ],
        "answer": "This is a synthesized answer.",
        "citations": ["https://example.com/source"],
        "errors": [],
        "conversation_id": conversation_id or "conv-new-123",
        "turn_number": 1,
        "images": None,
    }


def fake_error_chat_turn(
    db: Session,
    conversation_id: str | None,
    question: str,
) -> dict:
    """返回错误形状的模拟聊天响应。"""
    return {
        "run_id": "run-chat-error",
        "question": question.strip(),
        "status": "error",
        "scope": None,
        "queries": None,
        "sources": None,
        "answer": None,
        "citations": None,
        "errors": ["search_web: Tavily request failed"],
        "conversation_id": conversation_id or "conv-error-123",
        "turn_number": 1,
        "images": None,
    }


# ---------------------------------------------------------------------------
# POST /api/v1/chat 测试
# ---------------------------------------------------------------------------


def test_chat_returns_structured_success_response():
    """验证聊天路由是否返回预期的结构化成功
    当用例提供成功结果时的响应。"""
    app.dependency_overrides[get_chat_use_case] = lambda: fake_success_chat_turn

    try:
        response = client.post(
            "/api/v1/chat",
            json={"question": "Tell me about AI"},
        )

        assert response.status_code == 200

        data = response.json()

        assert data["run_id"] == "run-chat-123"
        assert data["question"] == "Tell me about AI"
        assert data["status"] == "completed"
        assert data["conversation_id"] == "conv-new-123"
        assert data["turn_number"] == 1
        assert data["answer"] == "This is a synthesized answer."
        assert data["errors"] == []
    finally:
        app.dependency_overrides.clear()


def test_chat_returns_error_response_shape():
    """验证聊天路由是否返回预期的错误形状
    当用例提供图形级错误结果时的响应。"""
    app.dependency_overrides[get_chat_use_case] = lambda: fake_error_chat_turn

    try:
        response = client.post(
            "/api/v1/chat",
            json={"question": "Trigger graph error"},
        )

        assert response.status_code == 200

        data = response.json()

        assert data["status"] == "error"
        assert data["answer"] is None
        assert data["errors"] == ["search_web: Tavily request failed"]
        assert "conversation_id" in data
        assert "turn_number" in data
    finally:
        app.dependency_overrides.clear()


def test_chat_accepts_conversation_id_in_request():
    """验证聊天路由接受并通过
    来自请求正文的conversation_id。"""
    app.dependency_overrides[get_chat_use_case] = lambda: fake_success_chat_turn

    try:
        response = client.post(
            "/api/v1/chat",
            json={
                "question": "Tell me about AI",
                "conversation_id": "conv-existing-abc",
            },
        )

        assert response.status_code == 200
        assert response.json()["conversation_id"] == "conv-existing-abc"
    finally:
        app.dependency_overrides.clear()


def test_chat_rejects_empty_question():
    """验证聊天路由是否拒绝空问题。"""
    response = client.post("/api/v1/chat", json={"question": ""})

    assert response.status_code == 422


def test_chat_rejects_whitespace_only_question():
    """验证聊天路由是否拒绝仅包含空格的问题。"""
    response = client.post("/api/v1/chat", json={"question": "   "})

    assert response.status_code == 422


def test_chat_rejects_missing_question():
    """验证聊天路由是否毫无疑问地拒绝请求。"""
    response = client.post("/api/v1/chat", json={})

    assert response.status_code == 422


def test_chat_rejects_punctuation_only_question():
    """验证聊天路由是否拒绝仅标点符号输入。"""
    response = client.post("/api/v1/chat", json={"question": "..."})

    assert response.status_code == 422


def test_chat_returns_structured_400_for_application_error():
    """验证聊天路由是否返回集中式 400 错误 JSON
    当用例引发应用程序错误时的形状。"""

    def fake_application_error_use_case(
        db: Session,
        conversation_id: str | None,
        question: str,
    ) -> dict:
        raise ApplicationError("User query must not be empty")

    app.dependency_overrides[get_chat_use_case] = lambda: (
        fake_application_error_use_case
    )

    try:
        response = client.post(
            "/api/v1/chat",
            json={"question": "Valid looking question"},
        )

        assert response.status_code == 400
        assert response.json() == {
            "status_code": 400,
            "error": "application_error",
            "detail": "User query must not be empty",
            "path": "/api/v1/chat",
        }
    finally:
        app.dependency_overrides.clear()


def test_chat_returns_structured_500_for_unexpected_exception():
    """验证聊天路由是否返回集中式 500 错误 JSON
    当用例引发意外异常时形状。"""

    def fake_unexpected_error_use_case(
        db: Session,
        conversation_id: str | None,
        question: str,
    ) -> dict:
        raise RuntimeError("Unexpected test failure")

    app.dependency_overrides[get_chat_use_case] = lambda: fake_unexpected_error_use_case

    local_client = TestClient(app, raise_server_exceptions=False)

    try:
        response = local_client.post(
            "/api/v1/chat",
            json={"question": "Valid looking question"},
        )

        assert response.status_code == 500
        assert response.json() == {
            "status_code": 500,
            "error": "internal_server_error",
            "detail": "An unexpected internal error occurred",
            "path": "/api/v1/chat",
        }
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /api/v1/conversations 测试
# ---------------------------------------------------------------------------


def test_get_conversations_returns_empty_list_when_no_data(db_session):
    """验证 GET /conversations 在没有时返回空列表
    对话存在于数据库中。"""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        response = client.get("/api/v1/conversations")

        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.clear()


def test_get_conversations_returns_seeded_conversations(db_session, sample_state):
    """验证 GET /conversations 返回的对话是
    保存到数据库。"""
    save_run(db_session, sample_state, conversation_id="conv-abc", turn_number=1)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        response = client.get("/api/v1/conversations")

        assert response.status_code == 200

        data = response.json()

        assert len(data) == 1
        assert data[0]["conversation_id"] == "conv-abc"
        assert data[0]["title"] == "What is quantum computing?"
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /api/v1/conversations/{conversation_id} 测试
# ---------------------------------------------------------------------------


def test_get_conversation_returns_empty_list_for_unknown_id(db_session):
    """验证 GET /conversations/{id} 是否返回空列表
    对话不存在。"""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        response = client.get("/api/v1/conversations/conv-unknown")

        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.clear()


def test_get_conversation_returns_turns_for_existing_conversation(
    db_session, sample_state
):
    """验证 GET /conversations/{id} 是否返回某个回合的所有回合
    与反序列化列表字段的现有对话。"""
    save_run(db_session, sample_state, conversation_id="conv-abc", turn_number=1)

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        response = client.get("/api/v1/conversations/conv-abc")

        assert response.status_code == 200

        data = response.json()

        assert len(data) == 1
        assert data[0]["question"] == "What is quantum computing?"
        assert (
            data[0]["answer"] == "Quantum computing uses quantum mechanical phenomena."
        )
        assert data[0]["turn_number"] == 1
        assert data[0]["queries"] == ["quantum computing overview"]
    finally:
        app.dependency_overrides.clear()


def test_get_reports_returns_empty_list_when_no_data(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        response = client.get("/api/v1/reports")
        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.clear()


def test_get_reports_returns_seeded_reports(db_session, sample_state):
    from focused_research_agent.database.repository import save_run as repo_save_run

    repo_save_run(
        db_session,
        sample_state,
        conversation_id="conv-report",
        turn_number=1,
        mode="report",
    )

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        response = client.get("/api/v1/reports")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["conversation_id"] == "conv-report"
    finally:
        app.dependency_overrides.clear()
