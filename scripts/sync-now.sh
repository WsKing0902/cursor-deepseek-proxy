#!/usr/bin/env bash
# 立即同步隧道 URL → .env → Cursor（1033 / Network Error 时用）
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo ">>> 1. 确保宿主机同步桥接…"
bash "${PROJECT_ROOT}/scripts/ensure-host-sync.sh"

echo ">>> 2. 等待隧道 URL 并写入 Cursor…"
python3 "${PROJECT_ROOT}/src/sync_cursor.py" --wait --launch

echo ">>> 完成。"
