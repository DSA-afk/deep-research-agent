"""重点研究代理的 UI 应用程序设置。

该模块定义 Streamlit UI 层使用的配置。
它保留特定于 UI 的设置，例如后端基本 URL 和请求
在一个结构化的地方超时，遵循与 api_config.py 相同的模式。

从架构上来说，该模块属于配置层。它提供
UI 传输层的设置，同时与渲染保持分离，
HTTP 和工作流程问题。"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class UISettings:
    """Streamlit 传输层使用的结构化 UI 设置。

    属性：
        api_base_url：UI 调用的 FastAPI 后端的基本 URL。
        request_timeout：等待研究响应的秒数
            超时。研究涉及法学硕士通话和网络搜索，因此
            这应该是慷慨的。"""

    api_base_url: str
    request_timeout: int


def get_ui_settings() -> UISettings:
    """从具有合理默认值的环境变量加载 UI 设置。

    返回：
        UISettings：完全构造的 UI 设置对象。"""
    api_base_url = os.getenv("UI_API_BASE_URL", "http://localhost:8000")
    request_timeout = int(os.getenv("UI_REQUEST_TIMEOUT", "120"))

    return UISettings(
        api_base_url=api_base_url,
        request_timeout=request_timeout,
    )
