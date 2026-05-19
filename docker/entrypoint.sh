#!/bin/sh
set -eu
PROXY_HOST="${PROXY_HOST:-0.0.0.0}"
PROXY_PORT="${PROXY_PORT:-9000}"
DATA_DIR="${DATA_DIR:-/data}"
mkdir -p "$DATA_DIR"
shutdown() { kill "$PROXY_PID" "$CF_PID" 2>/dev/null || true; }
trap shutdown INT TERM
echo "[entrypoint] starting proxy ${PROXY_HOST}:${PROXY_PORT}"
CONFIG_ARG=""
if [ -f "${DATA_DIR}/config.yaml" ]; then
  CONFIG_ARG="--config ${DATA_DIR}/config.yaml"
fi
deepseek-cursor-proxy ${CONFIG_ARG} --no-ngrok --host "$PROXY_HOST" --port "$PROXY_PORT" >"${DATA_DIR}/proxy.log" 2>&1 &
PROXY_PID=$!
i=0
while [ "$i" -lt 30 ]; do
  curl -sf "http://127.0.0.1:${PROXY_PORT}/v1/models" -H "Authorization: Bearer x" >/dev/null 2>&1 && break
  i=$((i+1)); sleep 1
done
curl -sf "http://127.0.0.1:${PROXY_PORT}/v1/models" -H "Authorization: Bearer x" >/dev/null || { tail -20 "${DATA_DIR}/proxy.log"; exit 1; }
: >"${DATA_DIR}/cloudflared.log"
/usr/local/bin/cloudflared tunnel --url "http://127.0.0.1:${PROXY_PORT}" >>"${DATA_DIR}/cloudflared.log" 2>&1 &
CF_PID=$!
PUBLIC_URL=""
i=0
while [ "$i" -lt 90 ]; do
  PUBLIC_URL=$(grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' "${DATA_DIR}/cloudflared.log" | grep -v api.trycloudflare | head -1 || true)
  [ -n "$PUBLIC_URL" ] && break
  i=$((i+1)); sleep 1
done
[ -n "$PUBLIC_URL" ] || { tail -15 "${DATA_DIR}/cloudflared.log"; exit 1; }
PUBLIC_URL="${PUBLIC_URL%/}/v1"
printf '%s\n' "$PUBLIC_URL" > "${DATA_DIR}/public-url.txt"
echo "=============================================="
echo " Cursor Base URL: ${PUBLIC_URL}"
echo "=============================================="
tail -F "${DATA_DIR}/proxy.log" "${DATA_DIR}/cloudflared.log" &
wait "$PROXY_PID"
