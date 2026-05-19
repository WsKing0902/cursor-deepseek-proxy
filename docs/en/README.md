# Documentation (English)

> **Languages / 语言:** [中文](../README.md) · [English](README.md)

English documentation for **cursor-deepseek-proxy**. For the full Chinese set, see [docs/README.md](../README.md).

| Order | Document | Audience |
|-------|----------|----------|
| 1 | [QUICK_START.md](./QUICK_START.md) | First-time setup (~10 min) |
| 2 | [OPERATIONS.md](./OPERATIONS.md) | Daily ops, Clash rules, commands |
| 3 | [ARCHITECTURE.md](./ARCHITECTURE.md) | Design, reverse-proxy risks, self-hosted tunnels |
| 4 | [SECURITY.md](./SECURITY.md) | Threat model and hardening |

## Overview

```
Fill .env → bash deploy.sh
    → Docker: proxy + url-sync
    → Tunnel URL → public-url.txt
    → Auto-sync Cursor (quit & rewrite if needed)
    → Select deepseek-v4-pro + Agent mode
```

Daily maintenance: **`bash redeploy.sh`**.

Back to [project home (EN)](../../README.en.md) · [项目主页 (中文)](../../README.md)
