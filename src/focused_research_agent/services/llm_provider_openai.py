"""OpenAI 兼容 API 实现 LLM 提供商合同。

用户只需配置 api_key 和 base_url 即可接入任意服务。

JSON 解析管道与 GroqLLMProvider 相同 - 代码围栏
剥离后直接进行 JSON 解析，并进行回退提取
周围的文字。

从架构上来说，该模块属于服务层并实现
适配器模式——它在 OpenAI 兼容 API 和
整个项目中使用的内部 LLMProvider 接口之间进行转换。"""

import json
import logging

from openai import OpenAI

from focused_research_agent.config.llm_config import get_llm_config
from focused_research_agent.interfaces.llm_interface import LLMProvider

logger = logging.getLogger(__name__)


class OpenAILLMProvider(LLMProvider):
    """OpenAI 支持实施 LLM 提供商。"""

    def __init__(self):
        self.llm_config = get_llm_config()
        self.client = OpenAI(
            api_key=self.llm_config["api_key"],
            base_url=self.llm_config["base_url"],
            max_retries=self.llm_config["max_retries"],
        )
        self.model = self.llm_config["model"]

    @staticmethod
    def _build_json_only_prompt(prompt: str) -> str:
        """验证提示并附加严格的仅 JSON 指令。
        参数：
            prompt：发送给 LLM 的原始提示。
        返回：
            str：经过验证的提示，带有添加的仅 JSON 指令。
        抛出：
            ValueError：如果提示不是非空字符串。"""

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("OpenAILLMProvider: No prompt provided!")
        return (
                prompt
                + "\n仅返回有效的JSON格式内容，不要使用markdown格式、反引号以及任何多余文字."
        )

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """从 LLM 输出中删除周围三重反引号代码围栏。
        参数：
            text：LLM 输出，可能包含由额外文本包围的 JSON。
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

    def generate_json(self, prompt: str) -> dict:
        """使用 OpenAI 根据提示生成结构化 JSON。

        该方法验证提示，附加仅 JSON 的指令，
        调用 LLM，删除代码围栏（如果存在），并首先尝试
        直接 JSON 解析。如果失败，它会尝试提取 JSON
        来自周围文本的对象或数组并解析它。
        参数：
            prompt：发送给 LLM 的提示。
        返回：
            dict：LLM 的已解析 JSON 输出。
        抛出：
            ValueError：如果提示无效或者提供者不
                返回可恢复的有效 JSON。"""

        updated_prompt = self._build_json_only_prompt(prompt)
        logger.info("Invoking OpenAI LLM with model: %s", self.model)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": updated_prompt}],
            temperature=self.llm_config["temperature"],
            max_tokens=self.llm_config["max_tokens"],
        )

        raw_text = response.choices[0].message.content.strip()
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
            logger.exception(
                "Invalid JSON from LLM: %s\nRaw output:\n%s", e, candidate[:400]
            )
            raise ValueError(
                f"Invalid JSON from LLM: {e}\nRaw output:\n{candidate[:400]}"
            )
