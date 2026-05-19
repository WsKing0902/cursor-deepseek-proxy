# 发布到 GitHub 检查清单

推送前请确认：

## 安全

- [ ] `.env` 未提交（已在 `.gitignore`）
- [ ] `docker/data/` 日志、密钥未提交
- [ ] 代码中无真实 `sk-` API Key

## 仓库设置

1. 仓库地址：https://github.com/WsKing0902/cursor-deepseek-proxy
2. 克隆后目录名为 `cursor-deepseek-proxy`
3. 可选：添加仓库 Description  
   `在 Cursor 中使用 DeepSeek V4 Agent 模式，自动处理 reasoning_content + Cloudflare 隧道`

## 首次推送

```bash
cd cursor-deepseek-proxy
git init
git add .
git commit -m "feat: Cursor DeepSeek V4 一键部署与 URL 自动同步"
git branch -M main
git remote add origin https://github.com/WsKing0902/cursor-deepseek-proxy.git
git push -u origin main
```

## 建议的仓库 Topics

`cursor` `deepseek` `docker` `cloudflare-tunnel` `byok` `agent-mode`
