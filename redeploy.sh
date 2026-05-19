#!/usr/bin/env bash
# ============================================================
#  一键重新部署（重建 Docker + 自动 URL 监视 + 同步 Cursor）
#  用法: bash redeploy.sh
# ============================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"

red()    { printf '\033[31m%s\033[0m\n' "$*"; }
green()  { printf '\033[32m%s\033[0m\n' "$*"; }
bold()   { printf '\033[1m%s\033[0m\n' "$*"; }

echo ""
bold "=============================================="
bold "  Cursor × DeepSeek V4 — 重新部署"
bold "=============================================="
echo ""

if [[ ! -f "$ENV_FILE" ]]; then
  red "✗ 未找到 .env，请先: cp config/env.example .env 并填写 DEEPSEEK_API_KEY"
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  red "✗ Docker 未运行，请先启动 Docker Desktop"
  exit 1
fi
green "✓ Docker 可用"

echo ""
echo ">>> 停止旧服务…"
bash "${PROJECT_ROOT}/docker/bin/down.sh" 2>/dev/null || true

echo ""
echo ">>> 重新构建并启动（含 url-sync 自动监视）…"
exec bash "${PROJECT_ROOT}/docker/bin/up.sh"
