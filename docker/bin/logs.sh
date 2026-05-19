#!/usr/bin/env bash
DIR="$(cd "$(dirname "$0")/.." && pwd)"
docker compose -f "${DIR}/docker-compose.yml" logs -f --tail=100
