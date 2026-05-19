#!/usr/bin/env bash
# 重启 Docker 容器并同步新隧道 URL 到 Cursor
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_ROOT="$(cd "$DIR/.." && pwd)"
COMPOSE_ARGS=(-f "${DIR}/docker-compose.yml")
[[ -f "${DIR}/.env.docker" ]] && COMPOSE_ARGS+=(--env-file "${DIR}/.env.docker")

docker compose "${COMPOSE_ARGS[@]}" restart
bash "${DIR}/bin/start-url-watcher.sh"
python3 "${PROJECT_ROOT}/src/sync_cursor.py" --wait --launch
