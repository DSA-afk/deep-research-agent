"""重点研究代理的共享问题验证助手。

该模块包含用于用户研究的传输中立验证逻辑
问题。 FastAPI 请求可以重复使用相同的验证规则
架构、应用程序层和未来的 UI 层。

从架构上讲，这属于应用程序层，因为它验证
用例输入的质量，而不依赖于 HTTP、CLI 或 UI 详细信息。"""


import re


def validate_and_clean_question(question: object) -> str:

    if not isinstance(question, str):
        raise ValueError("User query must be a string")

    cleaned_question = question.strip()

    if not cleaned_question:
        raise ValueError("No user query provided")

    if len(cleaned_question) < 2:
        raise ValueError("User query is too short to research meaningfully")

    if not re.search(r'[a-zA-Z0-9\u4e00-\u9fff]', cleaned_question):
        raise ValueError("User query must contain meaningful words")
    
    return cleaned_question
