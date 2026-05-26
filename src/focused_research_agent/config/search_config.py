import os
from dotenv import load_dotenv

load_dotenv()


def get_search_config():
    """从环境变量加载并验证搜索配置。

    返回：
        dict：包含provider、api_key和max_results的字典。

    加薪：
        ValueError：如果缺少必需的环境变量或者如果
        SEARCH_MAX_RESULTS 不是正整数。"""
    search_provider = os.getenv("SEARCH_PROVIDER")
    search_api_key = os.getenv("SEARCH_API_KEY")
    search_max_results = os.getenv("SEARCH_MAX_RESULTS")
    search_depth = os.getenv("SEARCH_DEPTH")

    if (
        (not search_provider or not search_provider.strip())
        or (not search_api_key or not search_api_key.strip())
        or (not search_max_results or not search_max_results.strip())
        or (not search_depth or not search_depth.strip())
    ):
        raise ValueError(
            "Search provider, search provider api key, max results and search depth should be given in .env file!"
        )

    try:
        search_max_results = int(search_max_results)
    except ValueError:
        raise ValueError(
            f"SEARCH_MAX_RESULTS must be an int. Got: {search_max_results}"
        )

    if search_max_results <= 0:
        raise ValueError("SEARCH_MAX_RESULTS must be a positive integer!")

    search_depth = search_depth.strip().lower()

    if search_depth not in ["basic", "advanced"]:
        raise ValueError(
            f"SEARCH_DEPTH must be either 'basic' or 'advanced'. Got: {search_depth}"
        )

    return {
        "provider": search_provider,
        "api_key": search_api_key,
        "max_results": search_max_results,
        "search_depth": search_depth,
    }
