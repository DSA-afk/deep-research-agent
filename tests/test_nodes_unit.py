from focused_research_agent.nodes.finalize_run import finalize_run
from focused_research_agent.nodes.generate_queries import generate_queries
from focused_research_agent.nodes.handle_error import handle_error
from focused_research_agent.nodes.init_run import initialize_state
from focused_research_agent.nodes.scope_question import scope_question
from focused_research_agent.nodes.search_web import search_web
from focused_research_agent.nodes.synthesize_answer import synthesize_answer
from focused_research_agent.state import ResearchState

"""
Unit tests for individual workflow nodes.

What is tested:
- success and expected error-state behavior for core nodes:
  init_run, scope_question, generate_queries, search_web,
  synthesize_answer, finalize_run, and handle_error

How it is tested:
- each node is called directly with controlled input state
- fake LLM/search providers are used where needed
- node outputs are checked without running the whole graph

Why it matters:
- validates node behavior in isolation
- makes debugging easier than relying only on full graph tests
- supports the state-based Option B error model
"""


def make_initial_state(question: str) -> ResearchState:
    return {
        "run_id": "",
        "question": question,
        "scope": None,
        "assumptions": None,
        "constraints": None,
        "queries": None,
        "sources": None,
        "answer": None,
        "citations": None,
        "status": "started",
        "errors": [],
        "debug": None,
        "conversation_id": None,
        "conversation_history": None,
        "mode": "research",  # ← 修复：之前是str（类型），应为“research”（值）
        "images": None,
    }


class FakeScopeLLMProvider:
    def generate_json(self, prompt: str) -> dict:
        return {
            "scope": "Explain the test topic clearly",
            "assumptions": ["User is a beginner", "General context"],
            "constraints": {"geography": "Global", "depth": "intro"},
        }


class FakeQueriesLLMProvider:
    def generate_json(self, prompt: str) -> dict:
        return {
            "queries": [
                "test topic overview",
                "test topic rules",
                "test topic examples",
            ]
        }


class FakeTooFewQueriesLLMProvider:
    def generate_json(self, prompt: str) -> dict:
        return {
            "queries": [
                "only one query",
                "only two queries",
            ]
        }


class FakeSynthesisLLMProvider:
    def generate_json(self, prompt: str) -> dict:
        return {
            "answer": (
                "The test topic can be understood through its overview, "
                "key rules, and common pitfalls."
            ),
            "citations": [
                "https://example.com/overview",
                "https://example.com/rules",
            ],
        }


class FakeBadCitationLLMProvider:
    def generate_json(self, prompt: str) -> dict:
        return {
            "answer": "This answer includes an invalid citation.",
            "citations": [
                "https://example.com/not-allowed",
            ],
        }


class FakeSearchProvider:
    def search(self, queries: list[str]) -> tuple[list[dict], list[str]]:
        # ← 修复：返回元组（来源、图片）
        return (
            [
                {
                    "title": "Overview of the test topic",
                    "url": "https://example.com/overview",
                    "snippet": "A high-level overview of the test topic.",
                    "source": "mock",
                    "score": 0.95,
                },
                {
                    "title": "Rules and requirements",
                    "url": "https://example.com/rules",
                    "snippet": "Important rules and requirements for the test topic.",
                    "source": "mock",
                    "score": 0.91,
                },
            ],
            [],
        )


def fake_get_search_provider():
    return FakeSearchProvider()


def test_initialize_state_success_sets_run_id_and_started_status():
    state = make_initial_state("test question")

    result = initialize_state(state)

    assert result["run_id"]
    assert result["status"] == "started"
    assert result["errors"] == []


def test_initialize_state_returns_error_when_question_missing():
    state = make_initial_state("   ")

    result = initialize_state(state)

    assert result["status"] == "started"
    assert result["errors"] == ["init_run: No question provided"]


def test_scope_question_returns_error_when_question_missing():
    state = make_initial_state("")

    result = scope_question(state, FakeScopeLLMProvider())

    assert result["errors"] == ["scope_question: No user query provided"]


def test_scope_question_success_returns_scope_data():
    state = make_initial_state("test question")

    result = scope_question(state, FakeScopeLLMProvider())

    assert result["scope"] == "Explain the test topic clearly"
    assert result["assumptions"] == ["User is a beginner", "General context"]
    assert result["constraints"] == {"geography": "Global", "depth": "intro"}
    assert result["status"] == "scoped"


def test_generate_queries_returns_error_when_too_few_queries():
    state = make_initial_state("test question")
    state["scope"] = "Explain the test topic clearly"

    result = generate_queries(state, FakeTooFewQueriesLLMProvider())

    assert result["errors"] == [
        "generate_queries: LLM returned fewer than 3 valid queries"
    ]


def test_generate_queries_success_returns_queries():
    state = make_initial_state("test question")
    state["scope"] = "Explain the test topic clearly"

    result = generate_queries(state, FakeQueriesLLMProvider())

    assert result["queries"] == [
        "test topic overview",
        "test topic rules",
        "test topic examples",
    ]
    assert result["status"] == "planned"


def test_search_web_returns_error_when_queries_missing():
    state = make_initial_state("test question")
    state["queries"] = None

    class FakeSearchProvider:
        def search(self, queries) -> tuple:
            return ([], [])  # ← 修复：返回元组

    result = search_web(state, FakeSearchProvider())

    assert result["errors"] == ["search_web: queries must be a list"]


def test_search_web_success_returns_sources(monkeypatch):
    class FakeSearchProvider:
        def search(self, queries) -> tuple:
            # ← 修复：返回元组（来源、图片）
            return (
                [
                    {
                        "title": "Test Source",
                        "url": "https://example.com",
                        "snippet": "Test snippet.",
                        "source": "mock",
                        "score": 0.9,
                    }
                ],
                [],
            )

    state = make_initial_state("test question")
    state["queries"] = ["test query one", "test query two", "test query three"]

    result = search_web(state, FakeSearchProvider())
    assert "sources" in result
    assert len(result["sources"]) == 1


def test_synthesize_answer_returns_error_for_unknown_citation():
    state = make_initial_state("test question")
    state["sources"] = [
        {
            "title": "Overview of the test topic",
            "url": "https://example.com/overview",
            "snippet": "A high-level overview of the test topic.",
            "source": "mock",
            "score": 0.95,
        },
        {
            "title": "Rules and requirements",
            "url": "https://example.com/rules",
            "snippet": "Important rules and requirements for the test topic.",
            "source": "mock",
            "score": 0.91,
        },
    ]

    result = synthesize_answer(state, FakeBadCitationLLMProvider())

    assert result["errors"] == [
        "synthesize_answer: LLM returned unknown citation URL: https://example.com/not-allowed"
    ]


def test_synthesize_answer_success_returns_answer_and_citations():
    state = make_initial_state("test question")
    state["sources"] = [
        {
            "title": "Overview of the test topic",
            "url": "https://example.com/overview",
            "snippet": "A high-level overview of the test topic.",
            "source": "mock",
            "score": 0.95,
        },
        {
            "title": "Rules and requirements",
            "url": "https://example.com/rules",
            "snippet": "Important rules and requirements for the test topic.",
            "source": "mock",
            "score": 0.91,
        },
    ]

    result = synthesize_answer(state, FakeSynthesisLLMProvider())

    assert result["answer"]
    assert result["citations"] == [
        "https://example.com/overview",
        "https://example.com/rules",
    ]
    assert result["status"] == "synthesized"


def test_finalize_run_marks_completed_when_answer_exists_and_no_errors():
    state = make_initial_state("test question")
    state["answer"] = "A valid answer"
    state["errors"] = []

    result = finalize_run(state)

    assert result["status"] == "completed"


def test_finalize_run_marks_error_when_errors_exist():
    state = make_initial_state("test question")
    state["answer"] = "A valid answer"
    state["errors"] = ["something failed"]

    result = finalize_run(state)

    assert result["status"] == "error"


def test_handle_error_sets_error_status():
    state = make_initial_state("test question")
    state["errors"] = ["scope_question: failed"]

    result = handle_error(state)

    assert result["status"] == "error"


def test_synthesize_answer_uses_conversation_history_in_prompt(monkeypatch):
    """验证synthesize_answer将conversation_history传递给
    当它存在于状态中时提示构建器。 FakeLLM 捕获
    提示，我们断言之前的回合内容出现在其中。"""
    captured_prompts = []

    class FakeCapturingLLMProvider:
        def generate_json(self, prompt: str) -> dict:
            captured_prompts.append(prompt)
            return {
                "answer": "Quantum computing has several limitations.",
                "citations": ["https://example.com/overview"],
            }

    state = make_initial_state("What are its limitations?")
    state["sources"] = [
        {
            "title": "Overview of the test topic",
            "url": "https://example.com/overview",
            "snippet": "A high-level overview of the test topic.",
            "source": "mock",
            "score": 0.95,
        },
    ]
    state["conversation_history"] = [
        {
            "turn": 1,
            "question": "What is quantum computing?",
            "answer": "Quantum computing uses quantum mechanical phenomena.",
            "scope": "Explain quantum computing clearly",
        }
    ]

    result = synthesize_answer(state, FakeCapturingLLMProvider())

    assert result.get("answer") is not None
    assert len(captured_prompts) == 1
    assert "CONVERSATION HISTORY" in captured_prompts[0]
    assert "What is quantum computing?" in captured_prompts[0]


def test_synthesize_answer_with_no_conversation_history_excludes_context(
    monkeypatch,
):
    """验证 Synthesize_answer 不包含对话上下文
    当conversation_history为None时的提示中。向后确认
    与单轮研究流程的兼容性。"""
    captured_prompts = []

    class FakeCapturingLLMProvider:
        def generate_json(self, prompt: str) -> dict:
            captured_prompts.append(prompt)
            return {
                "answer": "Quantum computing uses quantum mechanics.",
                "citations": ["https://example.com/overview"],
            }

    state = make_initial_state("What is quantum computing?")
    state["sources"] = [
        {
            "title": "Overview of the test topic",
            "url": "https://example.com/overview",
            "snippet": "A high-level overview of the test topic.",
            "source": "mock",
            "score": 0.95,
        },
    ]
    state["conversation_history"] = None

    result = synthesize_answer(state, FakeCapturingLLMProvider())

    assert result.get("answer") is not None
    assert len(captured_prompts) == 1
    assert "CONVERSATION HISTORY" not in captured_prompts[0]


def test_synthesize_answer_report_mode_includes_report_sections_in_prompt():
    """验证在以下情况下，synthesize_answer 是否使用报告提示：
    模式是“报告”。捕获的提示应包含
    结构化节标题。"""
    captured_prompts = []

    class FakeCapturingLLMProvider:
        def generate_json(self, prompt: str) -> dict:
            captured_prompts.append(prompt)
            return {
                "answer": "## Introduction\nTest intro.\n## Key Findings\nTest findings.",
                "citations": ["https://example.com/overview"],
            }

    state = make_initial_state("What is quantum computing?")
    state["mode"] = "report"
    state["sources"] = [
        {
            "title": "Overview of the test topic",
            "url": "https://example.com/overview",
            "snippet": "A high-level overview of the test topic.",
            "source": "mock",
            "score": 0.95,
        },
    ]

    result = synthesize_answer(state, FakeCapturingLLMProvider())

    assert result.get("answer") is not None
    assert len(captured_prompts) == 1
    assert "## Introduction" in captured_prompts[0]
    assert "## Key Findings" in captured_prompts[0]
    assert "## Analysis" in captured_prompts[0]
    assert "## Conclusion" in captured_prompts[0]


def test_synthesize_answer_research_mode_excludes_report_sections_from_prompt():
    """验证synthesize_answer不包含报告部分
    当模式为“研究”时提示中的标题。确认
    两种模式会产生不同的提示。"""
    captured_prompts = []

    class FakeCapturingLLMProvider:
        def generate_json(self, prompt: str) -> dict:
            captured_prompts.append(prompt)
            return {
                "answer": "Quantum computing uses quantum mechanics.",
                "citations": ["https://example.com/overview"],
            }

    state = make_initial_state("What is quantum computing?")
    state["mode"] = "research"
    state["sources"] = [
        {
            "title": "Overview of the test topic",
            "url": "https://example.com/overview",
            "snippet": "A high-level overview of the test topic.",
            "source": "mock",
            "score": 0.95,
        },
    ]

    result = synthesize_answer(state, FakeCapturingLLMProvider())

    assert result.get("answer") is not None
    assert len(captured_prompts) == 1
    assert "## Introduction" not in captured_prompts[0]
    assert "## Key Findings" not in captured_prompts[0]
