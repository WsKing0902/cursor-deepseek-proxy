#!/usr/bin/env bash
# DeepSeek + Cursor 链路诊断
set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"
URL_FILE="${PROJECT_ROOT}/docker/data/public-url.txt"
PROXY_PORT=9000

red()    { printf '\033[31m%s\033[0m\n' "$*"; }
green()  { printf '\033[32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }

DEEPSEEK_API_KEY=""
CURSOR_BASE_URL=""
while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line//$'\r'/}"
  [[ "$line" =~ ^DEEPSEEK_API_KEY=(.*)$ ]] && DEEPSEEK_API_KEY="${BASH_REMATCH[1]}"
  [[ "$line" =~ ^CURSOR_BASE_URL=(.*)$ ]] && CURSOR_BASE_URL="${BASH_REMATCH[1]}"
done <"$ENV_FILE"

echo "========== 1. .env =========="
[[ -n "$DEEPSEEK_API_KEY" ]] && green "DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY:0:8}...${DEEPSEEK_API_KEY: -4}" || red "未配置 DEEPSEEK_API_KEY"
[[ -n "$CURSOR_BASE_URL" ]] && echo "CURSOR_BASE_URL: $CURSOR_BASE_URL" || yellow "CURSOR_BASE_URL 为空"

echo ""
echo "========== 2. DeepSeek 官方 API =========="
CODE=$(curl -s -o /tmp/ds-verify.json -w "%{http_code}" -m 15 \
  "https://api.deepseek.com/v1/models" \
  -H "Authorization: Bearer ${DEEPSEEK_API_KEY}" || echo "000")
if [[ "$CODE" == "200" ]]; then
  green "官方 API: 200 OK — Key 有效"
elif [[ "$CODE" == "401" ]]; then
  red "官方 API: 401 — Key 无效/过期/余额不足"
else
  red "官方 API: HTTP $CODE"
fi

echo ""
echo "========== 3. 本地代理 :9000 =========="
if curl -sf -m 3 "http://127.0.0.1:${PROXY_PORT}/v1/models" -H "Authorization: Bearer x" >/dev/null 2>&1; then
  green "本地代理可访问"
else
  red "本地代理未运行 — 请执行: bash deploy.sh"
fi

echo ""
echo "========== 4. 公网隧道 =========="
if [[ -n "$CURSOR_BASE_URL" ]]; then
  CODE=$(curl -s -o /tmp/tunnel-verify.json -w "%{http_code}" -m 15 \
    "${CURSOR_BASE_URL%/}/models" \
    -H "Authorization: Bearer ${DEEPSEEK_API_KEY}" || echo "000")
  if [[ "$CODE" == "200" ]]; then
    green "隧道 URL: 200 OK"
  else
    red "隧道 URL: HTTP $CODE — 可能已失效，请重新 bash deploy.sh"
  fi
fi

echo ""
echo "========== 5. Docker 容器 =========="
if docker ps --filter name=cursor-deepseek-proxy --format '{{.Names}} {{.Status}}' 2>/dev/null | grep -q .; then
  docker ps --filter name=cursor-deepseek-proxy --format '  {{.Names}} — {{.Status}}'
  green "容器在运行"
else
  yellow "容器未运行（如果用的本机模式，可忽略此项）"
fi

echo ""
echo "========== 6. Cursor 配置 =========="
DB="${HOME}/Library/Application Support/Cursor/User/globalStorage/state.vscdb"
if [[ -f "$DB" ]]; then
  CUR_KEY=$(sqlite3 "$DB" "SELECT value FROM ItemTable WHERE key='cursorAuth/openAIKey';" 2>/dev/null || true)
  if [[ -n "$CUR_KEY" ]]; then
    [[ "$CUR_KEY" == "$DEEPSEEK_API_KEY" ]] && green "Cursor openAIKey 一致" || red "Cursor openAIKey 不一致"
  fi
  sqlite3 "$DB" "SELECT value FROM ItemTable WHERE key='src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl.persistentStorage.applicationUser';" 2>/dev/null \
    | python3 -c "import sys,json;d=json.load(sys.stdin);print('  openAIBaseUrl:',d.get('openAIBaseUrl'));print('  composerModel:',d.get('aiSettings',{}).get('composerModel','?'))" 2>/dev/null || true
fi

echo ""
echo "========== 建议 =========="
echo "若 Key 无效 → 更新 .env 中的 DEEPSEEK_API_KEY，重新 bash deploy.sh"
echo "若隧道失效 → 重新 bash deploy.sh 或 bash docker/bin/restart.sh"
echo "若配置不一致 → Cmd+Q 退出 Cursor，执行 python3 src/apply_config.py"
