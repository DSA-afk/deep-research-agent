import os
from dotenv import load_dotenv

load_dotenv()


def get_llm_config():
    """从环境变量加载并验证 LLM 配置。

    返回：
        dict：包含提供者、型号、温度的字典，
        最大重试次数和 api_key。

    加薪：
        ValueError：如果缺少所需的环境变量或
        如果温度或 max_retries 无法正确解析。"""
    max_tokens_raw = os.getenv("LLM_MAX_TOKENS", "4096")

    try:
        max_tokens = int(max_tokens_raw)
    except ValueError:
        raise ValueError(f"LLM_MAX_TOKENS must be an int. Got: {max_tokens_raw}")

    provider = os.getenv("LLM_PROVIDER")
    model = os.getenv("LLM_MODEL")
    temp_raw = os.getenv("LLM_TEMPERATURE")
    retries_raw = os.getenv("LLM_MAX_RETRIES")
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL")

    if (
        (not provider or not provider.strip())
        or (not model or not model.strip())
        or (not temp_raw or not temp_raw.strip())
        or (not retries_raw or not retries_raw.strip())
        or (not api_key or not api_key.strip())
    ):
        raise ValueError(
            "LLM provider, LLM Model, LLM temperature, number of retries and api key should be given in .env file!"
        )

    try:
        temperature = float(temp_raw)
    except ValueError:
        raise ValueError(f"LLM_TEMPERATURE must be a float. Got: {temp_raw}")

    try:
        max_retries = int(retries_raw)
    except ValueError:
        raise ValueError(f"LLM_MAX_RETRIES must be an int. Got: {retries_raw}")

    return {
        "provider": provider,
        "model": model,
        "temperature": temperature,
        "max_retries": max_retries,
        "api_key": api_key,
        "max_tokens": max_tokens,
        "base_url": base_url,
    }
