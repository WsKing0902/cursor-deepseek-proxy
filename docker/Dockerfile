# 默认用本机常见的 3.11-slim（可通过 build-arg 覆盖）
# 查看已有镜像: docker images | grep python
ARG PYTHON_IMAGE=python:3.11-slim
FROM ${PYTHON_IMAGE}

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates tini \
    && rm -rf /var/lib/apt/lists/*

ARG TARGETARCH
RUN case "${TARGETARCH}" in \
      amd64) CF=amd64 ;; \
      arm64) CF=arm64 ;; \
      *) CF=amd64 ;; \
    esac \
    && curl -fsSL -o /usr/local/bin/cloudflared \
      "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${CF}" \
    && chmod +x /usr/local/bin/cloudflared

WORKDIR /app
RUN pip install --no-cache-dir \
    "https://github.com/yxlao/deepseek-cursor-proxy/archive/refs/heads/main.zip"

COPY entrypoint.sh entrypoint-local.sh /
RUN chmod +x /entrypoint.sh /entrypoint-local.sh

ENV PROXY_HOST=0.0.0.0
ENV PROXY_PORT=9000
ENV DATA_DIR=/data

EXPOSE 9000
VOLUME ["/data"]

ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]
