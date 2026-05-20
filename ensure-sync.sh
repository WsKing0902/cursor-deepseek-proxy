#!/usr/bin/env bash
exec "$(cd "$(dirname "$0")" && pwd)/scripts/ensure-host-sync.sh" "$@"
