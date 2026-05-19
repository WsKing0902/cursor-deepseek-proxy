#!/usr/bin/env bash
# ============================================================
#  Cursor × DeepSeek V4 一键部署脚本
#  用法: bash setup.sh
# ============================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env"
ENV_EXAMPLE="${PROJECT_ROOT}/config/env.example"

# --------------- 颜色 ---------------
red()    { printf '\033[31m%s\033[0m\n' "$*"; }
green()  { printf '\033[32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[33m%s\033[0m\n' "$*"; }
bold()   { printf '\033[1m%s\033[0m\n' "$*"; }

echo ""
bold "=============================================="
bold "  Cursor × DeepSeek V4 — 一键部署"
bold "=============================================="
echo ""

# ============================================================
# 第一步：检查 .env
# ============================================================
echo "━━━ 第一步：检查配置 ━━━"

if [[ ! -f "$ENV_FILE" ]]; then
    if [[ -f "$ENV_EXAMPLE" ]]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        green "✓ 已从 .env.example 创建 .env"
    else
        cat > "$ENV_FILE" <<'EOF'
# DeepSeek API Key（从 https://platform.deepseek.com 获取）
DEEPSEEK_API_KEY=sk-your-key-here

# 上游 API 地址（一般不用改）
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-pro

# 代理公网地址（setup.sh 会自动填写，不要手动改）
CURSOR_BASE_URL=
EOF
        green "✓ 已创建 .env 模板"
    fi
    echo ""
    yellow "⚠️  请先编辑 .env 填写你的 DeepSeek API Key，然后重新运行 bash setup.sh"
    echo ""
    echo "   编辑命令: nano ${ENV_FILE}"
    echo "   获取 Key: https://platform.deepseek.com → API Keys"
    echo ""
    exit 0
fi

# 读取 API Key
DEEPSEEK_API_KEY=""
while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line//$'\r'/}"
    [[ "$line" =~ ^DEEPSEEK_API_KEY=(.*)$ ]] && DEEPSEEK_API_KEY="${BASH_REMATCH[1]}"
done <"$ENV_FILE"

if [[ -z "$DEEPSEEK_API_KEY" ]] || [[ "$DEEPSEEK_API_KEY" == "sk-your-key-here" ]]; then
    red "✗ 请在 .env 中填写真实的 DEEPSEEK_API_KEY"
    echo "  获取 Key: https://platform.deepseek.com → API Keys"
    echo "  编辑: nano ${ENV_FILE}"
    exit 1
fi
green "✓ API Key 已配置 (${DEEPSEEK_API_KEY:0:8}...${DEEPSEEK_API_KEY: -4})"

# ============================================================
# 第二步：检查依赖
# ============================================================
echo ""
echo "━━━ 第二步：检查依赖 ━━━"

HAS_DOCKER=false
HAS_PYTHON=false

if docker info >/dev/null 2>&1; then
    HAS_DOCKER=true
    green "✓ Docker 可用"
else
    yellow "⚠ Docker 未运行（将使用本机 Python 模式）"
fi

if command -v python3 >/dev/null 2>&1; then
    HAS_PYTHON=true
    green "✓ Python3 可用 ($(python3 --version))"
else
    red "✗ 需要 Python 3.9+。请安装: brew install python3"
    exit 1
fi

# ============================================================
# 第三步：验证 DeepSeek API Key
# ============================================================
echo ""
echo "━━━ 第三步：验证 API Key ━━━"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -m 15 \
    "https://api.deepseek.com/v1/models" \
    -H "Authorization: Bearer ${DEEPSEEK_API_KEY}" 2>/dev/null || echo "000")

if [[ "$HTTP_CODE" == "200" ]]; then
    green "✓ DeepSeek API Key 有效"
elif [[ "$HTTP_CODE" == "401" ]]; then
    red "✗ API Key 无效或余额不足"
    echo "  请到 https://platform.deepseek.com 检查 Key 状态并充值"
    exit 1
else
    yellow "⚠ 无法验证 API Key (HTTP $HTTP_CODE)，继续部署..."
fi

# ============================================================
# 第四步：选择部署模式
# ============================================================
echo ""
echo "━━━ 第四步：部署 ━━━"

DOCKER_LAUNCHED_CURSOR=false
NATIVE_LAUNCHED_CURSOR=false

if $HAS_DOCKER; then
    echo ">>> 使用 Docker 模式（推荐）..."
    echo ""

    # Kill old processes
    pkill -f "deepseek-cursor-proxy" 2>/dev/null || true
    pkill -f "cloudflared tunnel" 2>/dev/null || true

    # Create data dir
    mkdir -p "${PROJECT_ROOT}/docker/data"

    # Build and start
    cd "${PROJECT_ROOT}/docker"

    COMPOSE_ARGS=(-f docker-compose.yml)
    [[ -f .env.docker ]] && COMPOSE_ARGS+=(--env-file .env.docker)

    # Auto-detect available Python image
    if [[ -z "${PYTHON_IMAGE:-}" ]] && [[ ! -f .env.docker ]]; then
        for img in \
            "docker.m.daocloud.io/library/python:3.11-slim" \
            "python:3.11-slim" \
            "python:3.11"; do
            if docker image inspect "$img" >/dev/null 2>&1; then
                export PYTHON_IMAGE="$img"
                echo ">>> 使用已有镜像: $img"
                break
            fi
        done
    fi

    echo ">>> 构建镜像（首次约 1-2 分钟）..."
    docker compose "${COMPOSE_ARGS[@]}" build 2>&1 | tail -5

    echo ">>> 启动容器..."
    docker compose "${COMPOSE_ARGS[@]}" up -d

    cd "$PROJECT_ROOT"

    echo ">>> 等待隧道就绪，同步 Cursor 并启动..."
    python3 "${PROJECT_ROOT}/src/sync_cursor.py" --wait --launch
    DOCKER_LAUNCHED_CURSOR=true

else
    echo ">>> 使用本机 Python 模式..."
    echo ""

    # Kill old processes
    pkill -f "deepseek-cursor-proxy" 2>/dev/null || true
    pkill -f "cloudflared tunnel" 2>/dev/null || true

    PROXY_BIN="${HOME}/deepseek-v4-pro-venv/bin/deepseek-cursor-proxy"
    LOG_DIR="${HOME}/deepseek-v4-pro-logs"
    mkdir -p "$LOG_DIR"
    export PATH="${HOME}/bin:/opt/homebrew/bin:/usr/local/bin:${PATH}"

    # Install proxy if missing
    if [[ ! -x "$PROXY_BIN" ]]; then
        echo ">>> 安装 deepseek-cursor-proxy..."
        python3 -m venv "${HOME}/deepseek-v4-pro-venv"
        "${HOME}/deepseek-v4-pro-venv/bin/pip" install -q \
            "git+https://github.com/yxlao/deepseek-cursor-proxy.git" 2>&1 | tail -3
        green "✓ 代理已安装"
    fi

    # Install cloudflared if missing
    if ! command -v cloudflared >/dev/null 2>&1 && [[ ! -x "${HOME}/bin/cloudflared" ]]; then
        echo ">>> 安装 cloudflared..."
        arch=$(uname -m)
        [[ "$arch" == "arm64" ]] && cf_arch="arm64" || cf_arch="amd64"
        curl -fsSL -o /tmp/cf.tgz \
            "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-${cf_arch}.tgz"
        mkdir -p "${HOME}/bin"
        tar -xzf /tmp/cf.tgz -C "${HOME}/bin" cloudflared
        chmod +x "${HOME}/bin/cloudflared"
        green "✓ cloudflared 已安装"
    fi

    # 安装代理配置（思考模式 high，非 max）
    PROXY_CONFIG="${PROJECT_ROOT}/config/proxy-config.yaml"
    mkdir -p "${HOME}/.deepseek-cursor-proxy"
    cp "${PROXY_CONFIG}" "${HOME}/.deepseek-cursor-proxy/config.yaml"

    # Start proxy
    echo ">>> 启动代理..."
    nohup "$PROXY_BIN" --config "${HOME}/.deepseek-cursor-proxy/config.yaml" --no-ngrok --port 9000 >"${LOG_DIR}/proxy.log" 2>&1 &
    PROXY_PID=$!
    echo $PROXY_PID >"${LOG_DIR}/proxy.pid"
    sleep 2

    if ! curl -sf "http://127.0.0.1:9000/v1/models" -H "Authorization: Bearer x" >/dev/null 2>&1; then
        red "✗ 代理启动失败，查看日志: tail -30 ${LOG_DIR}/proxy.log"
        exit 1
    fi
    green "✓ 代理已启动 (127.0.0.1:9000)"

    # Start Cloudflare tunnel
    echo ">>> 启动 Cloudflare 隧道..."
    : >"${LOG_DIR}/cloudflared.log"
    if command -v cloudflared >/dev/null 2>&1; then
        nohup cloudflared tunnel --url http://127.0.0.1:9000 >>"${LOG_DIR}/cloudflared.log" 2>&1 &
    else
        nohup "${HOME}/bin/cloudflared" tunnel --url http://127.0.0.1:9000 >>"${LOG_DIR}/cloudflared.log" 2>&1 &
    fi
    TUNNEL_PID=$!
    echo $TUNNEL_PID >"${LOG_DIR}/tunnel.pid"

    # Wait for tunnel URL
    PUBLIC_URL=""
    for i in $(seq 1 60); do
        PUBLIC_URL=$(grep -oE 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' "${LOG_DIR}/cloudflared.log" 2>/dev/null \
            | grep -v 'api\.trycloudflare' | head -1 || true)
        [[ -n "$PUBLIC_URL" ]] && break
        sleep 1
    done

    if [[ -z "$PUBLIC_URL" ]]; then
        red "✗ Cloudflare 隧道启动失败"
        tail -15 "${LOG_DIR}/cloudflared.log" 2>/dev/null || true
        exit 1
    fi
    PUBLIC_URL="${PUBLIC_URL%/}/v1"
    green "✓ 隧道就绪: $PUBLIC_URL"

    # Update .env
    python3 -c "
from pathlib import Path
p = Path('${ENV_FILE}')
lines = p.read_text().splitlines()
out, found = [], False
for line in lines:
    if line.startswith('CURSOR_BASE_URL='):
        out.append(f'CURSOR_BASE_URL=${PUBLIC_URL}')
        found = True
    else:
        out.append(line)
if not found:
    out.append(f'CURSOR_BASE_URL=${PUBLIC_URL}')
p.write_text('\n'.join(out) + '\n')
"
    mkdir -p "${PROJECT_ROOT}/docker/data"
    printf '%s\n' "$PUBLIC_URL" >"${PROJECT_ROOT}/docker/data/public-url.txt"

    echo ">>> 同步 Cursor 配置并启动..."
    python3 "${PROJECT_ROOT}/src/sync_cursor.py" --launch
    NATIVE_LAUNCHED_CURSOR=true
fi

# ============================================================
# 完成
# ============================================================

echo ""
bold "=============================================="
bold "  部署完成！"
bold "=============================================="
echo ""

if $DOCKER_LAUNCHED_CURSOR || $NATIVE_LAUNCHED_CURSOR; then
    echo "  Cursor 已自动打开，请选择 deepseek-v4-pro，使用 Agent 模式。"
else
    echo "  下一步:"
    echo "  1. 打开 Cursor"
    echo "  2. 选择 deepseek-v4-pro，切换到 Agent 模式"
fi
echo ""

if $HAS_DOCKER; then
    PUBLIC_URL=$(tr -d '\r\n' <"${PROJECT_ROOT}/docker/data/public-url.txt" 2>/dev/null || echo "未知")
    echo "  公网地址: $PUBLIC_URL"
    echo "  查看日志: bash ${PROJECT_ROOT}/docker/bin/logs.sh"
    echo "  停止服务: bash ${PROJECT_ROOT}/docker/bin/down.sh"
    echo "  再次部署: bash ${PROJECT_ROOT}/scripts/deploy.sh"
else
    echo "  公网地址: $PUBLIC_URL"
    echo "  查看日志: tail -f ${LOG_DIR}/proxy.log"
    echo "  停止服务: pkill -f deepseek-cursor-proxy; pkill -f cloudflared"
fi
echo ""
