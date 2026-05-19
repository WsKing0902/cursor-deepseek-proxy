#!/usr/bin/env bash
# ============================================================
#  一键部署（推荐入口）
#  1. 克隆项目
#  2. 编辑 .env 填入 DEEPSEEK_API_KEY
#  3. bash deploy.sh
#  → Docker 启动 → 同步隧道 URL → 自动打开 Cursor
# ============================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"
ENV_EXAMPLE="${PROJECT_ROOT}/config/env.example"

red()    { printf '\033[31m%s\033[0m\n' "$*"; }
green()  { printf '\033[32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }
bold()   { printf '\033[1m%s\033[0m\n' "$*"; }

echo ""
bold "=============================================="
bold "  Cursor × DeepSeek V4 — 一键部署"
bold "=============================================="
echo ""

# --- .env ---
if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f "$ENV_EXAMPLE" ]]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    green "✓ 已从 .env.example 创建 .env"
  fi
  echo ""
  yellow "请先编辑 .env 填写 DEEPSEEK_API_KEY，然后重新运行:"
  echo "  nano ${ENV_FILE}"
  echo "  bash scripts/deploy.sh"
  echo ""
  exit 0
fi

DEEPSEEK_API_KEY=""
while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line//$'\r'/}"
  [[ "$line" =~ ^DEEPSEEK_API_KEY=(.*)$ ]] && DEEPSEEK_API_KEY="${BASH_REMATCH[1]}"
done <"$ENV_FILE"

if [[ -z "$DEEPSEEK_API_KEY" ]] || [[ "$DEEPSEEK_API_KEY" == "sk-your-key-here" ]]; then
  red "✗ 请在 .env 中填写真实的 DEEPSEEK_API_KEY"
  echo "  获取: https://platform.deepseek.com → API Keys"
  exit 1
fi
green "✓ API Key 已配置 (${DEEPSEEK_API_KEY:0:8}...${DEEPSEEK_API_KEY: -4})"

if ! docker info >/dev/null 2>&1; then
  red "✗ Docker 未运行，请先启动 Docker Desktop"
  exit 1
fi
green "✓ Docker 可用"

echo ""
echo ">>> 启动 Docker 代理 + 隧道，并配置 Cursor…"
exec bash "${PROJECT_ROOT}/docker/bin/up.sh"
