#!/usr/bin/env python3
"""
从 Docker 卷 data/public-url.txt 读取隧道地址，写入 .env 与 Cursor 数据库。

用法:
  python3 src/sync_cursor.py              # 同步（必要时退出 Cursor）
  python3 src/sync_cursor.py --wait       # 等待容器写出 URL（最多 90s）
  python3 src/sync_cursor.py --wait --launch  # 同步后自动打开 Cursor（部署脚本默认）
  python3 src/sync_cursor.py --check-only # 仅比较，不写入
  python3 src/sync_cursor.py --no-launch  # 同步但不启动 Cursor
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", str(Path(__file__).resolve().parent.parent)))
URL_FILE = Path(os.environ.get("URL_FILE", str(PROJECT_ROOT / "docker/data/public-url.txt")))
ENV_FILE = Path(os.environ.get("ENV_FILE", str(PROJECT_ROOT / ".env")))
APPLY_PY = PROJECT_ROOT / "src/apply_config.py"
_default_db = Path.home() / "Library/Application Support/Cursor/User/globalStorage/state.vscdb"
DB = Path(os.environ.get("CURSOR_DB", str(_default_db)))
APP_KEY = (
    "src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl"
    ".persistentStorage.applicationUser"
)
COMPOSE_FILE = PROJECT_ROOT / "docker/docker-compose.yml"
CONTAINER = "cursor-deepseek-proxy"


def cursor_running() -> bool:
    return subprocess.run(["pgrep", "-x", "Cursor"], capture_output=True).returncode == 0


def quit_cursor() -> None:
    subprocess.run(
        ["osascript", "-e", 'tell application "Cursor" to quit'],
        capture_output=True,
    )
    for _ in range(20):
        if not cursor_running():
            return
        time.sleep(0.5)


def launch_cursor() -> bool:
    if sys.platform != "darwin":
        print(
            "非 macOS：请手动打开 Cursor，选择 deepseek-v4-pro 或 deepseek-v4-flash。",
            file=sys.stderr,
        )
        return False
    r = subprocess.run(["open", "-a", "Cursor"], capture_output=True, text=True)
    if r.returncode != 0:
        print("无法启动 Cursor，请确认已安装 Cursor.app", file=sys.stderr)
        return False
    time.sleep(1.5)
    print("✓ 已启动 Cursor")
    print("  → 聊天窗口选择 deepseek-v4-pro / deepseek-v4-flash，切换到 Agent 模式")
    return True


def db_base_url() -> str | None:
    if not DB.is_file():
        return None
    row = sqlite3.connect(DB).execute(
        "SELECT value FROM ItemTable WHERE key=?", (APP_KEY,)
    ).fetchone()
    if not row:
        return None
    return json.loads(row[0]).get("openAIBaseUrl")


def env_base_url() -> str | None:
    if not ENV_FILE.is_file():
        return None
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip().replace("\r", "")
        if line.startswith("CURSOR_BASE_URL="):
            return line.split("=", 1)[1].strip()
    return None


def read_public_url() -> str | None:
    if URL_FILE.is_file():
        url = URL_FILE.read_text(encoding="utf-8").strip().replace("\r", "")
        if url.startswith("https://") and url.endswith("/v1"):
            return url
    env_url = env_base_url()
    if env_url and env_url.startswith("https://") and env_url.endswith("/v1"):
        return env_url
    # 从容器日志解析
    r = subprocess.run(
        ["docker", "logs", "--tail", "80", CONTAINER],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return None
    for m in re.finditer(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", r.stdout or ""):
        host = m.group(0)
        if "api.trycloudflare" in host:
            continue
        return f"{host.rstrip('/')}/v1"
    return None


def wait_for_url(timeout: int = 90) -> str:
    for _ in range(timeout):
        url = read_public_url()
        if url:
            return url
        time.sleep(1)
    sys.exit(f"超时：未在 {URL_FILE} 或容器日志中找到隧道 URL")


def _read_cursor_api_key() -> str:
    if not DB.is_file():
        return ""
    try:
        conn = sqlite3.connect(DB)
        row = conn.execute(
            "SELECT value FROM ItemTable WHERE key = ?",
            ("cursorAuth/openAIKey",),
        ).fetchone()
        conn.close()
        if row and row[0] and not str(row[0]).startswith("sk-your"):
            return str(row[0]).strip()
    except sqlite3.Error:
        pass
    return ""


def update_env(url: str) -> None:
    example = PROJECT_ROOT / "config" / "env.example"
    base_env: dict[str, str] = {}
    if example.is_file():
        for raw in example.read_text(encoding="utf-8").splitlines():
            line = raw.strip().replace("\r", "")
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            base_env[k.strip()] = v.strip()
    if ENV_FILE.is_file():
        for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = raw.strip().replace("\r", "")
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            base_env[k.strip()] = v.strip().strip('"').strip("'")
    base_env["CURSOR_BASE_URL"] = url
    if not base_env.get("DEEPSEEK_API_KEY") or base_env["DEEPSEEK_API_KEY"].startswith("sk-your"):
        recovered = _read_cursor_api_key()
        if recovered:
            base_env["DEEPSEEK_API_KEY"] = recovered
    order = (
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_BASE_URL",
        "DEEPSEEK_MODEL",
        "CURSOR_BASE_URL",
    )
    lines: list[str] = [
        "# Cursor × DeepSeek V4 — 由 sync 自动维护，请勿删除 DEEPSEEK_API_KEY",
        "",
    ]
    seen: set[str] = set()
    for key in order:
        if key in base_env and base_env[key]:
            lines.append(f"{key}={base_env[key]}")
            seen.add(key)
    for key, val in base_env.items():
        if key not in seen and val:
            lines.append(f"{key}={val}")
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        os.chmod(ENV_FILE, 0o600)
    except OSError:
        pass


def apply_cursor() -> int:
    return subprocess.run([sys.executable, str(APPLY_PY)], check=False).returncode


def sync(*, wait: bool, check_only: bool, quit_app: bool, launch: bool) -> int:
    url = wait_for_url() if wait else read_public_url()
    if not url:
        print("未找到公网 URL。请先运行: bash scripts/deploy.sh", file=sys.stderr)
        return 1

    old_env = env_base_url()
    old_db = db_base_url()
    print(f"隧道 URL: {url}")
    if old_env and old_env != url:
        print(f".env  旧: {old_env}")
    if old_db and old_db != url:
        print(f"Cursor 旧: {old_db}")

    already_synced = url == old_env == old_db

    if check_only:
        if already_synced:
            print("已与 Cursor 一致。")
            return 0
        print("需要同步（去掉 --check-only 执行写入）")
        return 2

    if not already_synced:
        update_env(url)
        URL_FILE.write_text(url + "\n", encoding="utf-8")
        print("已更新 .env")

        if cursor_running():
            if quit_app:
                print("正在退出 Cursor…")
                quit_cursor()
            if cursor_running():
                print("请 Cmd+Q 完全退出 Cursor 后执行:", file=sys.stderr)
                print(f"  python3 {__file__}", file=sys.stderr)
                return 1

        os.environ["CURSOR_BASE_URL"] = url
        rc = apply_cursor()
        if rc != 0:
            return rc
        print("Cursor 配置已同步。")
    else:
        print("已与 Cursor 一致，跳过写入。")

    if launch:
        launch_cursor()
    elif not already_synced:
        print("请打开 Cursor，选择 deepseek-v4-pro 或 deepseek-v4-flash。")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="同步 Docker 隧道 URL 到 Cursor")
    p.add_argument("--wait", action="store_true", help="等待 public-url.txt 出现")
    p.add_argument("--check-only", action="store_true", help="仅检查是否一致")
    p.add_argument("--no-quit", action="store_true", help="不自动退出 Cursor")
    p.add_argument("--launch", action="store_true", help="同步完成后启动 Cursor")
    p.add_argument("--no-launch", action="store_true", help="不自动启动 Cursor")
    args = p.parse_args()
    launch = args.launch and not args.no_launch
    return sync(
        wait=args.wait,
        check_only=args.check_only,
        quit_app=not args.no_quit,
        launch=launch,
    )


if __name__ == "__main__":
    raise SystemExit(main())
