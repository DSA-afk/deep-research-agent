"""测试 FastAPI 报告生成端点。

测试什么：
- POST /api/v1/report 返回结构化成功响应
- POST /api/v1/report 返回图形错误的错误响应形状
- POST /api/v1/report 拒绝无效问题 422
- POST /api/v1/report 对于应用程序错误返回 400
- POST /api/v1/report 对于意外异常返回 500
- POST /api/v1/report 答案包含结构化报告部分

如何测试：
- FastAPI 依赖覆盖用 fakes 替换 get_report_use_case
- 这里使用与 test_api_research.py 中使用的相同的 TestClient 模式
- 不需要数据库会话覆盖 - 报告用例在内部处理数据库

为什么它很重要：
- 验证报告传输层正确处理所有响应路径
- 确认结构化 Markdown 答案正确通过 API"""

from fastapi.testclient import TestClient

from focused_research_agent.api.app import create_app
from focused_research_agent.api.dependencies import get_report_use_case
from focused_research_agent.application.exceptions import ApplicationError

app = create_app()
client = TestClient(app)


# ---------------------------------------------------------------------------
# 假用例函数
# ---------------------------------------------------------------------------


def fake_success_report(question: str, db) -> dict:
    """返回成功的模拟报告响应。"""
    return {
        "run_id": "run-report-123",
        "question": question.strip(),
        "status": "completed",
        "scope": "Provide a comprehensive report on the topic",
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
        "answer": (
            "## Introduction\nThis is the introduction.\n"
            "## Key Findings\nThese are the key findings.\n"
            "## Analysis\nThis is the analysis.\n"
            "## Conclusion\nThis is the conclusion."
        ),
        "citations": [
            "https://example.com/source",
            "https://example.com/source2",
        ],
        "errors": [],
        "images": None,
    }


def fake_error_report(question: str, db) -> dict:
    """返回错误形状的模拟报告响应。"""
    return {
        "run_id": "run-report-error",
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


# ---------------------------------------------------------------------------
# POST /api/v1/report 测试成功
# ---------------------------------------------------------------------------


def test_report_returns_structured_success_response():
    """验证报告路由是否返回预期的结构化
    当用例提供成功结果时的成功响应。"""
    app.dependency_overrides[get_report_use_case] = lambda: fake_success_report

    try:
        response = client.post(
            "/api/v1/report",
            json={"question": "Tell me about quantum computing"},
        )

        assert response.status_code == 200

        data = response.json()

        assert data["run_id"] == "run-report-123"
        assert data["question"] == "Tell me about quantum computing"
        assert data["status"] == "completed"
        assert data["answer"] is not None
        assert data["errors"] == []
    finally:
        app.dependency_overrides.clear()


def test_report_answer_contains_structured_sections():
    """验证报告答案是否包含所有必需的四个内容
    结构化节标题。"""
    app.dependency_overrides[get_report_use_case] = lambda: fake_success_report

    try:
        response = client.post(
            "/api/v1/report",
            json={"question": "Tell me about quantum computing"},
        )

        assert response.status_code == 200

        answer = response.json()["answer"]

        assert "## Introduction" in answer
        assert "## Key Findings" in answer
        assert "## Analysis" in answer
        assert "## Conclusion" in answer
    finally:
        app.dependency_overrides.clear()


def test_report_returns_error_response_shape():
    """验证报告路由是否返回预期的错误形状
    当用例提供图形级错误结果时的响应。"""
    app.dependency_overrides[get_report_use_case] = lambda: fake_error_report

    try:
        response = client.post(
            "/api/v1/report",
            json={"question": "Trigger graph error"},
        )

        assert response.status_code == 200

        data = response.json()

        assert data["status"] == "error"
        assert data["answer"] is None
        assert data["errors"] == ["search_web: Tavily request failed"]
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /api/v1/report 验证测试
# ---------------------------------------------------------------------------


def test_report_rejects_empty_question():
    """验证报告路由是否拒绝空问题。"""
    response = client.post("/api/v1/report", json={"question": ""})

    assert response.status_code == 422


def test_report_rejects_whitespace_only_question():
    """验证报告路由是否拒绝仅包含空格的问题。"""
    response = client.post("/api/v1/report", json={"question": "   "})

    assert response.status_code == 422


def test_report_rejects_missing_question():
    """验证报告路由是否毫无疑问地拒绝请求。"""
    response = client.post("/api/v1/report", json={})

    assert response.status_code == 422


def test_report_rejects_punctuation_only_question():
    """验证报告路由是否拒绝仅标点符号输入。"""
    response = client.post("/api/v1/report", json={"question": "..."})

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/report 错误处理测试
# ---------------------------------------------------------------------------


def test_report_returns_structured_400_for_application_error():
    """验证报告路由是否返回集中式400错误
    当用例引发 ApplicationError 时的 JSON 形状。"""

    def fake_application_error_use_case(question: str, db) -> dict:
        raise ApplicationError("User query must not be empty")

    app.dependency_overrides[get_report_use_case] = lambda: (
        fake_application_error_use_case
    )

    try:
        response = client.post(
            "/api/v1/report",
            json={"question": "Valid looking question"},
        )

        assert response.status_code == 400
        assert response.json() == {
            "status_code": 400,
            "error": "application_error",
            "detail": "User query must not be empty",
            "path": "/api/v1/report",
        }
    finally:
        app.dependency_overrides.clear()


def test_report_returns_structured_500_for_unexpected_exception():
    """验证报告路由是否返回集中式500错误
    当用例引发意外异常时的 JSON 形状。"""

    def fake_unexpected_error_use_case(question: str, db) -> dict:
        raise RuntimeError("Unexpected test failure")

    app.dependency_overrides[get_report_use_case] = lambda: (
        fake_unexpected_error_use_case
    )

    local_client = TestClient(app, raise_server_exceptions=False)

    try:
        response = local_client.post(
            "/api/v1/report",
            json={"question": "Valid looking question"},
        )

        assert response.status_code == 500
        assert response.json() == {
            "status_code": 500,
            "error": "internal_server_error",
            "detail": "An unexpected internal error occurred",
            "path": "/api/v1/report",
        }
    finally:
        app.dependency_overrides.clear()
