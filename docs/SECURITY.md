# 安全说明

> **Languages / 语言:** [中文](SECURITY.md) · [English](en/SECURITY.md)

本文说明使用「本地代理 + 公网反代」时的风险边界与加固建议。架构背景见 [ARCHITECTURE.md](./ARCHITECTURE.md)。

---

## 一、威胁模型（你在暴露什么）

部署完成后，互联网上存在一个 URL（如 `https://xxx.trycloudflare.com/v1`），行为类似 **OpenAI 兼容 API**：

- 持有 **DeepSeek API Key** 的客户端可调用 chat/completions
- 本机 **deepseek-cursor-proxy** 可看到请求与响应（含代码、对话）
- **cloudflared Quick Tunnel** 无内置登录，URL 即入口

因此风险不仅是「Key 泄露」，还包括 **入口泄露、中间人、本机被入侵、代理被篡改**。

---

## 二、Cloudflare Quick Tunnel 特有风险

| 风险 | 严重程度 | 说明 |
|------|----------|------|
| 随机 URL 无鉴权 | 高 | 任何人猜到/拿到 URL 可尝试请求（仍需要有效 Bearer Key） |
| URL 随重启变化 | 中 | 旧 URL 失效但可能已泄露；Cursor 配置不同步导致误连 |
| 流量经 Cloudflare | 中 | 元数据、DDoS 防护可见；需信任 Cloudflare 策略 |
| 与 Clash 等代理冲突 | 中 | cloudflared QUIC 被错误走代理会导致隧道失败（见 OPERATIONS.md） |
| 日志泄露 | 中 | `docker/data/cloudflared.log`、`.env` 含完整 URL |

**不适用场景**：公司代码库、客户数据、受监管行业、共享机器上的多用户环境。

---

## 三、API Key 与 .env

- `.env` 含 `DEEPSEEK_API_KEY`，**切勿提交 Git**（已在 `.gitignore`）
- 建议 `chmod 600 .env`
- Cursor 数据库中也写入 Key（`cursorAuth/openAIKey`），备份 `state.vscdb` 时注意
- Key 在代理与 DeepSeek 之间转发，本机代理进程有权使用你的 Key 调官方 API

---

## 四、本机代理的信任

`deepseek-cursor-proxy` 来自第三方开源项目。应：

- 固定版本或校验镜像构建来源（`docker/Dockerfile` 从 GitHub 安装）
- 不在不可信机器上部署
- 高敏环境考虑自行审计源码或在内网隔离环境运行

---

## 五、加固清单

### 5.1 最低限度（个人开发）

- [ ] 不将 `CURSOR_BASE_URL`、`.env` 提交到仓库或截图外传
- [ ] Clash/Surge 对 `*.trycloudflare.com`、`*.cloudflare.com` **直连**（见 OPERATIONS.md）
- [ ] 容器重启后运行 `bash scripts/deploy.sh` 或 `python3 src/sync_cursor.py --launch` 同步 URL
- [ ] 不用时 `bash docker/bin/down.sh` 停止暴露

### 5.2 推荐（较长期使用）

- [ ] 改用 **Cloudflare Named Tunnel** + 自有域名 + **Cloudflare Access**
- [ ] 在 DeepSeek 控制台为 Key 设用量上限、定期轮换
- [ ] 专用 API Key 仅用于 Cursor，与其它项目隔离

### 5.3 高安全（接近生产）

- [ ] **不要**使用 Quick Tunnel
- [ ] VPS + FRP/Nginx + TLS + IP 白名单 / mTLS
- [ ] 或 **Tailscale/WireGuard**，仅 tailnet 内访问 HTTPS 网关
- [ ] 代理仅监听 `127.0.0.1`，由受控网关对外
- [ ] 审计日志、密钥进 Vault/1Password，不进明文 `.env`

---

## 六、自建方案对比

| 方案 | 暴露面 | 固定域名 | 访问控制 | 复杂度 |
|------|--------|----------|----------|--------|
| Quick Tunnel（默认） | 公网随机 URL | ❌ | ❌ | 低 |
| Named Tunnel + Access | 公网固定子域 | ✅ | ✅ | 中 |
| FRP + VPS + Nginx | 公网固定 | ✅ | 可配 | 中高 |
| Tailscale / WireGuard | 无公网端口 | 内网 | ✅ | 中 |

详细集成步骤见 [ARCHITECTURE.md](./ARCHITECTURE.md) 第六节。

---

## 七、 incident 响应

若怀疑 URL 或 Key 泄露：

1. 立即 `bash docker/bin/down.sh` 停止隧道
2. 在 [platform.deepseek.com](https://platform.deepseek.com) **吊销并重建** API Key
3. 更新 `.env` 后 `python3 src/apply_config.py`（先 Cmd+Q 退出 Cursor）
4. 重建容器获取新隧道 URL：`bash scripts/deploy.sh`

---

## 八、免责声明

本项目为个人/开发便利工具，**不提供安全保证**。公网暴露本地服务的后果由使用者自行承担。生产或敏感数据场景请采用自建零信任方案，而非默认 Quick Tunnel。
