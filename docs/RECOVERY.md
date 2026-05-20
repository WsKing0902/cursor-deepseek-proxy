# 失效与重启指南

> **Languages / 语言:** [中文](RECOVERY.md) · [English](en/RECOVERY.md)

隧道 URL 变化、Cursor 连不上、模型列表缺少 Flash 等问题，按下面顺序处理即可。

---

## 一条命令优先（推荐）

```bash
cd cursor-deepseek-proxy   # 你的项目目录
bash sync-now.sh          # 1033 / URL 过期：立即同步
# 或完整重建：
bash redeploy.sh
```

会自动：停止旧容器 → 重建 proxy + url-sync → 等待新隧道 → **写入 Cursor（含 pro + flash）** → 打开 Cursor。

> **重启电脑后**：Docker 里的 `url-sync` **不能**写 `.env`（只读挂载），必须由 **macOS 宿主机桥接** 更新。若日志出现 `Read-only file system: '/project/.env'`，请执行：
>
> ```bash
> bash ensure-sync.sh          # 启动宿主机桥接
> bash install-host-sync.sh    # 可选：开机自动启动桥接
> bash sync-now.sh             # 立即同步 URL 到 Cursor
> ```

> 若提示 Cursor 仍在运行：先 **Cmd+Q** 完全退出，再执行一次。

---

## 按现象处理

| 现象 | 原因 | 处理 |
|------|------|------|
| **Cloudflare 1033** / Tunnel error | 隧道 URL 已过期 | `bash redeploy.sh` |
| **Network Error** / 连不上模型 | Cursor Base URL 仍是旧地址 | `bash redeploy.sh` 或 `python3 src/sync_cursor.py --launch` |
| **看不到 deepseek-v4-flash** | Cursor 模型表未更新 | Cmd+Q → `python3 src/apply_config.py` 或 `bash redeploy.sh` |
| **reasoning_content 报错** | 直连了官方 API，未走代理 | `bash redeploy.sh`，确认 Base URL 为 `*.trycloudflare.com` |
| **API 401** | Key 无效或余额不足 | 更新 `.env` 后 `bash redeploy.sh` |
| **Docker 报错** | Docker Desktop 未启动 | 打开 Docker → `bash redeploy.sh` |
| **代理无响应** | 容器挂了 | `bash docker/bin/down.sh` → `bash redeploy.sh` |

---

## 分步重启（redeploy 失败时）

```bash
# 1. 完全退出 Cursor（Cmd+Q）

# 2. 停止服务
bash docker/bin/down.sh

# 3. 确认 Docker 在运行
docker info >/dev/null || open -a Docker

# 4. 重新部署
bash deploy.sh
# 或仅启动容器 + 同步：
# bash docker/bin/up.sh

# 5. 若仍未看到 Flash，单独写入 Cursor 配置
python3 src/apply_config.py

# 6. 打开 Cursor → Agent → 选择 deepseek-v4-pro 或 deepseek-v4-flash
```

---

## 仅同步 URL（容器已在跑）

```bash
python3 src/sync_cursor.py --wait --launch
```

---

## 切换默认模型

```bash
# 先 Cmd+Q 退出 Cursor
bash switch-model.sh deepseek-v4-flash
```

---

## 模型名变回小写 deepseek

**原因：** Cursor 启动时会请求 `/v1/models` 并刷新列表，可能把小写 id 写回界面。

**处理：**

1. **Cmd+Q** 退出 Cursor  
2. `bash fix-labels.sh` 或 `python3 src/apply_config.py --labels-only`  
3. 重新打开 Cursor  

重建容器后网关会自动返回 **DeepSeek V4 Pro / Flash** 显示名：`bash redeploy.sh`

---

## 完全清理后重来（少见）

```bash
bash docker/bin/down.sh
rm -f docker/data/*.sqlite3 docker/data/proxy.log docker/data/public-url.txt
bash redeploy.sh
```

---

## 验证是否正常

```bash
bash verify.sh
```

期望：官方 API 200、本地 `:9000` 可访问、隧道 200、Cursor 配置与 `.env` 一致。

手动确认模型列表（代理应返回 pro + flash）：

```bash
source .env
curl -s "${CURSOR_BASE_URL%/}/models" -H "Authorization: Bearer $DEEPSEEK_API_KEY" | python3 -m json.tool
```

---

返回 [运维手册](OPERATIONS.md) · [项目主页](../README.md)
