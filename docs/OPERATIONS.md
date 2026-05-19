# 运维与操作手册

日常部署、代理放行、故障排查的实操说明。

---

## 一、标准工作流（开箱即用）

```bash
# 1. 克隆并配置
cp config/env.example .env    # 或 cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 2. 一键部署（Docker + 同步 Cursor + 打开 Cursor）
bash deploy.sh

# 3. 在 Cursor 中选择 deepseek-v4-pro，Agent 模式
```

等价命令：`bash scripts/deploy.sh` → `docker/bin/up.sh` → `src/sync_cursor.py --wait --launch`。

---

## 二、常用命令

| 命令 | 作用 |
|------|------|
| `bash deploy.sh` | 一键部署（推荐） |
| `bash redeploy.sh` | **重新部署**（重建 + url-sync 监视 + 同步 Cursor） |
| `bash setup.sh` | 完整安装（校验 Key、无 Docker 时本机模式） |
| `bash verify.sh` | 链路诊断（官方 API / 本地代理 / 隧道 / Cursor DB） |
| `bash docker/bin/up.sh` | 启动容器并同步 Cursor |
| `bash docker/bin/restart.sh` | 重启容器（隧道 URL 会变，自动同步） |
| `bash docker/bin/down.sh` | 停止容器 |
| `bash docker/bin/logs.sh` | 查看容器日志 |
| `python3 src/sync_cursor.py --launch` | 仅同步 URL 并打开 Cursor |
| `python3 src/sync_cursor.py --check-only` | 检查 .env 与 Cursor 是否一致 |
| `python3 src/apply_config.py` | 仅写入 Cursor（需先 Cmd+Q） |

---

## 三、代理 / 防火墙放行（重要）

### 3.1 必须能直连的域名

以下服务 **不应走 Clash/V2Ray 等 HTTP 代理**，否则隧道失败或 API 超时：

| 域名 / 模式 | 用途 | 建议规则 |
|-------------|------|----------|
| `*.trycloudflare.com` | Cursor → 本机隧道 | `DIRECT` |
| `*.cloudflare.com` | cloudflared 控制面 | `DIRECT` |
| `*.argotunnel.com` | Cloudflare Tunnel | `DIRECT` |
| `api.deepseek.com` | 代理 → DeepSeek | 直连或稳定代理（按你网络） |
| `127.0.0.1:9000` | 本机代理 | 不走代理 |

### 3.2 Clash Verge 示例（prepend 规则）

在配置增强 → 规则 → **prepend** 添加：

```yaml
- DOMAIN-SUFFIX,trycloudflare.com,DIRECT
- DOMAIN-SUFFIX,cloudflare.com,DIRECT
- DOMAIN-SUFFIX,cloudflare.net,DIRECT
- DOMAIN-SUFFIX,argotunnel.com,DIRECT
- DOMAIN-SUFFIX,cfargotunnel.com,DIRECT
- DOMAIN-KEYWORD,cloudflare,DIRECT
```

保存后 **重新加载配置**。若 cloudflared 日志出现 `198.18.x.x` 且 QUIC 超时，多半是 fake-ip / 代理劫持，务必直连。

### 3.3 macOS 防火墙

- 允许 **Docker Desktop**、**cloudflared**（容器内）出站
- 无需对公网入站开端口（Quick Tunnel 为出站连接）

### 3.4 终端临时绕过代理

```bash
export NO_PROXY="127.0.0.1,localhost,*.trycloudflare.com,*.cloudflare.com,api.deepseek.com"
export no_proxy="$NO_PROXY"
```

---

## 四、配置说明

### 4.1 `.env`（项目根目录）

| 变量 | 必填 | 说明 |
|------|------|------|
| `DEEPSEEK_API_KEY` | ✅ | DeepSeek API Key |
| `DEEPSEEK_BASE_URL` | | 默认 `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | | 默认 `deepseek-v4-pro` |
| `CURSOR_BASE_URL` | | 由部署脚本自动写入隧道地址 |

### 4.2 代理思考模式 `config/proxy-config.yaml`

```yaml
reasoning_effort: high   # 已改为 high（非 max）
```

修改后需 **重建容器**：

```bash
bash docker/bin/redeploy.sh
```

本机 Python 模式会复制到 `~/.deepseek-cursor-proxy/config.yaml`。

---

## 五、部署后验证

```bash
bash verify.sh
```

期望：

1. 官方 API `200`
2. 本地 `:9000` 可访问
3. 隧道 URL `200`
4. Cursor `openAIBaseUrl` 与 `.env` 中 `CURSOR_BASE_URL` **一致**

手动测试 chat：

```bash
source .env
curl -s "${CURSOR_BASE_URL%/}/chat/completions" \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-v4-pro","messages":[{"role":"user","content":"hi"}],"max_tokens":20}'
```

---

## 六、故障排查

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| `Network Error` / 连不上模型 | Cursor Base URL 仍是旧隧道 | Cmd+Q → `python3 src/sync_cursor.py --launch` |
| 隧道 HTTP 530 | cloudflared 未连上 / Clash 劫持 | Clash 加 DIRECT 规则；`docker/bin/restart.sh` |
| `reasoning_content` 报错 | 未走代理或直连官方 API | 确认 Base URL 为隧道地址，非 api.deepseek.com |
| Agent 很慢 | thinking max | 已默认 `high`；确认 `config/proxy-config.yaml` 已挂载 |
| Docker 构建失败 | 镜像拉取慢 | 配置 `docker/.env.docker` 的 `PYTHON_IMAGE` |
| Cursor 配置写不进去 | Cursor 未退出 | Cmd+Q 后再 `python3 src/apply_config.py` |
| API 401 | Key 无效或余额不足 | 检查 platform.deepseek.com |

查看代理日志：

```bash
bash docker/bin/logs.sh
# 或
tail -f docker/data/proxy.log docker/data/cloudflared.log
```

---

## 七、隧道 URL 自动同步（已内置）

`docker-compose` 包含 **url-sync** 服务，每 5 秒检查 `docker/data/public-url.txt`：

- 与 `.env` / Cursor 不一致 → 更新 `.env` 并触发宿主机同步
- macOS 宿主机桥接进程会退出 Cursor、写入数据库

日常重新部署：

```bash
bash redeploy.sh
```

手动同步：

```bash
python3 src/sync_cursor.py --wait --launch
```

查看监视日志：

```bash
tail -f docker/data/url-watcher-host.log
docker logs -f cursor-deepseek-url-sync
```

---

## 八、模式切换（高级）

| 场景 | 命令 |
|------|------|
| 仅本地代理（无 cloudflared） | `docker compose -f docker/docker-compose.local.yml up -d` |
| 切回隧道 URL | `bash docker/bin/switch-to-tunnel.sh` |
| 尝试本地直连 Cursor | `python3 docker/tools/use-local-only.py`（多数情况 Cursor 仍拒绝 127.0.0.1） |
| 连接修复 | `python3 docker/tools/fix-connect.py auto` |

---

## 九、停止与清理

```bash
bash docker/bin/down.sh
pkill -f cloudflared 2>/dev/null || true
```

删除数据卷缓存（reasoning SQLite）：

```bash
rm -f docker/data/*.sqlite3 docker/data/proxy.log
```

---

## 十、相关文档

- [QUICK_START.md](./QUICK_START.md) — 从零安装
- [ARCHITECTURE.md](./ARCHITECTURE.md) — 原理与自建穿透
- [SECURITY.md](./SECURITY.md) — 风险与加固
