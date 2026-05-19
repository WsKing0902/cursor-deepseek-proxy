# Security

> **Languages / 语言:** [中文](../SECURITY.md) · [English](SECURITY.md)

Risks of **local proxy + public reverse proxy**. Background: [ARCHITECTURE.md](./ARCHITECTURE.md).

---

## 1. Threat model

After deploy, the internet can reach a URL like `https://xxx.trycloudflare.com/v1`—an **OpenAI-compatible API**:

- Clients with your **DeepSeek API key** can call chat/completions
- Local **deepseek-cursor-proxy** sees requests/responses (code, chat)
- **Quick Tunnel** has no built-in auth—the URL is the entry

Risks include key leak, URL leak, MITM, compromised host, tampered proxy—not only “key stolen.”

---

## 2. Quick Tunnel specific risks

| Risk | Severity | Notes |
|------|----------|-------|
| Random URL, no auth | High | Guessed URL + valid Bearer = API use |
| URL changes on restart | Medium | Old URL may have leaked; Cursor out of sync |
| Traffic via Cloudflare | Medium | Metadata visible; trust their policy |
| Clash conflict | Medium | Wrong proxy breaks tunnel (see OPERATIONS) |
| Log leakage | Medium | `cloudflared.log`, `.env` contain full URL |

**Not for:** company repos, customer data, regulated industries, shared machines.

---

## 3. API key & `.env`

- Never commit `.env` (in `.gitignore`)
- `chmod 600 .env`
- Key also in Cursor DB (`cursorAuth/openAIKey`)—protect backups
- Proxy can forward your key to DeepSeek—trust the process

---

## 4. Trust the local proxy

`deepseek-cursor-proxy` is third-party OSS:

- Pin version / verify Docker build (`docker/Dockerfile`)
- Do not run on untrusted machines
- Audit source for high-sensitivity environments

---

## 5. Hardening checklist

### 5.1 Minimum (personal dev)

- [ ] Do not commit or share `CURSOR_BASE_URL` / `.env`
- [ ] Clash: `*.trycloudflare.com`, `*.cloudflare.com` → **DIRECT**
- [ ] After container restart: `bash deploy.sh` or `sync_cursor.py --launch`
- [ ] `bash docker/bin/down.sh` when not in use

### 5.2 Recommended (longer term)

- [ ] **Named Tunnel** + own domain + **Cloudflare Access**
- [ ] Key usage limits and rotation on DeepSeek console
- [ ] Dedicated key for Cursor only

### 5.3 High security

- [ ] No Quick Tunnel
- [ ] VPS + FRP/Nginx + TLS + IP allowlist / mTLS
- [ ] Or Tailscale/WireGuard + internal HTTPS gateway
- [ ] Proxy listens on `127.0.0.1` only
- [ ] Secrets in Vault/1Password, not plain `.env`

---

## 6. Self-hosted comparison

| Option | Exposure | Fixed domain | Access control | Complexity |
|--------|----------|--------------|----------------|------------|
| Quick Tunnel (default) | Random public URL | ❌ | ❌ | Low |
| Named Tunnel + Access | Fixed subdomain | ✅ | ✅ | Medium |
| FRP + VPS + Nginx | Fixed public | ✅ | Configurable | Medium–high |
| Tailscale / WireGuard | No public port | Internal | ✅ | Medium |

Integration: [ARCHITECTURE.md §6](./ARCHITECTURE.md#6-safer-alternatives-self-hosted-tunnels).

---

## 7. Incident response

If URL or key may be leaked:

1. `bash docker/bin/down.sh`
2. Revoke and recreate key at [platform.deepseek.com](https://platform.deepseek.com)
3. Update `.env`, Cmd+Q Cursor, `python3 src/apply_config.py`
4. `bash deploy.sh` for new tunnel URL

---

## 8. Disclaimer

This is a **convenience tool** for development—**no security warranty**. You are responsible for exposing local services to the internet. For production or sensitive data, use zero-trust self-hosted options, not default Quick Tunnel.
