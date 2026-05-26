"""用于重点研究的 SQLAlchemy 引擎和会话管理
代理。

该模块根据配置创建数据库引擎，提供
用于创建数据库会话的会话工厂，并公开
get_db 依赖函数与 FastAPI 的依赖项一起使用
注射系统。

从架构上来说，该模块属于数据库层。它知道
仅关于 SQLAlchemy 和数据库配置。它不导入
来自应用层、图形层或API层。"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from focused_research_agent.config.database_config import get_database_settings
from focused_research_agent.database.models import Base


engine = create_engine(
    get_database_settings().database_url,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """创建所有数据库表（如果它们尚不存在）。

    多次安全调用 — SQLAlchemy 检查每个表是否
    在创建之前就已存在。在应用程序启动时通过调用一次
    FastAPI 生命周期或启动事件。

    返回：
        无"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """产生一个数据库会话并保证它在使用后关闭。

    通过 Depends(get_db) 用作 FastAPI 依赖项。产量一
    请求期间的会话并在最后关闭它
    块，因此即使发生错误，它也始终会被释放。

    产量：
        会话：活动的 SQLAlchemy 数据库会话。"""
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
