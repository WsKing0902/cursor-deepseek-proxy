#!/usr/bin/env bash
# Cursor 退出后修复模型显示名（DeepSeek V4 Pro / Flash，非小写 deepseek）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "${ROOT}/src/apply_config.py" --labels-only
