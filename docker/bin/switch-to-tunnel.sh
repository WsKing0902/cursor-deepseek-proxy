#!/usr/bin/env bash
# Switch Cursor back to Cloudflare Tunnel
set -eu

DIR="$(cd "$(dirname "$0")/.." && pwd)"
URL_FILE="${DIR}/data/public-url.txt"

if [ -f "$URL_FILE" ]; then
  TUNNEL_URL="$(tr -d '\r\n' < "$URL_FILE")"
else
  echo "No tunnel URL file found. Run up.sh first."
  exit 1
fi

echo ">>> Switching Cursor back to tunnel: ${TUNNEL_URL}"

python3 -c "
import sqlite3, json
from pathlib import Path

url = '${TUNNEL_URL}'.rstrip('/')
url = url if url.endswith('/v1') else url + '/v1'
db = Path.home() / 'Library/Application Support/Cursor/User/globalStorage/state.vscdb'
key_store = 'src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl.persistentStorage.applicationUser'

conn = sqlite3.connect(db)
row = conn.execute('SELECT value FROM ItemTable WHERE key=?', (key_store,)).fetchone()
d = json.loads(row[0])
d['openAIBaseUrl'] = url.rstrip('/')
conn.execute('INSERT OR REPLACE INTO ItemTable (key,value) VALUES (?,?)',
    (key_store, json.dumps(d, separators=(',',':'))))
conn.commit()
conn.close()
print(f'Reverted to: {url}')
"

osascript -e 'tell application "Cursor" to quit' 2>/dev/null || true
echo "Done. Reopen Cursor."
