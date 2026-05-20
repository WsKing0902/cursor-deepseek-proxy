#!/usr/bin/env bash
# 确保 macOS 宿主机 URL 桥接在运行（容器无法写 .env，必须靠宿主机）
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DIR="${PROJECT_ROOT}/docker"
PID_FILE="${DIR}/data/url-watcher-host.pid"
LOG_FILE="${DIR}/data/url-watcher-host.log"
WATCHER="${PROJECT_ROOT}/src/url_watcher.py"

red()   { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
yellow(){ printf '\033[33m%s\033[0m\n' "$*"; }

if [[ "$(uname)" != "Darwin" ]]; then
  yellow "非 macOS，跳过宿主机桥接检查。"
  exit 0
fi

running=0
if [[ -f "$PID_FILE" ]]; then
  pid=$(tr -d '\r\n' <"$PID_FILE" 2>/dev/null || true)
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    running=1
  fi
fi

if [[ "$running" -eq 1 ]]; then
  green "✓ 宿主机 URL 同步桥接已在运行 (PID $(cat "$PID_FILE"))"
  exit 0
fi

yellow "宿主机 URL 同步桥接未运行（重启电脑后需重新启动，否则隧道变更不会写入 Cursor）。"
echo "正在启动…"
bash "${DIR}/bin/start-url-watcher.sh"
green "✓ 已启动。日志: ${LOG_FILE}"
