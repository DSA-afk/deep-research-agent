"""重点研究代理的数据库存储库。

该模块是项目中唯一读取和写入的文件
到数据库。所有其他需要数据访问的模块都调用这些
函数——它们从不直接与 SQLAlchemy 会话交互。

从架构上来说，该模块属于数据库层，
实现存储库模式。它消除了存储问题
从应用层。切换数据库只需更改
此文件和database.py - 没有应用程序或图形代码更改。

列表字段（查询、来源、引用、错误）被序列化为
保存时使用 JSON 字符串，读取时反序列化回 Python 列表。
这种转换对于应用程序的其余部分是透明的。"""

import logging
import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from focused_research_agent.database.models import ConversationRun

logger = logging.getLogger(__name__)


def _serialize(value: list | None) -> str | None:
    """将 Python 列表序列化为 JSON 字符串以供数据库存储。

    参数：
        value：要序列化的列表，或无。

    返回：
        STR | None：如果值为列表，则为 JSON 字符串；如果值为，则为 None
            没有。"""
    if value is None:
        return None
    return json.dumps(value)


def _deserialize(value: str | None) -> list | None:
    """将 JSON 字符串从数据库反序列化回 Python 列表。

    参数：
        value：要反序列化的 JSON 字符串，或 None。

    返回：
        列表 | None：如果值是字符串则Python列表，如果值则无
            是无。"""
    if value is None:
        return None
    return json.loads(value)


def save_run(
    db: Session,
    state: dict,
    conversation_id: str,
    turn_number: int,
    mode: str = "research",
) -> ConversationRun:
    """将完成的研究运行保存到数据库中。

    从规范化研究创建一个新的 ConversationRun 行
    状态。设置对话标题的前 60 个字符
    仅第一回合的问题。将列表字段序列化为 JSON
    存储之前的字符串。

    参数：
        db：活动 SQLAlchemy 数据库会话。
        state：应用程序的标准化研究结果字典
            层。
        conversation_id：将此运行链接到其的 UUID 字符串
            谈话。
        turn_number：本次运行在对话中的位置
            （基于 1）。

    返回：
        ConversationRun：保存的模型实例及其数据库
            ID 已填充。"""
    now = datetime.now(timezone.utc)

    conversation_title = None
    if turn_number == 1:
        conversation_title = state["question"][:60]

    run = ConversationRun(
        conversation_id=conversation_id,
        turn_number=turn_number,
        conversation_title=conversation_title,
        run_id=state["run_id"],
        question=state["question"],
        status=state["status"],
        scope=state.get("scope"),
        queries=_serialize(state.get("queries")),
        sources=_serialize(state.get("sources")),
        answer=state.get("answer"),
        citations=_serialize(state.get("citations")),
        errors=_serialize(state.get("errors")),
        images=_serialize(state.get("images")),
        created_at=now,
        updated_at=now,
        mode=mode,
    )

    db.add(run)
    db.commit()
    db.refresh(run)
    logger.info(
        "Run saved. conversation_id=%s turn=%d mode=%s run_id=%s",
        conversation_id,
        turn_number,
        mode,
        state["run_id"],
    )
    return run


def get_conversation_history(
    db: Session,
    conversation_id: str,
    max_turns: int,
) -> list[dict]:
    """获取最近的对话内容以获取上下文
    线程。

    按时间顺序返回回合（最旧的在前），以便他们可以
    直接包含在 LLM 提示中作为对话历史记录。

    参数：
        db：活动 SQLAlchemy 数据库会话。
        Conversation_id：标识会话的 UUID 字符串。
        max_turns：最近返回的最大转弯数。年长的
            超过此限制的转数将被排除在管理 LLM 之外
            上下文大小。

    返回：
        list[dict]：按时间顺序排列的turn dict列表，每个
            包含回合、问题、答案和范围键。
            如果对话尚未轮到，则列表为空。"""
    runs = (
        db.query(ConversationRun)
        .filter(ConversationRun.conversation_id == conversation_id)
        .order_by(ConversationRun.turn_number.desc())
        .limit(max_turns)
        .all()
    )

    runs = list(reversed(runs))

    history = []
    for run in runs:
        history.append(
            {
                "turn": run.turn_number,
                "question": run.question,
                "answer": run.answer,
                "scope": run.scope,
            }
        )

    logger.debug(
        "Conversation history fetched. conversation_id=%s turns=%d",
        conversation_id,
        len(history),
    )
    return history


def get_all_conversations(db: Session) -> list[dict]:
    """获取历史记录侧边栏所有对话的摘要列表。

    仅使用第一轮返回每个对话的一个条目
    每个，先订购最新的。由 GET /api/v1/conversations 使用
    端点和聊天 UI 历史记录面板。

    参数：
        db：活动 SQLAlchemy 数据库会话。

    返回：
        list[dict]：对话摘要字典列表，每个
            包含conversation_id、title 和created_at 键。
            如果尚不存在任何对话，则列表为空。"""
    runs = (
        db.query(ConversationRun)
        .filter(
            ConversationRun.turn_number == 1,
            ConversationRun.mode != "report"
        )
        .order_by(ConversationRun.created_at.desc())
        .all()
    )

    conversations = []
    for run in runs:
        conversations.append(
            {
                "conversation_id": run.conversation_id,
                "title": run.conversation_title,
                "created_at": run.created_at.isoformat(),
            }
        )

    logger.debug("All conversations fetched. count=%d", len(conversations))
    return conversations


def get_conversation_turns(
    db: Session,
    conversation_id: str,
) -> list[dict]:
    """按时间顺序获取对话的所有回合。

    返回每轮的完整研究数据，包括
    反序列化的列表字段。由 GET 会话端点使用
    将完整的对话加载到聊天 UI 中。

    参数：
        db：活动 SQLAlchemy 数据库会话。
        Conversation_id：标识会话的 UUID 字符串。

    返回：
        list[dict]：按时间顺序排列的完整回合字典列表
            订单。如果对话不存在，则列表为空。"""
    runs = (
        db.query(ConversationRun)
        .filter(ConversationRun.conversation_id == conversation_id)
        .order_by(ConversationRun.turn_number.asc())
        .all()
    )

    turns = []
    for run in runs:
        turns.append(
            {
                "turn_number": run.turn_number,
                "run_id": run.run_id,
                "question": run.question,
                "status": run.status,
                "scope": run.scope,
                "queries": _deserialize(run.queries),
                "sources": _deserialize(run.sources),
                "answer": run.answer,
                "citations": _deserialize(run.citations),
                "errors": _deserialize(run.errors),
                "created_at": run.created_at.isoformat(),
                "images": _deserialize(run.images),
            }
        )
    logger.debug(
        "Conversation turns fetched. conversation_id=%s count=%d",
        conversation_id,
        len(turns),
    )
    return turns


def get_all_reports(db: Session) -> list[dict]:
    """获取报告历史记录的所有报告运行的摘要列表
    侧边栏。

    返回按最新顺序排列的每个报告的一个条目。过滤依据
    mode='report' 以排除聊天和研究运行。

    参数：
        db：活动 SQLAlchemy 数据库会话。

    返回：
        list[dict]：报告摘要字典列表，包含
            对话id、标题和created_at键。
            如果尚不存在报告，则列表为空。"""
    runs = (
        db.query(ConversationRun)
        .filter(ConversationRun.mode == "report")
        .order_by(ConversationRun.created_at.desc())
        .all()
    )

    reports = []
    for run in runs:
        reports.append(
            {
                "conversation_id": run.conversation_id,
                "title": run.conversation_title,
                "created_at": run.created_at.isoformat(),
            }
        )
    logger.debug("All reports fetched. count=%d", len(reports))
    return reports
