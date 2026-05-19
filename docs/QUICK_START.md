# 从零开始：在 Cursor 中使用 DeepSeek V4

本教程假设你从零开始，一步步引导你完成所有配置。全程大约需要 **10 分钟**。

---

## 目录

1. [准备工作](#1-准备工作)
2. [获取 DeepSeek API Key](#2-获取-deepseek-api-key)
3. [下载项目](#3-下载项目)
4. [安装 Docker（推荐）](#4-安装-docker推荐)
5. [填写配置](#5-填写配置)
6. [一键部署](#6-一键部署)
7. [打开 Cursor 使用](#7-打开-cursor-使用)
8. [验证是否成功](#8-验证是否成功)
9. [日常使用](#9-日常使用)
10. [故障排查](#10-故障排查)

---

## 1. 准备工作

在开始之前，请确认你的电脑满足以下条件：

| 要求 | 说明 |
|------|------|
| 操作系统 | macOS 或 Linux（Windows 请用 WSL2） |
| 磁盘空间 | ~500 MB（Docker 镜像 + Python 依赖） |
| 网络 | 能访问 [api.deepseek.com](https://api.deepseek.com) 和 GitHub |

---

## 2. 获取 DeepSeek API Key

这是最关键的一步——你需要一个 DeepSeek 的 API Key。

### 2.1 注册并获取 Key

1. 打开浏览器，访问 **[platform.deepseek.com](https://platform.deepseek.com)**
2. 注册账号（支持手机号或邮箱）
3. 登录后，点击左侧菜单 **「API Keys」**
4. 点击 **「创建 API Key」** 按钮
5. 给 Key 起个名字（如 `cursor`），点击创建
6. **复制并保存** 生成的 Key（格式：`sk-xxxxxxxxxxxxxxxx`）

> ⚠️ **重要**：Key 只显示一次，关闭页面后就看不到了，请务必保存好！

### 2.2 充值

DeepSeek API 需要充值才能使用。不用担心，费用极低：

1. 在 platform.deepseek.com 左侧点击 **「充值」**
2. 最低充值金额通常为 ¥1
3. 支持支付宝/微信支付

> 💡 **费用参考**：DeepSeek V4 的定价约为 输入 ¥2/百万 tokens，输出 ¥8/百万 tokens。日常使用每天几毛钱就足够了。

---

## 3. 下载项目

打开终端（macOS 按 `Cmd+Space` 搜 "Terminal"），执行：

```bash
# 克隆项目
git clone https://github.com/WsKing0902/cursor-deepseek-proxy.git
cd cursor-deepseek-proxy
```

> 如果你是下载的 ZIP 包，解压后 `cd` 到解压目录即可。

---

## 4. 安装 Docker（推荐）

Docker 是最简单的部署方式。如果你不想装 Docker，可以跳到 [方式二：本机 Python 部署](#方式二本机-python-部署可选)（但推荐用 Docker）。

### 4.1 安装 Docker Desktop

1. 访问 **[docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)**
2. 下载对应你系统的版本（macOS 选 Apple Chip 或 Intel Chip）
3. 双击 `.dmg` 安装
4. 安装完成后，在「应用程序」中找到 Docker 并打开
5. 首次启动会请求权限，全部允许

### 4.2 验证安装

打开终端，输入：

```bash
docker --version
```

如果输出类似 `Docker version 27.x.x` 就表示安装成功。

---

## 5. 填写配置

在项目目录下，将示例配置文件复制一份：

```bash
cp config/env.example .env
```

然后用任意编辑器打开 `.env` 文件，填入你的 API Key：

```bash
# macOS 用 nano 编辑
nano .env
```

修改这一行：

```env
DEEPSEEK_API_KEY=sk-your-key-here
```

把 `sk-your-key-here` 替换成你在第 2 步获取的真实 Key。改完后按 `Ctrl+O` 保存，`Ctrl+X` 退出。

其他配置项不用改，`CURSOR_BASE_URL` 留空即可——脚本会自动填写。

---

## 6. 一键部署

在项目目录下，执行：

```bash
bash deploy.sh
```

脚本会自动完成以下所有步骤：

```
  ✓ API Key 已配置
  ✓ Docker 可用
  → 构建并启动容器...
  → Cloudflare 隧道就绪: https://xxx.trycloudflare.com/v1
  → 自动写入 Cursor 配置
  → 自动打开 Cursor
```

> 首次安装或需要完整校验时，可使用 `bash deploy.sh`。

如果过程中弹出「Cursor 正在运行」的提示，正常关闭 Cursor（`Cmd+Q`）即可。

> 💡 如果 Docker 不可用，脚本会自动切换到本机 Python 模式，效果一样。

---

## 7. 打开 Cursor 使用

### 7.1 启动 Cursor

`deploy.sh` 会自动打开 Cursor。若未自动启动，手动打开 Cursor 即可。

### 7.2 选择模型

在 Cursor 聊天窗口的左上角，点击模型名称下拉菜单：

1. 找到并选择 **`deepseek-v4-pro`**
2. 将模式切换为 **Agent**（而不是 Chat）

### 7.3 测试一下

在聊天框中输入：

```
你好，请用中文回答：1+1等于几？
```

如果正常收到回复，恭喜，配置成功！🎉

---

## 8. 验证是否成功

如果想确认一切是否正常，可以运行诊断脚本：

```bash
bash verify.sh
```

它会检查 6 个关键环节：

```
========== 1. .env ==========
  DEEPSEEK_API_KEY: sk-xxxx...xxxx (OK)

========== 2. DeepSeek 官方 API ==========
  官方 API: 200 OK — Key 有效

========== 3. 本地代理 :9000 ==========
  本地代理可访问

========== 4. 公网隧道 ==========
  隧道 URL: 200 OK

========== 5. Docker 容器 ==========
  容器在运行

========== 6. Cursor 配置 ==========
  Cursor openAIKey 一致
```

如果全是绿色，说明一切完美。

---

## 9. 日常使用

### 9.1 推荐：一条命令重新部署

开机后或 Cursor 报 **Tunnel error / Network Error** 时，优先执行：

```bash
bash redeploy.sh
```

会自动：停止旧服务 → 重建 `proxy` + `url-sync` → 等待新隧道 → 同步 Cursor → 打开 Cursor。

### 9.2 自动 URL 同步（已内置）

`docker-compose` 包含 **url-sync** 容器，持续监视 `docker/data/public-url.txt`。  
隧道 URL 与 `.env` / Cursor 不一致时，会自动更新并触发 macOS 宿主机同步（可能短暂退出 Cursor）。

一般无需手动执行 `sync_cursor.py`；若需手动：

```bash
python3 src/sync_cursor.py --launch
```

### 9.3 每次开机后

1. 打开 **Docker Desktop**
2. 运行 `bash redeploy.sh`（或 `bash docker/bin/up.sh` 若容器仍在）

### 9.4 停止服务

```bash
bash docker/bin/down.sh
```

### 9.5 查看日志

```bash
bash docker/bin/logs.sh
tail -f docker/data/url-watcher-host.log
docker logs -f cursor-deepseek-url-sync
```

---

## 10. 故障排查

### 问题 1：`deploy.sh` 报 "未找到 Docker"

**原因**：Docker Desktop 没启动。

**解决**：
1. 打开「应用程序」→ 找到 Docker → 双击启动
2. 菜单栏出现 Docker 图标后，重新运行 `bash deploy.sh`

---

### 问题 2：Cloudflare Tunnel error 1033 / Network Error

**原因**：容器重启后隧道 URL 变了，Cursor 仍指向旧地址。

**解决**：
```bash
bash redeploy.sh
```

### 问题 3：报错 "The reasoning_content must be passed back"

**原因**：Cursor 直连了 `api.deepseek.com`，未走本地代理。

**解决**：确认 Base URL 为 `https://xxx.trycloudflare.com/v1`，执行 `bash redeploy.sh`。

---

### 问题 4：DeepSeek API 返回 401

**原因**：API Key 无效、过期或余额不足。

**解决**：
1. 到 [platform.deepseek.com](https://platform.deepseek.com) → API Keys 检查
2. 如果 Key 被删除了，创建新的
3. 如果余额不足，充一点（最低 ¥1）
4. 更新 `.env` 中的 Key，重新 `bash redeploy.sh`

---

### 问题 5：模型列表里找不到 `deepseek-v4-pro`

**原因**：`src/apply_config.py` 没有成功写入 Cursor 配置。

**解决**：
1. 完全退出 Cursor（`Cmd+Q`）
2. 执行 `python3 src/apply_config.py`
3. 重新打开 Cursor

---

### 问题 6：报了 "SSRF" 或 "localhost" 相关错误

**原因**：你在 Cursor 的 Settings 里手动把 Base URL 改成了 `http://127.0.0.1:9000`。Cursor 出于安全考虑不接受 127.0.0.1。

**解决**：
1. 不要手动改 Cursor Settings 里的 Base URL
2. 使用 `bash redeploy.sh` 自动配置（它会用 Cloudflare 的公网地址）
3. 在 Cursor Settings → Models 中确认 Base URL 是 `https://xxx.trycloudflare.com/v1`

---

## 方式二：本机 Python 部署（可选）

如果你不想装 Docker，可以用本机 Python 环境。**前提**：你已安装 Python 3.9+。

```bash
# 1. 安装 cloudflared（如果没有）
brew install cloudflared
# 或手动下载:
# curl -L -o ~/bin/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-arm64
# chmod +x ~/bin/cloudflared

# 2. 填写 .env（同第 5 步）

# 3. 运行 setup.sh（不含 Docker 时自动用本机模式）
bash deploy.sh
```

没有 Docker 的情况下，`setup.sh` 会自动：
- 创建 Python 虚拟环境 `~/deepseek-v4-pro-venv`
- 安装 `deepseek-cursor-proxy`
- 安装 `cloudflared`（如果没有）
- 启动代理 + 隧道
- 写入 Cursor 配置

---

## 项目结构一览

```
cursor-deepseek-v4/
├── deploy.sh             ← 一键部署入口
├── scripts/              ← deploy / setup / verify
├── src/                  ← apply_config.py / sync_cursor.py
├── config/               ← env.example、proxy-config.yaml（high）
├── docs/                 ← 教程、架构、运维、安全
└── docker/
    ├── bin/              ← up / down / restart / logs
    ├── tools/            ← 隧道监视、连接修复
    └── Dockerfile / docker-compose.yml
```

Clash 用户请阅读 [运维手册 - 代理放行](./OPERATIONS.md#三代理--防火墙放行重要)。

---

## 下一步

- 了解 [架构与原理](./ARCHITECTURE.md)（含反代风险与自建穿透）
- 运维与 Clash 规则：[OPERATIONS.md](./OPERATIONS.md)
- 安全加固：[SECURITY.md](./SECURITY.md)
- 如果你用着不错，欢迎给项目点个 Star ⭐

有问题？提 [GitHub Issue](https://github.com/WsKing0902/cursor-deepseek-proxy/issues)。
