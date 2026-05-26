"""重点研究代理的命令行界面入口点。

该模块包含项目特定于终端的交互逻辑。
它负责从命令行参数读取用户输入或
交互式提示、处理退出命令以及格式化最终结果
CLI 显示的研究结果。

从架构上来说，CLI 是一个传输适配器。应该继续关注
终端输入/输出问题并将研究执行委托给
应用层。"""

import logging
import sys

from focused_research_agent.application import research_use_case
from focused_research_agent.application.exceptions import ApplicationError
from focused_research_agent.config.logger_config import setup_logging

logger = logging.getLogger("focused_research_agent.cli")

EXIT_COMMANDS = {"exit", "quit", "bye"}


def format_queries(queries: list[str] | None) -> str:
    """设置生成的搜索查询的格式以供 CLI 显示。

    参数：
        查询：根据研究结果生成搜索查询。

    返回：
        str：查询部分的人类可读的 CLI 文本。"""
    if not queries:
        return "(no queries)\n"

    lines = []
    for q in queries:
        lines.append("- " + q)

    return "\n".join(lines) + "\n"


def format_sources(sources: list[dict] | None) -> str:
    """设置收集的源条目的格式以供 CLI 显示。

    参数：
        来源：研究结果中返回的来源词典。

    返回：
        str：源代码部分的人类可读的 CLI 文本。"""
    if not sources:
        return "(no sources)\n"

    result = []
    for i, source in enumerate(sources, start=1):
        title = source.get("title") or "No Title"
        url = source.get("url") or "No URL"
        result.append(f"{i}. {title} — {url}")

    return "\n".join(result)


def format_citations(citations: list[str] | None) -> str:
    """设置 CLI 显示的引用 URL 的格式。

    参数：
        引用：研究结果中返回的引用 URL。

    返回：
        str：引文部分的人类可读的 CLI 文本。"""
    if not citations:
        return "(no citations)\n"

    lines = []
    for c in citations:
        lines.append("- " + c)

    return "\n".join(lines) + "\n"


def format_output(state: dict) -> str:
    """根据标准化研究结果构建最终的 CLI 输出块。

    参数：
        state：应用层返回的标准化研究结果。

    返回：
        str：格式化的 CLI 输出块。"""
    return f"""
==============================
QUESTION:
{state.get("question")}

RUN ID:
{state.get("run_id")}

STATUS:
{state.get("status")}

SCOPE:
{state.get("scope")}

QUERIES:
{format_queries(state.get("queries"))}
SOURCES (title + url):
{format_sources(state.get("sources"))}

ANSWER:
{state.get("answer")}

CITATIONS:
{format_citations(state.get("citations"))}
==============================
""".strip()


def format_error_output(message: str) -> str:
    """构建 CLI 错误输出块。

    参数：
        message：在终端中显示的错误消息。

    返回：
        str：格式化的 CLI 错误块。"""
    return f"""
==============================
STATUS:
Error

ERROR:
{message}
==============================
""".strip()


def get_user_question_from_command_line() -> str | None:
    """从命令行参数或交互式输入读取用户问题。

    该函数首先检查用户是否提供了一个问题
    命令行参数。如果没有，它会回退到提示用户
    交互地。它还支持 exit 关键字来结束应用程序
    干净地。

    返回：
        STR |无：已验证的用户问题，如果用户选择，则为“无”
        退出应用程序。"""
    user_question = " ".join(sys.argv[1:]).strip()

    if user_question:
        if user_question.lower() in EXIT_COMMANDS:
            return None
        return user_question

    while True:
        typed_question = input("What is your question? ").strip()

        if not typed_question:
            print("Please enter a question.")
            continue

        if typed_question.lower() in EXIT_COMMANDS:
            return None

        return typed_question


def main() -> None:
    """运行研究代理的 CLI 入口点。

    该函数初始化日志记录，从
    终端，执行共享研究用例，并打印
    格式化输出或格式化 CLI 错误块。

    返回：
        无"""
    setup_logging()
    user_question = get_user_question_from_command_line()

    if user_question is None:
        return

    try:
        final_state = research_use_case.research_question(user_question)

        errors = final_state.get("errors") or []
        if errors:
            error_message = "\n".join(errors)
            print(format_error_output(error_message))
            return

        print(format_output(final_state))

    except ApplicationError as e:
        print(format_error_output(str(e)))
        logger.exception("ApplicationError occurred: %s", e)

    except Exception as e:
        print(format_error_output(f"Unexpected internal error occurred: {e}"))
        logger.exception("Unexpected error in CLI")
