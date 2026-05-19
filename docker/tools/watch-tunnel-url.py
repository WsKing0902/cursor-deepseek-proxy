#!/usr/bin/env python3
"""
监视 data/public-url.txt，隧道地址变化时自动 sync-cursor.py。
供 launchd 或手动后台运行。
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

DOCKER_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = DOCKER_DIR.parent
URL_FILE = DOCKER_DIR / "data/public-url.txt"
SYNC = PROJECT_ROOT / "src/sync_cursor.py"
INTERVAL = 5


def main() -> int:
    last = URL_FILE.read_text(encoding="utf-8").strip() if URL_FILE.is_file() else ""
    print(f"[watch] 监视 {URL_FILE}", flush=True)
    if last:
        print(f"[watch] 当前: {last}", flush=True)
    while True:
        try:
            cur = URL_FILE.read_text(encoding="utf-8").strip() if URL_FILE.is_file() else ""
        except OSError:
            cur = ""
        if cur and cur != last:
            print(f"[watch] 检测到变化 → {cur}", flush=True)
            subprocess.run([sys.executable, str(SYNC)], check=False)
            last = cur
        time.sleep(INTERVAL)


if __name__ == "__main__":
    raise SystemExit(main())
