# 文档索引

> **Languages / 语言:** [中文](README.md) · [English](en/README.md)

欢迎查阅 **cursor-deepseek-proxy** 文档。

## 中文文档

| 顺序 | 文档 | 适合谁 |
|------|------|--------|
| 1 | [QUICK_START.md](./QUICK_START.md) | 第一次部署，跟着做即可 |
| 2 | [OPERATIONS.md](./OPERATIONS.md) | 日常运维、Clash 放行、命令速查 |
| 3 | [ARCHITECTURE.md](./ARCHITECTURE.md) | 理解原理、反代风险、自建穿透 |
| 4 | [SECURITY.md](./SECURITY.md) | 安全边界与加固清单 |
| — | [HOW_IT_WORKS.md](./HOW_IT_WORKS.md) | 已合并至 ARCHITECTURE，保留跳转 |
| — | [PUBLISHING.md](./PUBLISHING.md) | 推送到 GitHub 前的检查清单 |

## English documentation

| Order | Document | Audience |
|-------|----------|----------|
| 1 | [en/QUICK_START.md](./en/QUICK_START.md) | First-time setup |
| 2 | [en/OPERATIONS.md](./en/OPERATIONS.md) | Daily ops & troubleshooting |
| 3 | [en/ARCHITECTURE.md](./en/ARCHITECTURE.md) | Design & self-hosted tunnels |
| 4 | [en/SECURITY.md](./en/SECURITY.md) | Security & hardening |

## 方案速览

```
填写 .env → bash deploy.sh
    → Docker: proxy + url-sync
    → 隧道 URL 写入 public-url.txt
    → 自动同步 Cursor（必要时退出并重开）
    → 选择 deepseek-v4-pro + Agent 模式
```

日常维护：**`bash redeploy.sh`**（重建 + 同步 + 打开 Cursor）。

返回 [项目主页 (中文)](../README.md) · [Project home (EN)](../README.en.md)
