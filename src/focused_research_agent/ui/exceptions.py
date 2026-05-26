"""重点研究代理的 UI 传输层例外。

该模块定义特定于 Streamlit UI 传输层的异常。
它们代表 UI 级别的故障，例如 FastAPI 后端无法访问，
这与应用程序层或图形级错误不同。

从架构上来说，该模块属于UI传输层。如下：
与 application/exceptions.py 相同的模式 - 一个命名的异常类
每层，因此每一层都有自己清晰的错误语言。"""


class BackendUnavailableError(Exception):
    """当无法访问 FastAPI 后端时引发。

    当 httpx 抛出 ConnectError 时，api_client.py 会引发此异常，
    意味着 FastAPI 服务器未运行或无法访问
    配置的 UI_API_BASE_URL。

    它被 1_🔍_Research.py 捕获，呈现一条清晰的、面向用户的消息，告诉
    用户在使用 UI 之前启动后端。

    参数：
        message：关于后端不可用原因的人类可读的描述。"""

    def __init__(self, message: str) -> None:
        super().__init__(message)
