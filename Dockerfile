FROM python:3.13-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
RUN pip install uv

# 创建非 root 用户 — Hugging Face Spaces 要求
RUN useradd -m -u 1000 appuser

WORKDIR /app

# 先以 root 用户复制项目文件
COPY pyproject.toml .
COPY uv.lock .
COPY src/ src/
COPY start.sh .

# 将 /app 下所有文件的所有权转给 appuser
RUN chown -R appuser:appuser /app

# 在安装依赖之前切换到非 root 用户
USER appuser

# 现在 uv sync 以 appuser 身份运行 — 不会出现权限问题
RUN uv sync --frozen --no-dev

# 使启动脚本可执行
RUN chmod +x start.sh

# 暴露 Streamlit 端口
EXPOSE 7860

CMD ["./start.sh"]