"""Groq 支持实施 LLM 提供商合同。

该模块提供了 GroqLLMProvider 类，它实现了
LLMProvider接口使用LangChain的init_chat_model与Groq
提供者。它处理提示验证、仅 JSON 指令附加、
代码栅栏剥离，以及从周围文本中提取后备 JSON。

JSON 解析管道分两个阶段工作：
1. 直接在清理后的响应文本上使用 json.loads
2. 如果失败，提取第一个 JSON 对象或数组子字符串并
   尝试解析它

静态助手用于所有纯转换函数
不需要实例状态，遵循与其余部分相同的模式
该项目。

从架构上来说，该模块属于服务层并实现
适配器模式——它在 LangChain/Groq API 和
整个项目中使用的内部 LLMProvider 接口。"""

import json
import logging

from langchain.chat_models import init_chat_model

from focused_research_agent.config.llm_config import get_llm_config
from focused_research_agent.interfaces.llm_interface import LLMProvider

logger = logging.getLogger(__name__)


class GroqLLMProvider(LLMProvider):
    """Groq 支持实施 LLM 提供商合同。"""

    def __init__(self):
        """使用经过验证的配置初始化 Groq LLM 客户端。"""
        self.llm_config = get_llm_config()

        self.llm = init_chat_model(
            model_provider=self.llm_config["provider"],
            model=self.llm_config["model"],
            temperature=self.llm_config["temperature"],
            max_retries=self.llm_config["max_retries"],
            api_key=self.llm_config["api_key"],
            max_tokens=self.llm_config["max_tokens"],
        )

    # ------------------------------------------------------------------
    # 静态辅助函数 — 支持提供者的纯函数，不读取或修改任何实例状态。
    # @staticmethod明确表示了这一点，并防止意外耦合到自身。
    # ------------------------------------------------------------------

    @staticmethod
    def _build_json_only_prompt(prompt: str) -> str:
        """验证提示并附加严格的仅 JSON 指令。

        参数：
            提示：发送给法学硕士的原始提示。

        返回：
            str：经过验证的提示，带有添加的仅 JSON 指令。

        加薪：
            ValueError: 如果提示不是非空字符串。"""
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("GroqLLMProvider: No prompt provided!")

        return (
            prompt
            + "\nReturn ONLY valid JSON. No markdown. No backticks. No extra text."
        )

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """从 LLM 输出中删除周围的三重反引号代码围栏。

        这会处理诸如“``json ...``”之类的响应并返回
        当不存在代码围栏时，内部内容不变。

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

        该方法首先查找最外层的 JSON 对象，如果没有
        找到后，返回到 JSON 数组。

        参数：
            text：LLM 输出，可能包含由额外文本包围的 JSON。

        返回：
            STR | None：如果找到则提取的 JSON 子字符串，否则 None。"""
        obj_start = text.find("{")
        obj_end = text.rfind("}")
        arr_start = text.find("[")
        arr_end = text.rfind("]")

        if obj_start != -1 and obj_end != -1 and obj_start < obj_end:
            return text[obj_start : obj_end + 1]

        if arr_start != -1 and arr_end != -1 and arr_start < arr_end:
            return text[arr_start : arr_end + 1]

        return None

    @staticmethod
    def _extract_text_from_content(content: str | list) -> str:
        """从 LangChain 响应内容值中提取纯文本字符串。

        LangChain声明response.content为str |列表[任意]。海峡
        分支是纯文本模型（例如 Groq）的正常路径。的
        列表分支携带多模式内容块（带有“文本”的字典）
        键）由具有视觉或音频功能的模型使用。这个方法处理
        两个分支，因此generate_json的其余部分始终与
        普通字符串。

        参数：
            content：LangChain响应返回的原始内容值
                对象。纯字符串或内容块列表
                听写。

        返回：
            str：从内容值中提取的纯文本。返回一个
                如果内容既不是 str 也不是列表，则为空字符串。"""
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            # 每个块通常为 {"type": "text", "text": "..."}。
            # 对于任何非 dict 项，回退到 str(block) 。
            text_parts = []

            for block in content:
                if isinstance(block, dict):
                    text_parts.append(block.get("text", ""))
                else:
                    text_parts.append(str(block))

            return "".join(text_parts)

        return ""

    # ------------------------------------------------------------------
    # 实例方法 — 使用 self.llm（实例状态）调用模型，并
    # 调用模型，并调用上述静态辅助函数。
    # ------------------------------------------------------------------

    def generate_json(self, prompt: str) -> dict:
        """使用 Groq 根据提示生成结构化 JSON。

        该方法验证提示，附加仅 JSON 的指令，
        调用 LLM，删除代码围栏（如果存在），并首先尝试
        直接JSON解析。如果失败，它会尝试提取 JSON
        来自周围文本的对象或数组并解析它。

        参数：
            提示：发送给 LLM 的提示。

        返回：
            dict：LLM 的已解析 JSON 输出。

        加薪：
            ValueError: 如果提示无效或者提供者不
                返回可恢复的有效 JSON。"""
        updated_prompt = self._build_json_only_prompt(prompt)
        logger.info("Invoking Groq LLM with model: %s", self.llm_config["model"])
        response = self.llm.invoke(updated_prompt)

        raw_text = self._extract_text_from_content(response.content)
        text = self._strip_code_fences(raw_text.strip())

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
