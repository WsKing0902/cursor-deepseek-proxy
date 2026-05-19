#!/usr/bin/env python3
"""安装 macOS launchd：容器重启导致 public-url.txt 变化时自动同步 Cursor。"""
from __future__ import annotations

import plistlib
import subprocess
import sys
from pathlib import Path

DOCKER_DIR = Path(__file__).resolve().parent.parent
WATCH = DOCKER_DIR / "tools/watch-tunnel-url.py"
PLIST = Path.home() / "Library/LaunchAgents/com.cursor-deepseek.url-sync.plist"
LABEL = "com.cursor-deepseek.url-sync"


def main() -> int:
    if not WATCH.is_file():
        sys.exit(f"缺少 {WATCH}")

    plist = {
        "Label": LABEL,
        "ProgramArguments": [sys.executable, str(WATCH)],
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(DOCKER_DIR / "data/watch-sync.log"),
        "StandardErrorPath": str(DOCKER_DIR / "data/watch-sync.log"),
        "EnvironmentVariables": {
            "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin",
        },
    }
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    PLIST.write_bytes(plistlib.dumps(plist))
    subprocess.run(["launchctl", "unload", str(PLIST)], capture_output=True)
    r = subprocess.run(["launchctl", "load", str(PLIST)], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr or r.stdout)
        return 1
    print("已安装自动同步守护进程:")
    print(f"  {PLIST}")
    print("日志: ~/deepseek-cursor-docker/data/watch-sync.log")
    print("卸载: python3 install-auto-sync.py --uninstall")
    return 0


def uninstall() -> int:
    subprocess.run(["launchctl", "unload", str(PLIST)], capture_output=True)
    if PLIST.is_file():
        PLIST.unlink()
    print("已卸载自动同步")
    return 0


if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        raise SystemExit(uninstall())
    raise SystemExit(main())
