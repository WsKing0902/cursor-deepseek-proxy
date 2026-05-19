#!/usr/bin/env bash
# 容器已在跑、仅 URL 变化时执行
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec python3 "${ROOT}/src/sync_cursor.py" "$@"
