#!/usr/bin/env bash
# 项目根目录便捷入口 → scripts/deploy.sh
exec bash "$(cd "$(dirname "$0")" && pwd)/scripts/deploy.sh" "$@"
