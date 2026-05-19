#!/usr/bin/env python3
"""修复 Cursor 连不上：把可用的 Base URL 写入 .env 和 Cursor 数据库。"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENV_FILE = Path.home() / ".cursor/deepseek-v4-pro/.env"
APPLY_PY = Path.home() / ".cursor/deepseek-v4-pro/apply-config.py"
URL_FILE = Path.home() / "deepseek-cursor-docker/data/public-url.txt"
LOCAL_URL = "http://127.0.0.1:9000/v1"
DB = Path.home() / "Library/Application Support/Cursor/User/globalStorage/state.vscdb"
APP_KEY = (
    "src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl"
    ".persistentStorage.applicationUser"
)


def load_key() -> str:
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip().replace("\r", "")
        if line.startswith("DEEPSEEK_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("未找到 DEEPSEEK_API_KEY，请检查 .env")


def probe(base: str, api_key: str) -> int:
    url = f"{base.rstrip('/')}/models"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
        method="GET",
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=15) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def pick_url(mode: str, api_key: str) -> str | None:
    if mode == "local":
        return LOCAL_URL if probe(LOCAL_URL, api_key) == 200 else None
    if mode == "tunnel":
        if not URL_FILE.is_file():
            return None
        tunnel = URL_FILE.read_text(encoding="utf-8").strip()
        return tunnel if probe(tunnel, api_key) == 200 else None
    if probe(LOCAL_URL, api_key) == 200:
        return LOCAL_URL
    if URL_FILE.is_file():
        tunnel = URL_FILE.read_text(encoding="utf-8").strip()
        if probe(tunnel, api_key) == 200:
            return tunnel
    return None


def update_env(url: str) -> None:
    lines = ENV_FILE.read_text(encoding="utf-8").replace("\r\n", "\n").splitlines()
    out: list[str] = []
    found = False
    for line in lines:
        if line.startswith("CURSOR_BASE_URL="):
            out.append(f"CURSOR_BASE_URL={url}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"CURSOR_BASE_URL={url}")
    ENV_FILE.write_text("\n".join(out) + "\n", encoding="utf-8")


def patch_cursor(url: str, api_key: str) -> str:
    conn = sqlite3.connect(DB)
    row = conn.execute("SELECT value FROM ItemTable WHERE key=?", (APP_KEY,)).fetchone()
    if not row:
        raise SystemExit("未找到 Cursor 配置数据库项")
    data = json.loads(row[0])
    old = data.get("openAIBaseUrl", "")
    data["openAIBaseUrl"] = url.rstrip("/")
    data["useOpenAIKey"] = True
    model = "deepseek-v4-pro"
    ai = data.setdefault("aiSettings", {})
    ums = list(ai.get("userAddedModels") or [])
    if model not in ums:
        ums.append(model)
    ai["userAddedModels"] = ums
    for mode in ("composer", "quick-agent", "cmd-k"):
        mc = ai.get("modelConfig", {}).get(mode)
        if mc:
            mc["modelName"] = model
            mc["selectedModels"] = [{"modelId": model, "parameters": []}]
    ai["composerModel"] = model
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
    return old


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "auto"
    api_key = load_key()

    print(">>> 检测连通性")
    lc = probe(LOCAL_URL, api_key)
    print(f"    本地 {LOCAL_URL} -> HTTP {lc or '失败'}")
    if URL_FILE.is_file():
        tunnel = URL_FILE.read_text(encoding="utf-8").strip()
        tc = probe(tunnel, api_key)
        print(f"    隧道 {tunnel} -> HTTP {tc or '失败'}")

    target = pick_url(mode, api_key)
    if not target:
        print("\n没有可用端点。请先启动代理：")
        print("  bash ~/deepseek-cursor-docker/up.sh")
        print("  或 bash ~/deepseek-cursor-docker/start-local.sh")
        return 1

    print(f"\n>>> 使用: {target}")
    update_env(target)
    old = patch_cursor(target, api_key)
    print(f"    旧 URL: {old}")
    print(f"    新 URL: {target}")

    if subprocess.run(["pgrep", "-x", "Cursor"], capture_output=True).returncode == 0:
        print(">>> 请 Cmd+Q 退出 Cursor 后重开（或已自动退出）")
        subprocess.run(
            ["osascript", "-e", 'tell application "Cursor" to quit'],
            check=False,
        )

    print("\n完成。重开 Cursor，选择 deepseek-v4-pro。")
    if target.startswith("http://127.0.0.1"):
        print("若仍连不上，Cursor 可能不接受 HTTP 本地地址，请试:")
        print("  python3 ~/deepseek-cursor-docker/fix-connect.py tunnel")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
