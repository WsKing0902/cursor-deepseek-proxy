#!/usr/bin/env bash
# Switch Cursor to local direct connect (bypass Cloudflare)
set -eu

LOCAL_URL="http://127.0.0.1:9000/v1"
MODEL="deepseek-v4-pro"
ENV_FILE="${HOME}/.cursor/deepseek-v4-pro/.env"

echo ">>> Switching Cursor to local: ${LOCAL_URL}"

# 1. Update .env
if [ -f "$ENV_FILE" ]; then
  python3 -c "
from pathlib import Path
p = Path('${ENV_FILE}')
lines = p.read_text(encoding='utf-8').replace('\r\n','\n').splitlines() if p.exists() else []
out, found = [], False
for line in lines:
    if line.startswith('CURSOR_BASE_URL='):
        out.append('CURSOR_BASE_URL=${LOCAL_URL}')
        found = True
    else:
        out.append(line)
if not found:
    out.append('CURSOR_BASE_URL=${LOCAL_URL}')
p.write_text('\n'.join(out)+'\n', encoding='utf-8')
print('updated .env')
"
fi

# 2. Write to Cursor DB
python3 -c "
import sqlite3, json
from pathlib import Path

url = '${LOCAL_URL}'.rstrip('/')
model = '${MODEL}'
db = Path.home() / 'Library/Application Support/Cursor/User/globalStorage/state.vscdb'
key_store = 'src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl.persistentStorage.applicationUser'

conn = sqlite3.connect(db)
row = conn.execute('SELECT value FROM ItemTable WHERE key=?', (key_store,)).fetchone()
d = json.loads(row[0])

old_url = d.get('openAIBaseUrl', 'NOT SET')
d['openAIBaseUrl'] = url
d['useOpenAIKey'] = True

ai = d.setdefault('aiSettings', {})
ums = list(ai.get('userAddedModels') or [])
if model not in ums:
    ums.append(model)
ai['userAddedModels'] = ums

for mode in ['composer','quick-agent','cmd-k']:
    if mode in ai.get('modelConfig', {}):
        ai['modelConfig'][mode]['modelName'] = model
        ai['modelConfig'][mode]['selectedModels'] = [{'modelId': model, 'parameters': []}]
ai['composerModel'] = model

conn.execute('INSERT OR REPLACE INTO ItemTable (key,value) VALUES (?,?)',
    (key_store, json.dumps(d, separators=(',',':'))))
conn.commit()
conn.close()

print(f'Old URL: {old_url}')
print(f'New URL: {url}')
print('Cursor config written.')
"

# 3. Restart Cursor
if pgrep -x Cursor >/dev/null 2>&1; then
  echo ">>> Restarting Cursor..."
  osascript -e 'tell application "Cursor" to quit' 2>/dev/null || true
  sleep 3
fi

echo ""
echo "Done! Reopen Cursor - it will use local proxy directly."
echo "If Cursor requires HTTPS, revert with:"
echo "  bash ${HOME}/deepseek-cursor-docker/switch-to-tunnel.sh"
