# ========== Builder ==========
FROM python:3.13-slim AS builder

WORKDIR /app

# 替换 Debian 源（使用稳定镜像）
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources

# 安装构建工具和 TA-Lib C 库
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential wget \
    && wget https://github.com/TA-Lib/ta-lib/releases/download/v0.4.0/ta-lib-0.4.0-src.tar.gz \
    && tar -xzf ta-lib-0.4.0-src.tar.gz \
    && cd ta-lib/ \
    && ./configure --prefix=/usr \
    && make && make install \
    && cd .. && rm -rf ta-lib* \
    && apt-get purge -y build-essential wget \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN chmod +x /usr/local/bin/uv

# 复制项目文件
COPY pyproject.toml .
COPY mizar ./mizar

# 核心安装逻辑
RUN uv pip install --system --no-cache-dir . \
    && uv pip install --system --no-cache-dir --no-deps mootdx==0.11.7 \
    && uv pip install --system --no-cache-dir chromadb==1.5.0 \
    && uv pip install --system --no-cache-dir websocket-client pytz tdxpy simplejson

# ========== Runtime ==========
FROM python:3.13-slim

ENV MIZAR_SKIP_INTEGRITY_CHECK=true

WORKDIR /app

RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/lib/libta_lib* /usr/lib/
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# ✅ 关键：复制 pyproject.toml 到运行时镜像
COPY --from=builder /app/pyproject.toml /app/pyproject.toml
# 新增：复制整个 config 目录
COPY config /app/config

# 创建用户和数据目录
RUN useradd -m -u 1000 mizar && chown -R mizar:mizar /app
USER mizar
# /app/models
RUN mkdir -p /app/data /app/models /app/storage /app/logs

CMD ["sh", "-c", "mizar --help; tail -f /dev/null"]