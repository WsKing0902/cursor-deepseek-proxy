#!/usr/bin/env python3
"""
启动/刷新 cloudflared 隧道并写入 Cursor（Cursor 不能连 localhost，必须用公网 HTTPS）。

用法（先 Cmd+Q 退出 Cursor）:
  python3 ~/deepseek-cursor-docker/refresh-tunnel.py
"""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROXY_PORT = 9000
PROXY_BIN = Path.home() / "deepseek-v4-pro-venv/bin/deepseek-cursor-proxy"
CF = Path.home() / "bin/cloudflared"
LOG_DIR = Path.home() / "deepseek-v4-pro-logs"
ENV_FILE = Path.home() / ".cursor/deepseek-v4-pro/.env"
URL_FILE = Path.home() / "deepseek-cursor-docker/data/public-url.txt"
DB = Path.home() / "Library/Application Support/Cursor/User/globalStorage/state.vscdb"
APP_KEY = (
    "src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl"
    ".persistentStorage.applicationUser"
)
MODEL = "deepseek-v4-pro"


def load_key() -> str:
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip().replace("\r", "")
        if line.startswith("DEEPSEEK_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("请在 .env 配置 DEEPSEEK_API_KEY")


def probe(base: str, key: str) -> bool:
    req = urllib.request.Request(
        f"{base.rstrip('/')}/models",
        headers={"Authorization": f"Bearer {key}"},
    )
    # 避免 shell 里的 https_proxy 导致误判隧道不可用
    no_proxy = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(no_proxy)
    try:
        with opener.open(req, timeout=15) as r:
            return r.status == 200
    except Exception:
        return False


def ensure_proxy() -> None:
    if probe(f"http://127.0.0.1:{PROXY_PORT}/v1", load_key()):
        print(">>> 本地代理已在 :9000")
        return
    if not PROXY_BIN.is_file():
        sys.exit(f"缺少代理: {PROXY_BIN}")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(["pkill", "-f", "deepseek-cursor-proxy"], check=False)
    time.sleep(1)
    log = LOG_DIR / "proxy.log"
    with open(log, "ab") as out:
        subprocess.Popen(
            [str(PROXY_BIN), "--no-ngrok", "--host", "127.0.0.1", "--port", str(PROXY_PORT)],
            stdout=out,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    for _ in range(30):
        if probe(f"http://127.0.0.1:{PROXY_PORT}/v1", load_key()):
            print(">>> 已启动本地代理 :9000")
            return
        time.sleep(1)
    sys.exit(f"代理启动失败，见 {log}")


def start_tunnel() -> str:
    if not CF.is_file():
        sys.exit(f"缺少 cloudflared: {CF}")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    URL_FILE.parent.mkdir(parents=True, exist_ok=True)
    cf_log = LOG_DIR / "cloudflared.log"
    subprocess.run(["pkill", "-f", "cloudflared tunnel"], check=False)
    time.sleep(1)
    cf_log.write_text("", encoding="utf-8")
    subprocess.Popen(
        [str(CF), "tunnel", "--url", f"http://127.0.0.1:{PROXY_PORT}"],
        stdout=open(cf_log, "ab"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    pat = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
    for _ in range(90):
        text = cf_log.read_text(encoding="utf-8", errors="replace")
        m = pat.search(text)
        if m:
            url = f"{m.group(0).rstrip('/')}/v1"
            URL_FILE.write_text(url + "\n", encoding="utf-8")
            key = load_key()
            for _ in range(30):
                if probe(url, key):
                    print(f">>> 隧道可用: {url}")
                    return url
                time.sleep(1)
        time.sleep(1)
    sys.exit(f"隧道未就绪，见 {cf_log}")


def apply(url: str, key: str) -> None:
    lines = ENV_FILE.read_text(encoding="utf-8").replace("\r\n", "\n").splitlines()
    out = [
        (f"CURSOR_BASE_URL={url}" if l.startswith("CURSOR_BASE_URL=") else l)
        for l in lines
    ]
    if not any(l.startswith("CURSOR_BASE_URL=") for l in out):
        out.append(f"CURSOR_BASE_URL={url}")
    ENV_FILE.write_text("\n".join(out) + "\n", encoding="utf-8")

    conn = sqlite3.connect(DB)
    row = conn.execute("SELECT value FROM ItemTable WHERE key=?", (APP_KEY,)).fetchone()
    data = json.loads(row[0])
    old = data.get("openAIBaseUrl", "")
    data["openAIBaseUrl"] = url.rstrip("/")
    data["useOpenAIKey"] = True
    ai = data.setdefault("aiSettings", {})
    ums = list(ai.get("userAddedModels") or [])
    if MODEL not in ums:
        ums.append(MODEL)
    ai["userAddedModels"] = ums
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
    print(f">>> Cursor DB 已更新")
    print(f"    旧: {old}")
    print(f"    新: {url}")


def main() -> int:
    if subprocess.run(["pgrep", "-x", "Cursor"], capture_output=True).returncode == 0:
        print("请先 Cmd+Q 完全退出 Cursor")
        return 1
    key = load_key()
    # Docker 占 9000 时 curl 可能打到错误进程
    subprocess.run(["docker", "stop", "cursor-deepseek-proxy", "cursor-deepseek-proxy-local"], check=False)
    ensure_proxy()
    url = start_tunnel()
    apply(url, key)
    print()
    print("说明: Cursor 有 SSRF 防护，不能连 127.0.0.1，必须用上面的 HTTPS 隧道。")
    print("代理在本机，只有 Cursor→隧道 这一段走 Cloudflare；推理仍走 DeepSeek。")
    print("重开 Cursor 后测试 deepseek-v4-pro。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
