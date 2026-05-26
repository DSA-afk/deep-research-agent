"""重点研究代理的 API 应用程序设置。

该模块定义 FastAPI 层使用的应用程序级配置。
它将特定于 API 的设置（例如标题、版本和调试模式）保留在
一个结构化的地方，而不是将它们分散在应用程序工厂中。

从架构上来说，该模块属于配置层。它提供
应用程序设置到 FastAPI 应用程序工厂，同时保持独立
来自路由器、用例逻辑和工作流编排。"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _parse_bool(value: str | None, default: bool) -> bool:
    """将字符串环境值解析为布尔值。

    参数：
        value：原始环境变量值。
        default：输入丢失时使用的默认布尔值。

    返回：
        bool：解析的布尔值。"""
    if value is None:
        return default

    normalized_value = value.strip().lower()
    return normalized_value in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class APISettings:
    """FastAPI 应用工厂使用的结构化 API 设置。

    属性：
        title：FastAPI 文档中显示的人类可读的 API 标题。
        version：FastAPI 文档中显示的 API 版本标签。
        debug：控制 FastAPI 调试行为的标志。"""

    title: str
    version: str
    debug: bool


def get_api_settings() -> APISettings:
    """从具有合理默认值的环境变量加载 API 设置。

    返回：
        APISettings：完全构建的 API 设置对象。"""
    title = os.getenv("API_TITLE", "Focused Research Agent API")
    version = os.getenv("API_VERSION", "1.0.0")
    debug = _parse_bool(os.getenv("API_DEBUG"), False)

    return APISettings(
        title=title,
        version=version,
        debug=debug,
    )
