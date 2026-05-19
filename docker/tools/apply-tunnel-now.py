#!/usr/bin/env python3
"""把当前 cloudflared 日志里的隧道 URL 写入 .env 和 Cursor DB（Cursor 已退出时运行）。"""
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

TUNNEL = "https://companion-requesting-wma-editors.trycloudflare.com/v1"
ENV = Path.home() / ".cursor/deepseek-v4-pro/.env"
DB = Path.home() / "Library/Application Support/Cursor/User/globalStorage/state.vscdb"
APP_KEY = (
    "src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl"
    ".persistentStorage.applicationUser"
)
CF_LOG = Path.home() / "deepseek-v4-pro-logs/cloudflared.log"


def tunnel_from_log() -> str:
    if not CF_LOG.is_file():
        return TUNNEL
    m = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", CF_LOG.read_text())
    return f"{m.group(0).rstrip('/')}/v1" if m else TUNNEL


def main() -> int:
    if subprocess.run(["pgrep", "-x", "Cursor"], capture_output=True).returncode == 0:
        print("请先 Cmd+Q 退出 Cursor")
        return 1
    url = tunnel_from_log()
    key = ""
    lines = ENV.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines:
        if line.startswith("DEEPSEEK_API_KEY="):
            key = line.split("=", 1)[1].strip()
        if line.startswith("CURSOR_BASE_URL="):
            out.append(f"CURSOR_BASE_URL={url}")
        else:
            out.append(line)
    if not any(l.startswith("CURSOR_BASE_URL=") for l in out):
        out.append(f"CURSOR_BASE_URL={url}")
    ENV.write_text("\n".join(out) + "\n", encoding="utf-8")

    conn = sqlite3.connect(DB)
    data = json.loads(
        conn.execute("SELECT value FROM ItemTable WHERE key=?", (APP_KEY,)).fetchone()[0]
    )
    old = data.get("openAIBaseUrl", "")
    data["openAIBaseUrl"] = url.rstrip("/")
    data["useOpenAIKey"] = True
    conn.execute(
        "INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
        (APP_KEY, json.dumps(data, separators=(",", ":"))),
    )
    conn.execute(
        "INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
        ("cursorAuth/openAIKey", key),
    )
    conn.commit()
    conn.close()
    Path.home().joinpath("deepseek-cursor-docker/data/public-url.txt").write_text(
        url + "\n", encoding="utf-8"
    )
    print(f"已写入: {url}")
    print(f"旧 URL: {old}")
    print("重开 Cursor 测试。Settings 里 Override Base URL 必须与上面一致。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
