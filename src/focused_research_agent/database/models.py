"""Focused Research Agent 数据库的 SQLAlchemy 模型。

该模块使用 SQLAlchemy 定义数据库表结构
声明式 ORM。 ConversationRun 模型映射到
conversation_runs 表并存储每个研究的完整状态
在对话中转动。

列表字段（查询、来源、引用、错误）存储为 JSON
字符串。存储库层处理序列化和反序列化
透明地，因此应用程序的其余部分始终可以使用 Python
列表。

从架构上来说，该模块属于数据库层。它定义了
数据模式，对 HTTP、图形节点或
应用逻辑。"""

from sqlalchemy import DateTime, Integer, String, Text, Column
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有 SQLAlchemy 模型的基类。

    该项目中的所有模型都继承自该类。 SQLAlchemy 使用
    它跟踪所有表定义并在数据库中创建它们。"""

    pass


class ConversationRun(Base):
    """代表对话中的一个研究回合。

    每一行都是一次完整的研究运行——提出一个问题
    回答道。具有相同conversation_id的多行形成一个
    完整的对话线程。 turn_number 字段跟踪订单
    对话中的轮流。

    列表字段（查询、来源、引用、错误）存储为
    JSON 序列化字符串。存储库层处理转换
    Python 列表和 JSON 字符串之间。"""

    __tablename__ = "conversation_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 会话线程
    conversation_id = Column(String, nullable=False, index=True)
    turn_number = Column(Integer, nullable=False)
    conversation_title = Column(String, nullable=True)

    # 研究运行标识
    run_id = Column(String, nullable=False)

    # 核心研究字段
    question = Column(Text, nullable=False)
    status = Column(String, nullable=False)
    scope = Column(Text, nullable=True)

    # 列表字段 — 以 JSON 字符串存储，由repository反序列化
    queries = Column(Text, nullable=True)
    sources = Column(Text, nullable=True)
    citations = Column(Text, nullable=True)
    errors = Column(Text, nullable=True)

    # 答案
    answer = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    mode = Column(String, nullable=False, default="research")

    # 用于报告的图像
    images = Column(Text, nullable=True)

    def __repr__(self) -> str:
        """返回用于调试的可读字符串表示形式。

        返回：
            str：显示运行 ID、对话 ID 和回合的字符串
                数量。"""
        return (
            f"ConversationRun("
            f"id={self.id}, "
            f"conversation_id={self.conversation_id}, "
            f"turn={self.turn_number}"
            f")"
        )
