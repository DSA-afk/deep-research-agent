"""重点研究代理的法学硕士提供商工厂。

该模块包含负责实例化的工厂函数
基于 LLM_PROVIDER 的正确 LLM 提供程序实现
环境变量。

目前支持的提供商：
- groq：使用LangChain的init_chat_model的GroqLLMProvider
- ollama：使用 Ollama 客户端库的 OllamaLLMProvider

添加新的 LLM 提供商需要：
- 实现LLMProvider接口
- 在 get_llm_provider 中添加新分支

不需要更改其他文件——所有调用者都经过这个工厂。
olama 导入有意本地化，以避免导入 ollama
当它不是活动的提供者时打包。

从架构上来说，该模块属于服务层并实现
工厂模式。它将提供商选择逻辑保留在一处，并且
将应用程序的其余部分与具体的提供程序类解耦。"""

from focused_research_agent.config.llm_config import get_llm_config
from focused_research_agent.interfaces.llm_interface import LLMProvider
from focused_research_agent.services.llm_provider_groq import GroqLLMProvider


def get_llm_provider() -> LLMProvider:
    """返回有效的 LLM 提供商实施。

    返回：
        LLMProvider：配置的LLM提供程序实例。

    加薪：
        ValueError：如果配置的提供程序不受支持。"""
    llm_config = get_llm_config()
    provider = llm_config["provider"]

    if provider == "groq":
        return GroqLLMProvider()

    if provider == "ollama":
        from focused_research_agent.services.llm_provider_ollama import (
            OllamaLLMProvider,
        )
        return OllamaLLMProvider()

    if provider == "openai":
        from focused_research_agent.services.llm_provider_openai import (
            OpenAILLMProvider,
        )

        return OpenAILLMProvider()

    raise ValueError(f"Unsupported LLM provider: {provider}")
