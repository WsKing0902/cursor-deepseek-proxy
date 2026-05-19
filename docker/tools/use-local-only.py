#!/usr/bin/env python3
"""
本地直连 DeepSeek（不走 Cloudflare）

用法:
  1. Cmd+Q 退出 Cursor
  2. python3 ~/deepseek-cursor-docker/use-local-only.py
  3. 重开 Cursor，选 deepseek-v4-pro

可选:
  python3 use-local-only.py --docker   # 用 Docker 起代理（仍只映射 localhost:9000）
  python3 use-local-only.py --native   # 本机 venv（默认，延迟最低）
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

LOCAL_URL = "http://127.0.0.1:9000/v1"
MODEL = "deepseek-v4-pro"
ENV_FILE = Path.home() / ".cursor/deepseek-v4-pro/.env"
DB = Path.home() / "Library/Application Support/Cursor/User/globalStorage/state.vscdb"
APP_KEY = (
    "src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl"
    ".persistentStorage.applicationUser"
)
PROXY_BIN = Path.home() / "deepseek-v4-pro-venv/bin/deepseek-cursor-proxy"
LOG_DIR = Path.home() / "deepseek-v4-pro-logs"
DOCKER_DIR = Path.home() / "deepseek-cursor-docker"


def load_key() -> str:
    if not ENV_FILE.is_file():
        sys.exit(f"缺少 {ENV_FILE}")
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip().replace("\r", "")
        if line.startswith("DEEPSEEK_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit("请在 .env 中设置 DEEPSEEK_API_KEY")


def probe() -> bool:
    key = load_key()
    req = urllib.request.Request(
        f"{LOCAL_URL}/models",
        headers={"Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


def stop_tunnel_and_old_proxy() -> None:
    for pat in ("cloudflared tunnel", "deepseek-cursor-proxy"):
        subprocess.run(["pkill", "-f", pat], check=False)
    time.sleep(1)
    for name in ("cursor-deepseek-proxy", "cursor-deepseek-proxy-local"):
        subprocess.run(
            ["docker", "stop", name],
            capture_output=True,
            check=False,
        )


def start_native() -> None:
    if not PROXY_BIN.is_file():
        sys.exit(
            "未找到代理，请先运行:\n"
            "  bash ~/deepseek-cursor-docker/start-local.sh\n"
            "（只需安装 venv 一次，之后用本脚本即可）"
        )
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = LOG_DIR / "proxy.log"
    pid_file = LOG_DIR / "proxy.pid"
    with open(log, "ab") as out:
        proc = subprocess.Popen(
            [str(PROXY_BIN), "--no-ngrok", "--host", "127.0.0.1", "--port", "9000"],
            stdout=out,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    pid_file.write_text(str(proc.pid), encoding="utf-8")
    for _ in range(30):
        if probe():
            print(f">>> 本机代理已启动 (pid {proc.pid})")
            return
        time.sleep(1)
    sys.exit(f"代理启动失败，查看 {log}")


def start_docker() -> None:
    compose = DOCKER_DIR / "docker-compose.local.yml"
    subprocess.run(
        ["docker", "compose", "-f", str(compose), "up", "-d", "--build"],
        cwd=DOCKER_DIR,
        check=True,
    )
    for _ in range(60):
        if probe():
            print(">>> Docker 本地代理已启动 (localhost:9000)")
            return
        time.sleep(1)
    subprocess.run(
        ["docker", "compose", "-f", str(compose), "logs", "--tail", "40"],
        cwd=DOCKER_DIR,
        check=False,
    )
    sys.exit("Docker 代理未就绪")


def apply_cursor(api_key: str) -> None:
    url = LOCAL_URL.rstrip("/")
    lines = ENV_FILE.read_text(encoding="utf-8").replace("\r\n", "\n").splitlines()
    out: list[str] = []
    for line in lines:
        if line.startswith("CURSOR_BASE_URL="):
            out.append(f"CURSOR_BASE_URL={LOCAL_URL}")
        else:
            out.append(line)
    if not any(l.startswith("CURSOR_BASE_URL=") for l in out):
        out.append(f"CURSOR_BASE_URL={LOCAL_URL}")
    ENV_FILE.write_text("\n".join(out) + "\n", encoding="utf-8")

    conn = sqlite3.connect(DB)
    row = conn.execute("SELECT value FROM ItemTable WHERE key=?", (APP_KEY,)).fetchone()
    if not row:
        sys.exit("未找到 Cursor 配置库")
    data = json.loads(row[0])
    old = data.get("openAIBaseUrl", "")
    data["openAIBaseUrl"] = url
    data["useOpenAIKey"] = True
    ai = data.setdefault("aiSettings", {})
    ums = list(ai.get("userAddedModels") or [])
    if MODEL not in ums:
        ums.append(MODEL)
    ai["userAddedModels"] = ums
    for mode in ("composer", "quick-agent", "cmd-k"):
        mc = ai.get("modelConfig", {}).get(mode)
        if mc:
            mc["modelName"] = MODEL
            mc["selectedModels"] = [{"modelId": MODEL, "parameters": []}]
    ai["composerModel"] = MODEL
    conn.execute(
        "INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
        (APP_KEY, json.dumps(data, separators=(",", ":"))),
    )
    conn.execute(
        "INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
        ("cursorAuth/openAIKey", api_key),
    )
    conn.commit()
    conn.close()
    print(f">>> Cursor 已设为本地直连")
    print(f"    旧: {old}")
    print(f"    新: {LOCAL_URL}")


def main() -> int:
    p = argparse.ArgumentParser(description="DeepSeek 本地直连（无 Cloudflare）")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--docker", action="store_true", help="用 Docker 起代理")
    g.add_argument("--native", action="store_true", help="用本机 venv（默认）")
    args = p.parse_args()

    if subprocess.run(["pgrep", "-x", "Cursor"], capture_output=True).returncode == 0:
        print("请先 Cmd+Q 完全退出 Cursor，再运行本脚本。")
        return 1

    api_key = load_key()
    print(">>> 停止 cloudflared / 旧隧道容器...")
    stop_tunnel_and_old_proxy()

    if args.docker:
        start_docker()
    else:
        if not probe():
            start_native()
        else:
            print(">>> 本地代理已在运行")

    if not probe():
        sys.exit("本地 :9000 仍不可用")

    apply_cursor(api_key)
    print()
    print("完成。请打开 Cursor → Settings → Models 确认:")
    print(f"  Override Base URL = {LOCAL_URL}")
    print("  OpenAI API Key = 你的 DeepSeek Key")
    print("  模型 = deepseek-v4-pro")
    print()
    print()
    print("注意: Cursor 有 SSRF 防护，通常无法使用 127.0.0.1。")
    print("若仍报 trouble connecting，请改用:")
    print("  python3 ~/deepseek-cursor-docker/refresh-tunnel.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
