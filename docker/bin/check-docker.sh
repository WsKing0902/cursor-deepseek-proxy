#!/usr/bin/env bash
echo "=== Docker 诊断 ==="
echo "1. Docker Desktop 进程:"
pgrep -l "Docker Desktop" || echo "   未运行 → 请打开 Docker Desktop"
echo ""
echo "2. Context:"
docker context ls 2>&1 || true
echo ""
echo "3. Ping:"
docker info 2>&1 | head -5 || true
echo ""
echo "4. Socket:"
ls -la "${HOME}/.docker/run/docker.sock" 2>&1 || true
