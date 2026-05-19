#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
bash "${DIR}/bin/stop-url-watcher.sh" 2>/dev/null || true
docker compose -f "${DIR}/docker-compose.yml" down --remove-orphans
echo "容器与 URL 监视已停止"
