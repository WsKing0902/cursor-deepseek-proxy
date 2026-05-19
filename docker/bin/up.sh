#!/usr/bin/env bash
# 默认方案：Docker + cloudflared → 同步 URL 到 Cursor
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_ROOT="$(cd "$DIR/.." && pwd)"

pkill -f "deepseek-cursor-proxy" 2>/dev/null || true
pkill -f "cloudflared tunnel" 2>/dev/null || true
mkdir -p "${DIR}/data"

if ! docker info >/dev/null 2>&1; then
  echo "错误: Docker 不可用。请启动 Docker Desktop。"
  exit 1
fi

COMPOSE_ARGS=(-f "${DIR}/docker-compose.yml")
[[ -f "${DIR}/.env.docker" ]] && COMPOSE_ARGS+=(--env-file "${DIR}/.env.docker")

if [[ -z "${PYTHON_IMAGE:-}" ]] && [[ ! -f "${DIR}/.env.docker" ]]; then
  for img in \
    "docker.m.daocloud.io/library/python:3.11-slim" \
    "python:3.11-slim" \
    "python:3.11"; do
    if docker image inspect "$img" >/dev/null 2>&1; then
      export PYTHON_IMAGE="$img"
      echo ">>> 使用本机已有基础镜像: $img"
      break
    fi
  done
fi

echo ">>> 构建并启动容器（proxy + url-sync 自动监视）..."
docker compose "${COMPOSE_ARGS[@]}" up -d --build

bash "${DIR}/bin/start-url-watcher.sh"

echo ">>> 等待隧道就绪，同步 Cursor 配置并启动 Cursor..."
python3 "${PROJECT_ROOT}/src/sync_cursor.py" --wait --launch

PUBLIC_URL=$(tr -d '\r\n' <"${DIR}/data/public-url.txt" 2>/dev/null || echo '?')
echo ""
echo "=============================================="
echo "  部署完成，开箱即用"
echo "=============================================="
echo "  公网地址: ${PUBLIC_URL}"
echo "  模型:     deepseek-v4-pro（Agent 模式）"
echo "  查看日志: bash ${DIR}/bin/logs.sh"
echo "  停止服务: bash ${DIR}/bin/down.sh"
echo ""
