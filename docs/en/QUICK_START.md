# Quick start: DeepSeek V4 in Cursor

> **Languages / 语言:** [中文](../QUICK_START.md) · [English](QUICK_START.md)

Step-by-step setup from zero—about **10 minutes**.

---

## 1. Prerequisites

| Requirement | Notes |
|-------------|-------|
| OS | macOS or Linux (Windows: WSL2) |
| Disk | ~500 MB (Docker + deps) |
| Network | Reach [api.deepseek.com](https://api.deepseek.com) and GitHub |

---

## 2. Get a DeepSeek API key

1. Open [platform.deepseek.com](https://platform.deepseek.com)
2. Register / sign in
3. **API Keys** → **Create API Key**
4. Copy `sk-...` (shown once)

### Top up

API requires balance (often from ¥1). Pricing is low for typical daily use.

---

## 3. Clone the project

```bash
git clone https://github.com/WsKing0902/cursor-deepseek-proxy.git
cd cursor-deepseek-proxy
```

---

## 4. Install Docker (recommended)

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
2. Start Docker; verify: `docker --version`

Without Docker, `deploy.sh` can fall back to local Python mode.

---

## 5. Configure

```bash
cp config/env.example .env
nano .env   # or any editor
```

Set:

```env
DEEPSEEK_API_KEY=sk-your-real-key
```

Leave `CURSOR_BASE_URL` empty—scripts fill it automatically.

### 5.1 Thinking effort (optional)

Default **`reasoning_effort: high`** (not `max`—`max` is slower in Agent multi-turn).

Edit `config/proxy-config.yaml`, then `bash redeploy.sh`. See [README · Adjust thinking mode](../../README.en.md#adjust-thinking-mode-reasoning_effort).

---

## 6. Deploy

```bash
bash deploy.sh
```

The script validates the key, builds/starts containers, waits for the Cloudflare tunnel, writes Cursor config, and may launch Cursor.

If prompted that Cursor is running, quit with **Cmd+Q** and retry.

---

## 7. Use Cursor

1. Open Cursor (or let `deploy.sh` open it)
2. Select model **`deepseek-v4-pro`**
3. Switch to **Agent** mode (not Chat only)
4. Test: `Hello, what is 1+1?`

---

## 8. Verify

```bash
bash verify.sh
```

Checks: `.env`, official API, local `:9000`, tunnel, Docker, Cursor DB consistency.

---

## 9. Daily use

### Redeploy (recommended)

After reboot or **Tunnel error / Network Error**:

```bash
bash redeploy.sh
```

### Auto URL sync

`url-sync` watches `docker/data/public-url.txt`. Manual sync:

```bash
python3 src/sync_cursor.py --launch
```

### After each boot

1. Start Docker Desktop
2. `bash redeploy.sh` (or `bash docker/bin/up.sh` if containers still exist)

### Stop / logs

```bash
bash docker/bin/down.sh
bash docker/bin/logs.sh
```

---

## 10. Troubleshooting

### No Docker

Start Docker Desktop, then `bash deploy.sh` again.

### Cloudflare 1033 / Network Error

Tunnel URL changed. Run:

```bash
bash redeploy.sh
```

### `reasoning_content must be passed back`

Cursor is hitting `api.deepseek.com` directly. Base URL must be the tunnel—`bash redeploy.sh`.

### API 401

Invalid key or no balance—fix at platform.deepseek.com, update `.env`, redeploy.

### Model `deepseek-v4-pro` missing

1. Cmd+Q Cursor
2. `python3 src/apply_config.py`
3. Reopen Cursor

### SSRF / localhost errors

Do not set Base URL to `http://127.0.0.1:9000` in Cursor Settings. Use tunnel URL from deploy/sync scripts.

### Clash breaks tunnel

Add DIRECT rules for Cloudflare domains—see [OPERATIONS.md §3](./OPERATIONS.md#3-proxy--firewall-rules-important).

---

More: [Operations](./OPERATIONS.md) · [Architecture](./ARCHITECTURE.md) · [Security](./SECURITY.md)
