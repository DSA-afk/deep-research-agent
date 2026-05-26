"""Focused Research Agent 测试套件的 Pytest 配置。

在任何操作之前将 DATABASE_URL 设置为共享内存 SQLite 数据库
测试模块已导入。使用共享缓存 URI 可确保所有
测试会话中的连接看到相同的数据库和
相同的表，避免出现“没有这样的表”错误
每个连接都有自己独立的内存数据库。"""

import os

os.environ.setdefault(
    "DATABASE_URL",
    "sqlite:///file::memory:?cache=shared&uri=true",
)


def pytest_configure(config):
    """设置环境变量后创建所有数据库表
    在任何测试运行之前。

    参数：
        config：pytest 配置对象。"""
    from focused_research_agent.database.database import init_db

    init_db()
