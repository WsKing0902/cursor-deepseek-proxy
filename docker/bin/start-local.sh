#!/usr/bin/env bash
# 不依赖 Docker：本机启动代理 + cloudflared（Docker 异常时用）
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="${HOME}/.cursor/deepseek-v4-pro"
ENV_FILE="${ROOT}/.env"
APPLY_PY="${ROOT}/apply-config.py"
LOG_DIR="${HOME}/deepseek-v4-pro-logs"
PROXY_BIN="${HOME}/deepseek-v4-pro-venv/bin/deepseek-cursor-proxy"
PROXY_PORT=9000
URL_FILE="${LOG_DIR}/public-url.txt"

export PATH="${HOME}/bin:/opt/homebrew/bin:/usr/local/bin:${PATH}"
mkdir -p "$LOG_DIR"

DEEPSEEK_API_KEY=""
while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line//$'\r'/}"
  [[ "$line" =~ ^DEEPSEEK_API_KEY=(.*)$ ]] && DEEPSEEK_API_KEY="${BASH_REMATCH[1]}"
done <"$ENV_FILE"
[[ -n "$DEEPSEEK_API_KEY" ]] || { echo "请配置 ${ENV_FILE} 中的 DEEPSEEK_API_KEY"; exit 1; }

pkill -f "deepseek-cursor-proxy" 2>/dev/null || true
pkill -f "cloudflared tunnel" 2>/dev/null || true

if [[ ! -x "$PROXY_BIN" ]]; then
  echo "安装代理到 ~/deepseek-v4-pro-venv ..."
  curl -fsSL -o /tmp/dcp.zip https://github.com/yxlao/deepseek-cursor-proxy/archive/refs/heads/main.zip
  unzip -q -o /tmp/dcp.zip -d /tmp
  /opt/homebrew/bin/python3.12 -m venv "${HOME}/deepseek-v4-pro-venv"
  "${HOME}/deepseek-v4-pro-venv/bin/pip" install -q /tmp/deepseek-cursor-proxy-main
fi

nohup "$PROXY_BIN" --no-ngrok --port "$PROXY_PORT" >"${LOG_DIR}/proxy.log" 2>&1 &
echo $! >"${LOG_DIR}/proxy.pid"
sleep 2
curl -sf "http://127.0.0.1:${PROXY_PORT}/v1/models" -H "Authorization: Bearer x" >/dev/null

if [[ ! -x "${HOME}/bin/cloudflared" ]]; then
  arch=$(uname -m); [[ "$arch" == arm64 ]] && a=arm64 || a=amd64
  curl -fsSL -o /tmp/cf.tgz -L "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-${a}.tgz"
  mkdir -p "${HOME}/bin"
  tar -xzf /tmp/cf.tgz -C "${HOME}/bin" cloudflared
  chmod +x "${HOME}/bin/cloudflared"
fi

: >"${LOG_DIR}/cloudflared.log"
nohup "${HOME}/bin/cloudflared" tunnel --url "http://127.0.0.1:${PROXY_PORT}" >>"${LOG_DIR}/cloudflared.log" 2>&1 &
echo $! >"${LOG_DIR}/tunnel.pid"

url=""
for _ in $(seq 1 60); do
  url=$(grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' "${LOG_DIR}/cloudflared.log" | grep -v api.trycloudflare | head -1 || true)
  [[ -n "$url" ]] && break
  sleep 1
done
[[ -n "$url" ]] || { tail -15 "${LOG_DIR}/cloudflared.log"; exit 1; }
url="${url%/}/v1"
echo "$url" >"$URL_FILE"
echo "公网 URL: $url"

export CURSOR_BASE_URL="$url"
python3 - <<PY
from pathlib import Path
url = """${url}"""
p = Path("${ENV_FILE}")
lines = p.read_text(encoding="utf-8").replace("\r\n", "\n").splitlines()
out = [f"CURSOR_BASE_URL={url}" if l.startswith("CURSOR_BASE_URL=") else l for l in lines]
if not any(l.startswith("CURSOR_BASE_URL=") for l in lines):
    out.append(f"CURSOR_BASE_URL={url}")
p.write_text("\n".join(out) + "\n", encoding="utf-8")
PY

if pgrep -x Cursor >/dev/null 2>&1; then
  osascript -e 'tell application "Cursor" to quit' 2>/dev/null || true
  sleep 3
fi
python3 "$APPLY_PY"

echo ""
echo "本机模式已启动。日志: ${LOG_DIR}/"
echo "停止: pkill -f deepseek-cursor-proxy; pkill -f cloudflared"
