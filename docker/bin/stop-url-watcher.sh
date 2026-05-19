#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="${DIR}/data/url-watcher-host.pid"

pkill -f "url_watcher.py --host-bridge" 2>/dev/null || true

if [[ -f "$PID_FILE" ]]; then
  pid=$(tr -d '\r\n' <"$PID_FILE" 2>/dev/null || true)
  [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
  rm -f "$PID_FILE"
fi

rm -f "${DIR}/data/need-sync"
echo ">>> 已停止宿主机 URL 同步桥接"
