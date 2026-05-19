#!/usr/bin/env bash
# 启动 macOS 宿主机 URL 同步桥接（配合 compose 的 url-sync 容器）
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_ROOT="$(cd "$DIR/.." && pwd)"
PID_FILE="${DIR}/data/url-watcher-host.pid"
LOG_FILE="${DIR}/data/url-watcher-host.log"
WATCHER="${PROJECT_ROOT}/src/url_watcher.py"

mkdir -p "${DIR}/data"

if [[ "$(uname)" != "Darwin" ]]; then
  echo ">>> 非 macOS，跳过宿主机 url-sync 桥接（由容器负责 .env）"
  exit 0
fi

# 停止旧进程
if [[ -f "$PID_FILE" ]]; then
  old_pid=$(tr -d '\r\n' <"$PID_FILE" 2>/dev/null || true)
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    kill "$old_pid" 2>/dev/null || true
    sleep 0.5
  fi
fi
pkill -f "url_watcher.py --host-bridge" 2>/dev/null || true

echo ">>> 启动宿主机 URL 同步桥接…"
nohup python3 "$WATCHER" --host-bridge --interval 5 >>"$LOG_FILE" 2>&1 &
echo $! >"$PID_FILE"
echo ">>> 桥接 PID: $(cat "$PID_FILE")，日志: $LOG_FILE"
