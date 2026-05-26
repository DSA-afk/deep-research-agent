"""Ollama 支持实施 LLM 提供商合同。

该模块提供了OllamaLLMProvider类，它实现了
使用 Ollama 客户端库的 LLMProvider 接口。它同时支持
本地 Ollama 实例和 Ollama Cloud API。

当 LLM_API_KEY 设置且不是“不需要”时，请求将被路由
通过不记名令牌身份验证访问 https://ollama.com 上的 Ollama Cloud。
当未设置API密钥时，默认端口的本地Ollama实例是
代替使用。

JSON 解析管道与 GroqLLMProvider 相同 - 代码围栏
剥离后直接进行 JSON 解析，并进行回退提取
周围的文字。

从架构上来说，该模块属于服务层并实现
适配器模式——它在 Ollama 客户端 API 和
整个项目中使用的内部 LLMProvider 接口。"""

import json
import logging

from ollama import Client

from focused_research_agent.config.llm_config import get_llm_config
from focused_research_agent.interfaces.llm_interface import LLMProvider

logger = logging.getLogger(__name__)


class OllamaLLMProvider(LLMProvider):
    """Ollama 支持实施 LLM 提供商合同。"""

    def __init__(self):
        """使用经过验证的配置初始化 Ollama 客户端。"""
        self.llm_config = get_llm_config()

        api_key = self.llm_config.get("api_key")

        if api_key and api_key.strip() and api_key != "not-needed":
            self.client = Client(
                host="https://ollama.com",
                headers={"Authorization": f"Bearer {api_key}"},
            )
        else:
            self.client = Client()

        self.model = self.llm_config["model"]

    def generate_json(self, prompt: str) -> dict:
        """使用 Ollama 根据提示生成结构化 JSON。

        参数：
            提示：发送给 LLM 的提示。

        返回：
            dict：LLM 的已解析 JSON 输出。

        加薪：
            ValueError：如果提示无效或提供者无效
                不返回可恢复的有效 JSON。"""
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("OllamaLLMProvider: No prompt provided!")

        logger.info("Invoking Ollama LLM with model: %s", self.model)

        updated_prompt = (
                prompt
                + "\n仅返回有效的JSON格式内容，不要使用markdown格式、反引号以及任何多余文字."
        )

        response = self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": updated_prompt}],
        )

        raw_text = response.message.content.strip()
        text = self._strip_code_fences(raw_text)

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.exception("Invalid JSON from LLM: %s", e)

        candidate = self._extract_json_candidate(text)

        if candidate is None:
            raise ValueError(f"LLM did not return JSON. Raw output:\n{text[:400]}")

        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON from LLM: {e}\nRaw output:\n{candidate[:400]}"
            )

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """从 LLM 输出中删除周围的三重反引号代码围栏。

        参数：
            text：LLM 返回的原始文本。

        返回：
            str：存在外部代码围栏的文本已被删除。"""
        if text.startswith("```"):
            lines = text.splitlines()
            if lines:
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            return "\n".join(lines).strip()
        return text

    @staticmethod
    def _extract_json_candidate(text: str) -> str | None:
        """从混合文本中提取可能的 JSON 对象或数组子字符串。

        参数：
            text：LLM 输出，可能包含由额外文本包围的 JSON。

        返回：
            STR | None：如果找到则提取的 JSON 子字符串，否则 None。"""
        obj_start = text.find("{")
        obj_end = text.rfind("}")
        arr_start = text.find("[")
        arr_end = text.rfind("]")

        if obj_start != -1 and obj_end != -1 and obj_start < obj_end:
            return text[obj_start: obj_end + 1]

        if arr_start != -1 and arr_end != -1 and arr_start < arr_end:
            return text[arr_start: arr_end + 1]

        return None
