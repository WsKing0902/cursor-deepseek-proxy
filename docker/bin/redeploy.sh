#!/usr/bin/env bash
# 重新部署：重建容器 + 启动 url-sync + 同步 Cursor
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_ROOT="$(cd "$DIR/.." && pwd)"

exec bash "${DIR}/bin/up.sh"
