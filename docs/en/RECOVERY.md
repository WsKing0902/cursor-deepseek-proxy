# Recovery & restart guide

> **Languages / 语言:** [中文](../RECOVERY.md) · [English](RECOVERY.md)

When the tunnel URL changes, Cursor cannot connect, or **deepseek-v4-flash** is missing from the picker, use this guide.

---

## One command (recommended)

```bash
cd cursor-deepseek-proxy
bash redeploy.sh
```

Stops old containers → rebuilds proxy + url-sync → waits for new tunnel → **writes Cursor config (pro + flash)** → launches Cursor.

> If prompted that Cursor is running: **Cmd+Q** quit fully, then run `bash redeploy.sh` again.

---

## By symptom

| Symptom | Cause | Fix |
|---------|-------|-----|
| **Cloudflare 1033** / Tunnel error | Expired tunnel URL | `bash redeploy.sh` |
| **Network Error** | Stale Base URL in Cursor | `bash redeploy.sh` or `python3 src/sync_cursor.py --launch` |
| **No deepseek-v4-flash** | Model catalog not updated | Cmd+Q → `python3 src/apply_config.py` or `bash redeploy.sh` |
| **reasoning_content error** | Hitting official API, not proxy | `bash redeploy.sh` |
| **API 401** | Invalid key / no balance | Update `.env` → `bash redeploy.sh` |
| **Docker errors** | Docker Desktop not running | Start Docker → `bash redeploy.sh` |
| **Proxy down** | Containers stopped | `bash docker/bin/down.sh` → `bash redeploy.sh` |

---

## Step-by-step (if redeploy fails)

```bash
# 1. Cmd+Q Cursor

bash docker/bin/down.sh
docker info >/dev/null || open -a Docker

bash deploy.sh
python3 src/apply_config.py   # if Flash still missing

# Open Cursor → Agent → pick pro or flash
```

---

## URL sync only (containers already running)

```bash
python3 src/sync_cursor.py --wait --launch
```

---

## Switch default model

```bash
bash switch-model.sh deepseek-v4-flash   # Cmd+Q first
```

---

## Full reset (rare)

```bash
bash docker/bin/down.sh
rm -f docker/data/*.sqlite3 docker/data/proxy.log docker/data/public-url.txt
bash redeploy.sh
```

---

## Verify

```bash
bash verify.sh
curl -s "${CURSOR_BASE_URL%/}/models" -H "Authorization: Bearer $DEEPSEEK_API_KEY"
```

Both `deepseek-v4-pro` and `deepseek-v4-flash` should appear.

Back to [Operations](OPERATIONS.md) · [Home](../../README.en.md)
