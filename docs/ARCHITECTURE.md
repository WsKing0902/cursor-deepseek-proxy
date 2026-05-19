# 架构与原理

> 快速上手请看 [QUICK_START.md](./QUICK_START.md)。运维与代理放行见 [OPERATIONS.md](./OPERATIONS.md)。安全风险见 [SECURITY.md](./SECURITY.md)。

---

## 一、要解决的问题

在 Cursor BYOK 直连 DeepSeek 时：

- **Chat 单轮**通常正常
- **Agent 多轮**会报错：`The reasoning_content in the thinking mode must be passed back to the API.`

此外 Cursor **禁止** Base URL 指向 `127.0.0.1` / 局域网（SSRF 防护），本地代理必须有 **公网 HTTPS** 入口。

---

## 二、DeepSeek Thinking 机制

DeepSeek V4 在思考模式下返回 `reasoning_content`（内部推理链）。下一轮请求必须把上一轮的 `reasoning_content` **原样回传**，否则 API 返回 400。

Cursor 的 OpenAI 兼容层不保存、不回传该字段 → Agent 多轮必然失败。

```
Cursor 第1轮 ← content + reasoning_content（只留了 content）
Cursor 第2轮 → 请求里没有 reasoning_content → DeepSeek 400
```

---

## 三、本项目的架构

```
┌──────────┐   HTTPS 公网    ┌──────────────────────┐   HTTPS    ┌──────────────┐
│  Cursor  │───────────────▶│ deepseek-cursor-proxy │──────────▶│ DeepSeek API │
│  (BYOK)  │◀───────────────│      :9000            │◀──────────│              │
└──────────┘                └──────────┬───────────┘            └──────────────┘
                                       │
                              ┌────────┴────────┐
                              │  cloudflared     │  （默认：Quick Tunnel）
                              │  trycloudflare   │
                              └──────────────────┘
```

### 代理职责

| 能力 | 说明 |
|------|------|
| 缓存 reasoning | 从响应中提取 `reasoning_content` 写入 SQLite，再发给 Cursor |
| 恢复 reasoning | 下一轮请求前注入缓存，满足 DeepSeek API 要求 |
| 协议兼容 | tools / function_call、流式、thinking 展示等 |

### 思考强度配置

代理配置见 `config/proxy-config.yaml`，默认：

```yaml
thinking: enabled
reasoning_effort: high   # 非 max，平衡质量与速度/成本
```

Docker 通过卷挂载到容器内 `/data/config.yaml`，由 `entrypoint.sh` 以 `--config` 传入。

### Cursor 配置写入

`src/apply_config.py` 在 Cursor **完全退出**后写入 SQLite：

`~/Library/Application Support/Cursor/User/globalStorage/state.vscdb`

主要字段：`openAIBaseUrl`、`useOpenAIKey`、`composerModel`、`cursorAuth/openAIKey`。

`src/sync_cursor.py` 从 `docker/data/public-url.txt` 读取隧道 URL，更新 `.env` 并调用 `apply_config.py`，可选 `--launch` 打开 Cursor。

---

## 四、默认方案：Cloudflare Quick Tunnel

`cloudflared tunnel --url http://127.0.0.1:9000` 会分配随机 `*.trycloudflare.com` 域名。

**优点**：免注册、免公网 IP、与 Cursor SSRF 规则兼容。  
**缺点**：每次重启 URL 变化；流量经 Cloudflare；见 [SECURITY.md](./SECURITY.md)。

---

## 五、反代 / 公网隧道的风险（必读）

使用「本地服务 + 公网反代」让 Cursor 访问，本质是 **把本机 HTTP 服务暴露到互联网**。即便有 API Key，仍存在结构性风险：

| 风险 | 说明 |
|------|------|
| **未授权访问** | Quick Tunnel 无访问控制，知道 URL 的人可尝试调用（依赖 Bearer Key，但 Key 泄露即全权限） |
| **流量经过第三方** | Cloudflare 边缘可见 TLS 内元数据；Quick Tunnel 不适合高敏代码/密钥场景 |
| **URL 泄露** | 日志、截图、Git 误提交 `.env` 中的 `CURSOR_BASE_URL` 会暴露入口 |
| **无固定域名** | 重启换 URL，易与 Cursor 配置不同步（本项目用 `sync_cursor.py` 缓解） |
| **代理即信任根** | 本机代理可记录请求体；恶意或被入侵的代理危害极大 |

**结论**：适合个人开发、低敏项目；**不适合**生产密钥、客户数据、合规环境。

更稳妥的方向是 **自建受控内网穿透**（见下节），而不是长期依赖随机 Quick Tunnel。

---

## 六、更安全的替代：自建内网穿透

目标：仍给 Cursor 一个 **HTTPS 公网 URL**，但 **访问可控、域名固定、尽量不经过不可信第三方**。

### 6.1 Cloudflare Named Tunnel（推荐进阶）

- 注册 Cloudflare，创建 **Named Tunnel** + 自有子域（如 `ds-proxy.yourdomain.com`）
- 在隧道侧配置 **Cloudflare Access**（邮箱/OTP）或 IP 白名单
- 本地 `cloudflared` 只出站连接，无需开端口

比 Quick Tunnel 更安全：固定域名、可鉴权、可审计。

### 6.2 自建 FRP / 反向代理（VPS）

```
Cursor → https://ds.example.com (Nginx+TLS on VPS) → frps → frpc → 本机 :9000
```

- VPS 上 Nginx 终止 TLS，仅转发到 frp
- **必须**加：防火墙白名单、Basic Auth、mTLS 或 VPN 后再暴露
- 域名与证书自己掌控，不依赖 trycloudflare

### 6.3 Tailscale / WireGuard（零信任）

- 本机与运行 Cursor 的设备在同一 tailnet
- 若 Cursor 仍拒绝私网 IP，可在 tailnet 内用 **小型 HTTPS 网关**（Caddy + 内网证书）暴露代理
- 无公网开放端口，攻击面最小

### 6.4 与本项目集成

1. 自行取得固定 HTTPS URL（指向本机 `9000` 的代理）
2. 写入 `.env`：`CURSOR_BASE_URL=https://你的域名/v1`
3. **关闭** 容器内 cloudflared：使用 `docker-compose.local.yml` 仅起代理，或改 `entrypoint` 不启动 tunnel
4. `python3 src/sync_cursor.py --launch` 或 `src/apply_config.py` 写入 Cursor

---

## 七、项目目录结构

```
cursor-deepseek-v4/
├── deploy.sh / setup.sh / verify.sh   # 根目录便捷入口
├── scripts/                           # Shell 部署与诊断
├── src/                               # Python：Cursor 配置与 URL 同步
│   ├── apply_config.py
│   └── sync_cursor.py
├── config/                            # 配置模板与代理 config
│   ├── env.example
│   └── proxy-config.yaml              # reasoning_effort: high
├── docker/
│   ├── Dockerfile / docker-compose*.yml
│   ├── entrypoint*.sh
│   ├── bin/                           # up / down / restart …
│   └── tools/                         # 隧道监视、修复连接等
└── docs/
    ├── QUICK_START.md
    ├── ARCHITECTURE.md                # 本文
    ├── OPERATIONS.md
    └── SECURITY.md
```

---

## 八、总结

| 问题 | 原因 | 本项目做法 |
|------|------|------------|
| Agent 报错 | Cursor 不回传 reasoning | 本地代理缓存/恢复 |
| 不能连 localhost | Cursor SSRF | 公网 HTTPS 隧道 |
| URL 常变 | Quick Tunnel 特性 | 部署后自动 sync + 可 launch Cursor |
| 思考过强/慢 | max effort | 配置为 `reasoning_effort: high` |

长期建议：从 Quick Tunnel 迁移到 **Named Tunnel + Access** 或 **自建 FRP/VPN**，见 [SECURITY.md](./SECURITY.md)。
