# Architecture & design

> **Languages / 语言:** [中文](../ARCHITECTURE.md) · [English](ARCHITECTURE.md)

> Quick start: [QUICK_START.md](./QUICK_START.md). Operations: [OPERATIONS.md](./OPERATIONS.md). Security: [SECURITY.md](./SECURITY.md).

---

## 1. Problem statement

With Cursor BYOK pointing at DeepSeek:

- **Chat (single turn)** usually works
- **Agent (multi-turn)** fails: `The reasoning_content in the thinking mode must be passed back to the API.`

Cursor also **blocks** Base URL to `127.0.0.1` / LAN (SSRF), so the local proxy needs a **public HTTPS** URL.

---

## 2. DeepSeek thinking mode

DeepSeek V4 returns `reasoning_content` (internal chain-of-thought). The next request must send the previous turn’s `reasoning_content` **unchanged**, or the API returns 400.

Cursor’s OpenAI-compatible layer does not store or replay that field → multi-turn Agent fails.

```
Turn 1: Cursor ← content + reasoning_content (Cursor keeps content only)
Turn 2: Cursor → request without reasoning_content → DeepSeek 400
```

---

## 3. This project’s architecture

```
┌──────────┐   HTTPS public   ┌──────────────────────┐   HTTPS    ┌──────────────┐
│  Cursor  │───────────────▶│ deepseek-cursor-proxy │──────────▶│ DeepSeek API │
│  (BYOK)  │◀───────────────│      :9000            │◀──────────│              │
└──────────┘                └──────────┬───────────┘            └──────────────┘
                                       │
                              ┌────────┴────────┐
                              │  cloudflared     │  (default: Quick Tunnel)
                              │  trycloudflare   │
                              └──────────────────┘
```

### Proxy responsibilities

| Feature | Description |
|---------|-------------|
| Cache reasoning | Extract `reasoning_content` from responses → SQLite → forward to Cursor |
| Restore reasoning | Inject cache on next request to satisfy DeepSeek API |
| Protocol | tools / function_call, streaming, thinking display |

### Thinking effort

`config/proxy-config.yaml` (mounted as `/data/config.yaml`):

```yaml
thinking: enabled
reasoning_effort: high   # not max—long chains slow Agent multi-turn; see README
```

`src/apply_config.py` writes Cursor SQLite when Cursor is **fully quit**:

`~/Library/Application Support/Cursor/User/globalStorage/state.vscdb`

`src/sync_cursor.py` reads `docker/data/public-url.txt`, updates `.env`, calls `apply_config.py`, optional `--launch`.

---

## 4. Default: Cloudflare Quick Tunnel

`cloudflared tunnel --url http://127.0.0.1:9000` → random `*.trycloudflare.com`.

**Pros:** No signup, no public IP, works with Cursor SSRF rules.  
**Cons:** URL changes on restart; traffic via Cloudflare—see [SECURITY.md](./SECURITY.md).

---

## 5. Reverse-proxy risks (read this)

Exposing local HTTP to the internet has structural risks:

| Risk | Description |
|------|-------------|
| **Unauthenticated entry** | Quick Tunnel has no login; anyone with URL can try calls (still needs Bearer key) |
| **Third-party path** | Cloudflare edge sees metadata; not for highly sensitive code |
| **URL leakage** | Logs, screenshots, committed `.env` |
| **Unstable URL** | Restart changes URL—mitigated by `sync_cursor.py` |
| **Proxy as trust root** | Local proxy can log bodies |

**Conclusion:** Personal dev / low sensitivity only—not production secrets or compliance workloads.

---

## 6. Safer alternatives: self-hosted tunnels

Goal: **HTTPS public URL** for Cursor with **fixed domain and access control**.

### 6.1 Cloudflare Named Tunnel (recommended upgrade)

- Named Tunnel + your subdomain (e.g. `ds-proxy.yourdomain.com`)
- **Cloudflare Access** (email/OTP) or IP allowlist
- `cloudflared` outbound only—no inbound port on your machine

### 6.2 FRP + VPS + Nginx

```
Cursor → https://ds.example.com (Nginx TLS on VPS) → frps → frpc → localhost:9000
```

Add firewall, Basic Auth, mTLS, or VPN.

### 6.3 Tailscale / WireGuard

Same tailnet; if Cursor still rejects private IPs, use an **HTTPS gateway** (Caddy) inside the tailnet.

### 6.4 Integrate with this repo

1. Obtain a fixed HTTPS URL to local proxy `:9000`
2. Set `.env`: `CURSOR_BASE_URL=https://your-domain/v1`
3. Disable in-container cloudflared: `docker-compose.local.yml` or custom entrypoint
4. `python3 src/sync_cursor.py --launch` or `src/apply_config.py`

---

## 7. Summary

| Issue | Cause | This project |
|-------|-------|--------------|
| Agent error | Cursor drops reasoning | Local proxy cache/replay |
| No localhost | Cursor SSRF | Public HTTPS tunnel |
| URL changes | Quick Tunnel | Auto sync + optional launch |
| Too slow | `max` effort | Default `reasoning_effort: high` |

Long term: migrate to **Named Tunnel + Access** or **FRP/VPN**—see [SECURITY.md](./SECURITY.md).
