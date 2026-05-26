"""测试 FastAPI 版本化 /research 端点。

这些测试验证请求验证、成功响应和错误形状
研究 API 路线的响应。它们覆盖 FastAPI 依赖项
由路由使用，以便测试可以专注于 API 行为而无需调用
真实的研究工作流程。"""

from fastapi.testclient import TestClient

from focused_research_agent.api.app import create_app
from focused_research_agent.api.dependencies import get_research_use_case
from focused_research_agent.application.exceptions import ApplicationError

app = create_app()
client = TestClient(app)


def fake_success_research_question(question: str) -> dict:
    """返回成功的模拟研究响应。

    参数：
        问题：向端点提供的用户研究问题。

    返回：
        dict：嘲笑成功的研究结果。"""
    return {
        "run_id": "run-123",
        "question": question.strip(),
        "status": "completed",
        "scope": "Explain the topic clearly",
        "queries": [
            "ai agents overview",
            "latest ai agent frameworks",
            "ai agent use cases",
        ],
        "sources": [
            {
                "title": "AI Agents Overview",
                "url": "https://example.com/overview",
                "snippet": "A high-level overview of AI agents.",
                "source": "mock",
                "score": 0.95,
            },
            {
                "title": "AI Agent Frameworks",
                "url": "https://example.com/frameworks",
                "snippet": "A summary of current AI agent frameworks.",
                "source": "mock",
                "score": 0.91,
            },
        ],
        "answer": "AI agents are systems that can plan and act toward goals.",
        "citations": [
            "https://example.com/overview",
            "https://example.com/frameworks",
        ],
        "errors": [],
        "images": None,
    }


def fake_error_research_question(question: str) -> dict:
    """返回错误形状的模拟研究响应。

    参数：
        问题：向端点提供的用户研究问题。

    返回：
        dict：模拟错误研究结果。"""
    return {
        "run_id": "run-999",
        "question": question.strip(),
        "status": "error",
        "scope": None,
        "queries": None,
        "sources": None,
        "answer": None,
        "citations": None,
        "errors": ["search_web: Tavily request failed"],
        "images": None,
    }


def test_research_returns_structured_success_response():
    """验证版本化研究路线是否返回预期的结构化
    当依赖性提供成功的研究时的成功响应
    结果。"""
    app.dependency_overrides[get_research_use_case] = lambda: (
        fake_success_research_question
    )

    try:
        response = client.post(
            "/api/v1/research",
            json={"question": "Tell me about AI agents"},
        )

        assert response.status_code == 200

        data = response.json()

        assert data["run_id"] == "run-123"
        assert data["question"] == "Tell me about AI agents"
        assert data["status"] == "completed"
        assert data["scope"] == "Explain the topic clearly"
        assert data["queries"] == [
            "ai agents overview",
            "latest ai agent frameworks",
            "ai agent use cases",
        ]
        assert len(data["sources"]) == 2
        assert data["sources"][0]["title"] == "AI Agents Overview"
        assert data["sources"][0]["url"] == "https://example.com/overview"
        assert (
            data["answer"]
            == "AI agents are systems that can plan and act toward goals."
        )
        assert data["citations"] == [
            "https://example.com/overview",
            "https://example.com/frameworks",
        ]
        assert data["errors"] == []
    finally:
        app.dependency_overrides.clear()


def test_research_returns_error_response_shape():
    """验证版本化研究路线是否返回预期的错误形状
    当依赖项提供图形样式错误结果时的响应。"""
    app.dependency_overrides[get_research_use_case] = lambda: (
        fake_error_research_question
    )

    try:
        response = client.post(
            "/api/v1/research",
            json={"question": "Trigger graph error"},
        )

        assert response.status_code == 200

        data = response.json()

        assert data["run_id"] == "run-999"
        assert data["question"] == "Trigger graph error"
        assert data["status"] == "error"
        assert data["scope"] is None
        assert data["queries"] is None
        assert data["sources"] is None
        assert data["answer"] is None
        assert data["citations"] is None
        assert data["errors"] == ["search_web: Tavily request failed"]
    finally:
        app.dependency_overrides.clear()


def test_research_rejects_empty_question():
    """验证版本化路由是否拒绝 API 上的空问题
    验证层。"""
    response = client.post("/api/v1/research", json={"question": ""})

    assert response.status_code == 422


def test_research_rejects_whitespace_only_question():
    """验证版本化路由是否拒绝仅包含空格的问题
    API验证层。"""
    response = client.post("/api/v1/research", json={"question": "   "})

    assert response.status_code == 422


def test_research_rejects_missing_question():
    """Verify that the versioned route rejects a request body with no question
    场。"""
    response = client.post("/api/v1/research", json={})

    assert response.status_code == 422


def test_research_rejects_wrong_question_type():
    """验证版本化路由是否拒绝问题具有以下内容的请求
    类型错误。"""
    response = client.post("/api/v1/research", json={"question": 123})

    assert response.status_code == 422


def test_research_rejects_punctuation_only_question():
    """验证版本化路由是否拒绝 API 中仅标点符号的输入
    验证层。"""
    response = client.post("/api/v1/research", json={"question": "."})

    assert response.status_code == 422


def test_research_rejects_ultra_short_question():
    """验证版本化路由是否拒绝无意义的超短输入
    API验证层。"""
    response = client.post("/api/v1/research", json={"question": "a"})

    assert response.status_code == 422


def test_research_returns_structured_400_for_application_error():
    """第400章 验证版本化研究路线是否返回集中式
    当注入的用例引发 ApplicationError 时，错误 JSON 形状。"""

    def fake_application_error_use_case(question: str) -> dict:
        raise ApplicationError("User query must not be empty")

    app.dependency_overrides[get_research_use_case] = lambda: (
        fake_application_error_use_case
    )

    try:
        response = client.post(
            "/api/v1/research",
            json={"question": "Valid looking question"},
        )

        assert response.status_code == 400
        assert response.json() == {
            "status_code": 400,
            "error": "application_error",
            "detail": "User query must not be empty",
            "path": "/api/v1/research",
        }
    finally:
        app.dependency_overrides.clear()


def test_research_returns_structured_500_for_unexpected_exception():
    """验证版本化研究路线是否返回集中式 500
    当注入的用例引发意外情况时，出现错误 JSON 形状
    例外。"""

    def fake_unexpected_error_use_case(question: str) -> dict:
        raise RuntimeError("Unexpected test failure")

    app.dependency_overrides[get_research_use_case] = lambda: (
        fake_unexpected_error_use_case
    )

    local_client = TestClient(app, raise_server_exceptions=False)

    try:
        response = local_client.post(
            "/api/v1/research",
            json={"question": "Valid looking question"},
        )

        assert response.status_code == 500
        assert response.json() == {
            "status_code": 500,
            "error": "internal_server_error",
            "detail": "An unexpected internal error occurred",
            "path": "/api/v1/research",
        }
    finally:
        app.dependency_overrides.clear()
