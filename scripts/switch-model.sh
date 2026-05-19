#!/usr/bin/env bash
# 切换 .env 中的默认 DeepSeek 模型并写入 Cursor
# 用法: bash scripts/switch-model.sh deepseek-v4-flash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"
MODEL="${1:-}"

valid_models=(deepseek-v4-pro deepseek-v4-flash)

usage() {
  echo "用法: bash scripts/switch-model.sh <模型名>"
  echo ""
  echo "  deepseek-v4-pro    更强推理（默认）"
  echo "  deepseek-v4-flash  更快、更省 token"
  echo ""
  echo "示例:"
  echo "  bash scripts/switch-model.sh deepseek-v4-flash"
  exit 1
}

[[ -n "$MODEL" ]] || usage

ok=0
for m in "${valid_models[@]}"; do
  [[ "$MODEL" == "$m" ]] && ok=1 && break
done
[[ "$ok" -eq 1 ]] || usage

if [[ ! -f "$ENV_FILE" ]]; then
  echo "未找到 .env，请先: cp config/env.example .env" >&2
  exit 1
fi

if grep -q '^DEEPSEEK_MODEL=' "$ENV_FILE"; then
  if [[ "$(uname)" == Darwin ]]; then
    sed -i '' "s/^DEEPSEEK_MODEL=.*/DEEPSEEK_MODEL=${MODEL}/" "$ENV_FILE"
  else
    sed -i "s/^DEEPSEEK_MODEL=.*/DEEPSEEK_MODEL=${MODEL}/" "$ENV_FILE"
  fi
else
  echo "DEEPSEEK_MODEL=${MODEL}" >> "$ENV_FILE"
fi

echo "✓ .env 已设置 DEEPSEEK_MODEL=${MODEL}"
echo "  → 正在写入 Cursor（请先 Cmd+Q 退出 Cursor）..."
echo ""

exec python3 "${PROJECT_ROOT}/src/apply_config.py"
