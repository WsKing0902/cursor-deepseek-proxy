#!/usr/bin/env bash
# 安装 macOS 登录项：开机自动启动宿主机 URL 同步桥接
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.cursor-deepseek.url-sync"
PLIST="${HOME}/Library/LaunchAgents/${LABEL}.plist"
WATCHER="${PROJECT_ROOT}/src/url_watcher.py"
LOG_FILE="${PROJECT_ROOT}/docker/data/url-watcher-host.log"

red()   { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
yellow(){ printf '\033[33m%s\033[0m\n' "$*"; }

if [[ "$(uname)" != "Darwin" ]]; then
  red "仅支持 macOS。"
  exit 1
fi

PYTHON="$(command -v python3)"
[[ -x "$PYTHON" ]] || { red "未找到 python3"; exit 1; }

mkdir -p "${PROJECT_ROOT}/docker/data" "${HOME}/Library/LaunchAgents"

cat >"$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON}</string>
    <string>${WATCHER}</string>
    <string>--host-bridge</string>
    <string>--interval</string>
    <string>5</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${PROJECT_ROOT}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PROJECT_ROOT</key>
    <string>${PROJECT_ROOT}</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${LOG_FILE}</string>
  <key>StandardErrorPath</key>
  <string>${LOG_FILE}</string>
</dict>
</plist>
EOF

# 停止旧的手动 nohup 进程，避免重复
bash "${PROJECT_ROOT}/docker/bin/stop-url-watcher.sh" 2>/dev/null || true

launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl enable "gui/$(id -u)/${LABEL}"
launchctl kickstart -k "gui/$(id -u)/${LABEL}" 2>/dev/null || true

green "✓ 已安装登录项: ${PLIST}"
green "  开机后将自动监视隧道 URL 并同步 Cursor（需 Docker 容器在跑）。"
echo ""
yellow "macOS 可能弹出权限提示："
echo "  · 若同步 Cursor 失败，请在 系统设置 → 隐私与安全性 中允许 Terminal/Cursor 访问。"
echo "  · 写入 Cursor 配置前脚本会尝试退出 Cursor（Cmd+Q）。"
echo ""
echo "卸载: launchctl bootout gui/$(id -u)/${LABEL}; rm ${PLIST}"
