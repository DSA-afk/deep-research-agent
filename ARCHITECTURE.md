# Focused Research Agent — 六层架构全景图

---

## 架构总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Layer 1: UI 层 (Streamlit)                        │
│                                                                             │
│  Home.py · 1_🔍_Research.py · 2_💬_Chat.py · 3_📄_Report.py                │
│  views.py · api_client.py · exceptions.py                                   │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │ httpx.post() / httpx.get()
                                 │ HTTP JSON 请求
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Layer 2: API 层 (FastAPI)                         │
│                                                                             │
│  app.py · dependencies.py · api_exception_handlers.py                       │
│  routers/health.py · routers/research.py · routers/chat.py                  │
│  routers/report.py · routers/conversations.py · routers/v1.py               │
│  schemas/research.py · schemas/chat.py · schemas/report.py                  │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │ Depends() 注入用例函数
                                 │ 直接函数调用
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Layer 3: 应用层 (Use Cases)                       │
│                                                                             │
│  research_use_case.py · chat_use_case.py · report_use_case.py               │
│  question_validation.py · exceptions.py                                     │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │ build_graph() 构建图
                                 │ graph.invoke(initial_state) 执行图
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Layer 4: Graph 层 (LangGraph)                     │
│                                                                             │
│  graph.py · state.py                                                        │
│  nodes/init_run.py · nodes/scope_question.py · nodes/generate_queries.py    │
│  nodes/search_web.py · nodes/synthesize_answer.py                           │
│  nodes/finalize_run.py · nodes/handle_error.py                              │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
┌──────────────────────────────┐  ┌──────────────────────────────┐
│  Layer 5a: LLM 服务层        │  │  Layer 5b: 搜索服务层        │
│                              │  │                              │
│  interfaces/llm_interface.py │  │  interfaces/search_          │
│  services/llm_factory.py     │  │      interface.py            │
│  services/llm_provider_      │  │  services/search_factory.py  │
│      groq.py                 │  │  services/search_provider_   │
│  services/llm_provider_      │  │      tavily.py               │
│      ollama.py               │  │                              │
└──────────────┬───────────────┘  └──────────────┬───────────────┘
               │                                  │
               │ langchain-groq / ollama          │ tavily-python
               │ SDK 调用                         │ SDK 调用
               ▼                                  ▼
        ┌────────────┐                    ┌─────────────┐
        │  Groq API  │                    │ Tavily API  │
        │  Ollama    │                    │             │
        └────────────┘                    └─────────────┘

                    ┌────────────┐
                    ▼            │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Layer 6: 数据库层 (SQLAlchemy)                    │
│                                                                             │
│  database/database.py · database/models.py · database/repository.py         │
│  config/database_config.py                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                          ┌─────────────┐
                          │   SQLite    │
                          │ research.db │
                          └─────────────┘
```

---

## 各层文件清单与职责

### Layer 1: UI 层

| 文件 | 职责 |
|------|------|
| `ui/Home.py` | 首页，Streamlit 入口 |
| `ui/pages/1_🔍_Research.py` | 快速研究页面，管理会话状态，调用 api_client，委托 views 渲染 |
| `ui/pages/2_💬_Chat.py` | 多轮对话页面，管理 conversation_id 和消息列表 |
| `ui/pages/3_📄_Report.py` | 报告生成页面，管理报告状态 |
| `ui/views.py` | 纯渲染函数，接收 dict 数据，输出 Streamlit 组件（不含 HTTP 逻辑） |
| `ui/api_client.py` | 纯 HTTP 客户端，使用 httpx 调用 FastAPI（不含 Streamlit 代码） |
| `ui/exceptions.py` | `BackendUnavailableError` 异常定义 |

### Layer 2: API 层

| 文件 | 职责 |
|------|------|
| `api/app.py` | FastAPI 应用工厂 `create_app()`，注册路由和异常处理器 |
| `api/dependencies.py` | 依赖注入，将应用层用例注入到路由 |
| `api/api_exception_handlers.py` | 集中式 400/500 异常处理 |
| `api/routers/v1.py` | `/api/v1` 前缀路由组，聚合所有子路由 |
| `api/routers/health.py` | `GET /health` 健康检查端点 |
| `api/routers/research.py` | `POST /api/v1/research` 研究端点 |
| `api/routers/chat.py` | `POST /api/v1/chat` 聊天端点 |
| `api/routers/report.py` | `POST /api/v1/report` 报告端点 |
| `api/routers/conversations.py` | `GET /api/v1/conversations` 历史查询端点 |
| `api/schemas/research/research.py` | Research 请求/响应的 Pydantic 模型 |
| `api/schemas/chat/chat.py` | Chat 请求/响应的 Pydantic 模型 |
| `api/schemas/report/report.py` | Report 请求/响应的 Pydantic 模型 |

### Layer 3: 应用层

| 文件 | 职责 |
|------|------|
| `application/research_use_case.py` | 单轮研究用例：验证 → 建图 → 执行 → 规范化 |
| `application/chat_use_case.py` | 多轮对话用例：注入历史 → 建图 → 执行 → 持久化 |
| `application/report_use_case.py` | 报告生成用例：高级搜索 → 结构化报告 → 持久化 |
| `application/question_validation.py` | 共享问题验证逻辑（API 层和应用层共用） |
| `application/exceptions.py` | `ApplicationError` 异常定义 |

### Layer 4: Graph 层

| 文件 | 职责 |
|------|------|
| `graph.py` | `build_graph()` 构建 StateGraph，注册节点和条件边 |
| `state.py` | `ResearchState` TypedDict 定义（15 个字段的共享状态） |
| `nodes/init_run.py` | 生成 run_id，验证问题 |
| `nodes/scope_question.py` | LLM 解读问题，生成范围/假设/约束 |
| `nodes/generate_queries.py` | LLM 生成 3-6 条搜索查询 |
| `nodes/search_web.py` | Tavily 执行搜索，去重，收集图片 |
| `nodes/synthesize_answer.py` | 域名排序 + LLM 合成答案 + 引用验证 |
| `nodes/finalize_run.py` | 标记状态为 completed/error |
| `nodes/handle_error.py` | 终止错误节点 |

### Layer 5: 服务层

| 文件 | 职责 |
|------|------|
| `interfaces/llm_interface.py` | `LLMProvider` ABC，定义 `generate_json()` 契约 |
| `interfaces/search_interface.py` | `SearchProvider` ABC + `SearchResult` TypedDict |
| `services/llm_factory.py` | 工厂函数，根据环境变量返回 Groq 或 Ollama |
| `services/llm_provider_groq.py` | Groq 实现，通过 langchain-groq 调用 |
| `services/llm_provider_ollama.py` | Ollama 实现，支持本地和云端 |
| `services/search_factory.py` | 工厂函数，返回 Tavily 实现 |
| `services/search_provider_tavily.py` | Tavily 实现，搜索 + 去重 + 图片提取 |

### Layer 6: 数据库层

| 文件 | 职责 |
|------|------|
| `database/database.py` | SQLAlchemy Engine 和 Session 工厂，`init_db()` |
| `database/models.py` | `ConversationRun` SQLAlchemy ORM 模型 |
| `database/repository.py` | Repository Pattern，唯一直接操作 SQLAlchemy 的文件 |
| `config/database_config.py` | `DATABASE_URL` 环境变量读取 |

### 配置层（横切关注点，不属于六层之一）

| 文件 | 职责 |
|------|------|
| `config/api_config.py` | FastAPI 配置（title, version, debug） |
| `config/llm_config.py` | LLM 配置（provider, model, api_key, temperature） |
| `config/search_config.py` | 搜索配置（provider, api_key, max_results, depth） |
| `config/database_config.py` | 数据库 URL 配置 |
| `config/ui_config.py` | UI 配置（api_base_url, request_timeout） |
| `config/logger_config.py` | 日志配置（循环文件日志） |

---

## 层间连接详解

### UI 层 → API 层

```
ui/api_client.py                          api/routers/research.py
─────────────────                         ────────────────────────
call_research(question)                   research(search, run_research_use_case)
  │                                         │
  ├─ httpx.post(                            ├─ @research_router.post("/research")
  │    url = settings.api_base_url          │
  │        + "/api/v1/research",            ├─ run_research_use_case(search.question)
  │    json={"question": question},         │    ↑
  │    timeout=settings.request_timeout     │    │ Depends(get_research_use_case)
  │  )                                      │    │
  │                                         │
  ├─ _parse_post_response(response)         │
  │    ├─ 200 → {"success": True, ...}      │
  │    ├─ 400 → {"success": False, ...}     │
  │    ├─ 422 → {"success": False, ...}     │
  │    └─ 其他 → {"success": False, ...}    │
  │                                         │
  └─ 返回 ResearchCallResult                └─ 返回 dict → FastAPI 自动序列化为 JSON
```

**连接方式：** HTTP JSON 请求/响应
**关键函数：** `api_client.py` 中的 `httpx.post()` / `httpx.get()`
**配置来源：** `config/ui_config.py` → `UI_API_BASE_URL`（默认 `http://localhost:8000`）

---

### API 层 → 应用层

```
api/dependencies.py                       application/research_use_case.py
───────────────────                       ──────────────────────────────────
get_research_use_case()                   research_question(question: str)
  │                                         │
  └─ return research_use_case.              ├─ validate_and_clean_question(question)
       research_question                    ├─ build_graph()
                                            ├─ make_initial_state(user_query)
api/routers/research.py                    ├─ graph.invoke(initial_state)
────────────────────────                   └─ normalize_state(final_state)
research(search, run_research_use_case)
  │
  └─ search_result = run_research_use_case(search.question)
```

**连接方式：** FastAPI 依赖注入 `Depends()`
**关键函数：** `dependencies.py` 中的 `get_research_use_case()` 返回用例函数引用
**调用链：** 路由 → `Depends(get_research_use_case)` → `research_question`

---

### 应用层 → Graph 层

```
application/research_use_case.py          graph.py
─────────────────────────────────         ────────
research_question(question)               build_graph(search_depth=None)
  │                                         │
  ├─ graph = build_graph()  ───────────────►├─ llm = get_llm_provider()
  │                                         ├─ search = get_search_provider()
  ├─ initial_state = make_initial_state()   ├─ builder = StateGraph(ResearchState)
  │                                         ├─ builder.add_node("init_run", ...)
  └─ final_state = graph.invoke(            ├─ builder.add_node("scope_question", ...)
       initial_state                        ├─ ...（7 个节点）
     )  ──────────────────────────────────►├─ builder.add_conditional_edges(...)
                                           └─ return builder.compile()
```

**连接方式：** 直接函数调用
**关键函数：** `research_use_case.py` 调用 `build_graph()` 获取编译后的图，再调用 `graph.invoke(initial_state)` 执行

---

### Graph 层 → 服务层

```
graph.py                                  services/llm_factory.py
───────                                   ────────────────────────
build_graph()                             get_llm_provider()
  │                                         │
  ├─ llm = get_llm_provider()  ────────────►├─ provider = os.getenv("LLM_PROVIDER")
  │                                         ├─ if "groq" → return GroqLLMProvider(...)
  │                                         └─ if "ollama" → return OllamaLLMProvider(...)
  │
  ├─ search = get_search_provider()  ─────► services/search_factory.py
  │                                         get_search_provider(search_depth)
  │                                           └─ return TavilySearchClient(...)

nodes/scope_question.py                   interfaces/llm_interface.py
───────────────────────                   ────────────────────────────
scope_question(state, llm_provider)       class LLMProvider(ABC):
  │                                         @abstractmethod
  └─ response = llm_provider.               def generate_json(prompt) -> dict
       generate_json(prompt)  ────────────►

nodes/search_web.py                       interfaces/search_interface.py
───────────────────                       ──────────────────────────────
search_web(state, search_provider)        class SearchProvider(ABC):
  │                                         @abstractmethod
  └─ results, images = search_provider.     def search(queries) -> tuple[list, list]
       search(queries)  ──────────────────►
```

**连接方式：** 通过抽象接口（ABC）调用具体实现
**关键设计：** 节点只依赖 `LLMProvider` / `SearchProvider` 接口，不直接依赖 Groq/Tavily

---

### 应用层 → 数据库层

```
application/chat_use_case.py              database/repository.py
───────────────────────────               ────────────────────────
execute_chat_turn(db, question, ...)      save_run(db, run_data)
  │                                         │
  ├─ save_run(db, {...})  ─────────────────►├─ db.add(ConversationRun(...))
  │                                         └─ db.commit()
  ├─ get_conversation_history(              │
  │    db, conversation_id                  get_conversation_history(db, conv_id)
  │  )  ──────────────────────────────────►├─ db.query(ConversationRun)
  │                                         │   .filter_by(...)
  │                                         └─ .all()
  └─ get_all_conversations(db)  ──────────► get_all_conversations(db)

database/models.py
──────────────────
class ConversationRun(Base):
    __tablename__ = "conversation_runs"
    id · conversation_id · turn_number · question · answer
    · scope · queries · sources · citations · images · status
    · mode · created_at

database/database.py
────────────────────
init_db()
  └─ Base.metadata.create_all(engine)  ← 在 app.py 的 create_app() 中调用
```

**连接方式：** 通过 Repository Pattern 传入 db session
**关键函数：** `repository.py` 中的 `save_run()` / `get_conversation_history()` / `get_all_conversations()`
**session 创建：** `database.py` 中的 `get_db()` 生成器，在 API 层通过 FastAPI 的 `Depends()` 注入

---

## 完整请求链路（以 Research 为例）

```
用户点击 "🔍 开始 Research"
    │
    ▼
[Layer 1] 1_🔍_Research.py: _handle_research()
    │  st.button("🔍 开始 Research")
    │  call_research(question)
    ▼
[Layer 1] api_client.py: call_research()
    │  httpx.post("http://localhost:8000/api/v1/research", json={...})
    │  ──── HTTP 请求 ────
    ▼
[Layer 2] api/app.py: create_app() 已注册的路由
    │  匹配到 routers/v1.py → routers/research.py
    ▼
[Layer 2] api/routers/research.py: research()
    │  search_result = run_research_use_case(search.question)
    │  ↑ 通过 Depends(get_research_use_case) 注入
    ▼
[Layer 2] api/dependencies.py: get_research_use_case()
    │  return research_use_case.research_question
    ▼
[Layer 3] application/research_use_case.py: research_question()
    │  ① validate_and_clean_question(question)
    │  ② graph = build_graph()
    │  ③ initial_state = make_initial_state(user_query)
    │  ④ final_state = graph.invoke(initial_state)
    │  ⑤ result = normalize_state(final_state)
    ▼
[Layer 4] graph.py: build_graph() → graph.invoke()
    │
    │  ┌─ init_run ────────────────────── nodes/init_run.py
    │  │    生成 run_id，验证问题
    │  │
    │  ├─ scope_question ──────────────── nodes/scope_question.py
    │  │    │
    │  │    └─ llm_provider.generate_json(prompt)
    │  │         │
    │  │         ▼
    │  │    [Layer 5a] services/llm_provider_groq.py
    │  │         langchain init_chat_model → Groq API
    │  │
    │  ├─ generate_queries ────────────── nodes/generate_queries.py
    │  │    │
    │  │    └─ llm_provider.generate_json(prompt)
    │  │         ▼
    │  │    [Layer 5a] Groq API
    │  │
    │  ├─ search_web ──────────────────── nodes/search_web.py
    │  │    │
    │  │    └─ search_provider.search(queries)
    │  │         │
    │  │         ▼
    │  │    [Layer 5b] services/search_provider_tavily.py
    │  │         tavily_client.search() → Tavily API
    │  │
    │  ├─ synthesize_answer ───────────── nodes/synthesize_answer.py
    │  │    │
    │  │    ├─ _collect_valid_sources()   域名排序
    │  │    └─ llm_provider.generate_json(prompt)
    │  │         ▼
    │  │    [Layer 5a] Groq API
    │  │
    │  └─ finalize_run ────────────────── nodes/finalize_run.py
    │       标记 status = "completed"
    ▼
[Layer 3] 返回 result dict
    ▼
[Layer 2] FastAPI 自动序列化为 JSON 响应
    │  ──── HTTP 响应 ────
    ▼
[Layer 1] api_client.py: _parse_post_response()
    │  返回 ResearchCallResult
    ▼
[Layer 1] 1_🔍_Research.py: _render_results()
    │  render_answer(data)
    │  render_metrics(data)
    │  render_research_details(data)
    │  render_sources(sources, images)
    ▼
用户看到研究结果
```

---

## Chat 模式的额外链路（数据库交互）

```
[Layer 3] application/chat_use_case.py: execute_chat_turn()
    │
    ├─ ① db = next(get_db())                    ← 创建数据库 session
    ├─ ② get_conversation_history(db, conv_id)   ← [Layer 6] 读取历史
    ├─ ③ history → 注入到 state["conversation_history"]
    ├─ ④ graph.invoke(initial_state)             ← [Layer 4] 执行图
    ├─ ⑤ save_run(db, {...})                     ← [Layer 6] 保存本轮结果
    └─ ⑥ return result
```

---

## 依赖注入关系图

```
api/dependencies.py
───────────────────
get_research_use_case()  ──► research_use_case.research_question
get_chat_use_case()      ──► chat_use_case.execute_chat_turn
get_report_use_case()    ──► report_use_case.execute_report

api/routers/*.py 通过 Depends() 获取上述函数
api/routers/chat.py 还通过 Depends(get_db) 获取数据库 session
```

---

## 工厂模式关系图

```
config/llm_config.py: get_llm_config()
    │
    │  读取 LLM_PROVIDER / LLM_MODEL / LLM_API_KEY
    ▼
services/llm_factory.py: get_llm_provider()
    │
    ├─ "groq"   → GroqLLMProvider(config)   ──► services/llm_provider_groq.py
    └─ "ollama" → OllamaLLMProvider(config) ──► services/llm_provider_ollama.py

config/search_config.py: get_search_config()
    │
    │  读取 SEARCH_PROVIDER / SEARCH_API_KEY / SEARCH_MAX_RESULTS / SEARCH_DEPTH
    ▼
services/search_factory.py: get_search_provider(search_depth)
    │
    └─ "tavily" → TavilySearchClient(config, search_depth) ──► services/search_provider_tavily.py
```

---

## Pydantic 验证链路

```
用户输入 "question"
    │
    ▼
api/schemas/research/research.py: ResearchRequest
    │  question: str = Field(...)
    │  AfterValidator(validate_and_clean_question)  ← 共享验证
    ▼
application/question_validation.py: validate_and_clean_question()
    │  strip → 长度检查 → 空值检查 → 返回清理后的问题
    ▼
application/research_use_case.py: research_question()
    │  再次调用 validate_and_clean_question()  ← 双重保险
    ▼
进入 LangGraph 工作流
```
