#!/bin/sh
# 仅本地代理，不启动 cloudflared
set -eu

PROXY_HOST="${PROXY_HOST:-0.0.0.0}"
PROXY_PORT="${PROXY_PORT:-9000}"
DATA_DIR="${DATA_DIR:-/data}"
LOCAL_URL="http://127.0.0.1:${PROXY_PORT}/v1"

mkdir -p "$DATA_DIR"
echo "[local] proxy ${PROXY_HOST}:${PROXY_PORT}"
echo "[local] Cursor Base URL: ${LOCAL_URL}"

CONFIG_ARG=""
if [ -f "${DATA_DIR}/config.yaml" ]; then
  CONFIG_ARG="--config ${DATA_DIR}/config.yaml"
fi
deepseek-cursor-proxy ${CONFIG_ARG} --no-ngrok --host "$PROXY_HOST" --port "$PROXY_PORT" \
  >"${DATA_DIR}/proxy.log" 2>&1 &
PROXY_PID=$!

i=0
while [ "$i" -lt 30 ]; do
  if curl -sf "http://127.0.0.1:${PROXY_PORT}/v1/models" -H "Authorization: Bearer x" >/dev/null 2>&1; then
    break
  fi
  i=$((i + 1))
  sleep 1
done

curl -sf "http://127.0.0.1:${PROXY_PORT}/v1/models" -H "Authorization: Bearer x" >/dev/null \
  || { tail -30 "${DATA_DIR}/proxy.log"; exit 1; }

printf '%s\n' "$LOCAL_URL" > "${DATA_DIR}/public-url.txt"
echo "=============================================="
echo " LOCAL ONLY (no Cloudflare)"
echo " Cursor Base URL: ${LOCAL_URL}"
echo "=============================================="

tail -F "${DATA_DIR}/proxy.log" &
wait "$PROXY_PID"
