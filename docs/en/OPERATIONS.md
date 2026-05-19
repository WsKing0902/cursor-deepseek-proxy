# Operations manual

> **Languages / 语言:** [中文](../OPERATIONS.md) · [English](OPERATIONS.md)

Day-to-day deploy, proxy rules, and troubleshooting.

---

## 1. Standard workflow

```bash
cp config/env.example .env
# Edit .env: DEEPSEEK_API_KEY

bash deploy.sh
# In Cursor: deepseek-v4-pro + Agent mode
```

Equivalent: `bash scripts/deploy.sh` → `docker/bin/up.sh` → `src/sync_cursor.py --wait --launch`.

---

## 2. Common commands

| Command | Purpose |
|---------|---------|
| `bash deploy.sh` | One-shot deploy |
| `bash redeploy.sh` | **Redeploy** (rebuild + url-sync + sync Cursor) |
| `bash setup.sh` | Full install (local Python if no Docker) |
| `bash verify.sh` | Health check |
| `bash docker/bin/up.sh` | Start containers + sync |
| `bash docker/bin/restart.sh` | Restart (URL may change—auto sync) |
| `bash docker/bin/down.sh` | Stop |
| `bash docker/bin/logs.sh` | Logs |
| `python3 src/sync_cursor.py --launch` | Sync URL + open Cursor |
| `python3 src/sync_cursor.py --check-only` | Compare .env vs Cursor |
| `python3 src/apply_config.py` | Write Cursor DB only (Cmd+Q first) |

---

## 3. Proxy / firewall rules (important)

These must **not** go through Clash/V2Ray HTTP proxy, or the tunnel/API will fail:

| Domain / pattern | Purpose | Rule |
|------------------|---------|------|
| `*.trycloudflare.com` | Cursor → tunnel | `DIRECT` |
| `*.cloudflare.com` | cloudflared control plane | `DIRECT` |
| `*.argotunnel.com` | Cloudflare Tunnel | `DIRECT` |
| `api.deepseek.com` | Proxy → DeepSeek | DIRECT or stable route |
| `127.0.0.1:9000` | Local proxy | No proxy |

### Clash Verge example (prepend)

```yaml
- DOMAIN-SUFFIX,trycloudflare.com,DIRECT
- DOMAIN-SUFFIX,cloudflare.com,DIRECT
- DOMAIN-SUFFIX,cloudflare.net,DIRECT
- DOMAIN-SUFFIX,argotunnel.com,DIRECT
- DOMAIN-SUFFIX,cfargotunnel.com,DIRECT
- DOMAIN-KEYWORD,cloudflare,DIRECT
```

Reload config. If logs show `198.18.x.x` and QUIC timeout, fix fake-ip / proxy hijacking.

### Terminal bypass

```bash
export NO_PROXY="127.0.0.1,localhost,*.trycloudflare.com,*.cloudflare.com,api.deepseek.com"
export no_proxy="$NO_PROXY"
```

---

## 4. Configuration

### 4.1 `.env`

| Variable | Required | Description |
|----------|----------|-------------|
| `DEEPSEEK_API_KEY` | ✅ | DeepSeek API key |
| `DEEPSEEK_BASE_URL` | | Default `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | | Default `deepseek-v4-pro` |
| `CURSOR_BASE_URL` | | Auto-filled tunnel URL |

### 4.2 Thinking mode `config/proxy-config.yaml`

Field: **`reasoning_effort`**

| Value | Description |
|-------|-------------|
| `low` | Minimal reasoning, fastest |
| `medium` | Light reasoning |
| **`high`** | **Default**—balanced for daily Agent |
| `max` | Strongest; large `reasoning_content`, slow, costly |

**Why `high` not `max`:** Agent multi-turn accumulates reasoning text; proxy must cache/replay it—`max` feels sluggish for most coding.

**Change steps:**

1. Edit `config/proxy-config.yaml`
2. `bash redeploy.sh`

Local Python mode copies to `~/.deepseek-cursor-proxy/config.yaml`—restart proxy after edits.

Optional: delete `docker/data/*.sqlite3` after lowering effort—see [§9](#9-stop--cleanup).

Details: [README · Adjust thinking mode](../../README.en.md#adjust-thinking-mode-reasoning_effort).

---

## 5. Post-deploy verification

```bash
bash verify.sh
```

Expect: official API 200, local `:9000` up, tunnel 200, Cursor `openAIBaseUrl` matches `.env`.

---

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Network Error` | Stale tunnel URL in Cursor | Cmd+Q → `python3 src/sync_cursor.py --launch` |
| Tunnel HTTP 530 | cloudflared / Clash | DIRECT rules; `docker/bin/restart.sh` |
| `reasoning_content` error | Direct to official API | Base URL must be tunnel, not api.deepseek.com |
| Agent slow | `max` effort | Default is `high`; check mounted config |
| Config not written | Cursor running | Cmd+Q → `apply_config.py` |
| API 401 | Bad key / no balance | platform.deepseek.com |

```bash
bash docker/bin/logs.sh
tail -f docker/data/proxy.log docker/data/cloudflared.log
```

---

## 7. Auto URL sync (built-in)

`url-sync` polls `docker/data/public-url.txt` every 5s; updates `.env` and triggers host bridge on macOS.

Daily: `bash redeploy.sh`. Manual: `python3 src/sync_cursor.py --wait --launch`.

---

## 8. Advanced mode switching

| Scenario | Command |
|----------|---------|
| Local proxy only (no cloudflared) | `docker compose -f docker/docker-compose.local.yml up -d` |
| Back to tunnel | `bash docker/bin/switch-to-tunnel.sh` |
| Try localhost in Cursor | `python3 docker/tools/use-local-only.py` (usually blocked) |
| Connection fix | `python3 docker/tools/fix-connect.py auto` |

---

## 9. Stop & cleanup

```bash
bash docker/bin/down.sh
pkill -f cloudflared 2>/dev/null || true
rm -f docker/data/*.sqlite3 docker/data/proxy.log
```

---

## 10. Related docs

- [QUICK_START.md](./QUICK_START.md)
- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [SECURITY.md](./SECURITY.md)
