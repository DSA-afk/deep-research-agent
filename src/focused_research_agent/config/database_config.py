"""重点研究代理的数据库配置。

该模块定义 SQLAlchemy 使用的数据库连接设置
发动机。它将特定于数据库的配置保留在一处，如下
与 api_config.py 和 llm_config.py 相同的模式。

从架构上来说，该模块属于配置层。它
向数据库层提供数据库 URL，同时保持独立
来自模型、查询和应用程序逻辑。

DATABASE_URL 遵循 SQLAlchemy 的连接字符串格式：
- SQLite（本地）：sqlite:///./research_agent.db
- PostgreSQL（产品）：postgresql://user:password@host/dbname

切换数据库只需要更改DATABASE_URL环境
变量。无需更改应用程序代码。"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class DatabaseSettings:
    """SQLAlchemy 引擎使用的结构化数据库设置。

    属性：
        database_url：数据库的 SQLAlchemy 连接字符串。
            如果环境中未设置，则默认为本地 SQLite 文件。"""

    database_url: str


def get_database_settings() -> DatabaseSettings:
    """使用合理的方式从环境变量加载数据库设置
    默认。

    默认为名为 Research_agent.db 的本地 SQLite 文件
    如果环境中未设置 DATABASE_URL，则为项目根目录。

    返回：
        DatabaseSettings：完全构建的数据库设置对象。"""
    database_url = os.getenv(
        "DATABASE_URL",
        "sqlite:///./research_agent.db",
    )

    return DatabaseSettings(database_url=database_url)
