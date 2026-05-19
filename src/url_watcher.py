#!/usr/bin/env python3
"""
隧道 URL 自动监视：发现 public-url.txt 与 .env / Cursor 不一致时触发同步。

- Docker 容器内（--daemon）：轮询 /data/public-url.txt，更新 .env，并写入 need-sync 标记
- macOS 宿主机（--host-bridge）：读取 need-sync，执行完整 sync（退出 Cursor + 写库）

由 docker-compose 的 url-sync 服务与 up.sh 自动启动。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

# 允许从 src/ 目录导入
_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import sync_cursor as sc  # noqa: E402

APPLY_PY = sc.APPLY_PY

NEED_SYNC_FILE = Path(
    os.environ.get("NEED_SYNC_FILE", str(sc.PROJECT_ROOT / "docker/data/need-sync"))
)
DEFAULT_INTERVAL = int(os.environ.get("WATCH_INTERVAL", "5"))


def normalize(url: str | None) -> str | None:
    if not url:
        return None
    u = url.strip().replace("\r", "").rstrip("/")
    if u.endswith("/v1"):
        return u
    if u.startswith("https://"):
        return f"{u}/v1" if not u.endswith("/v1") else u
    return u


def current_tunnel_url() -> str | None:
    if sc.URL_FILE.is_file():
        url = normalize(sc.URL_FILE.read_text(encoding="utf-8"))
        if url:
            return url
    return normalize(sc.read_public_url())


def is_out_of_sync(url: str) -> bool:
    env_u = normalize(sc.env_base_url())
    db_u = normalize(sc.db_base_url())
    return url != env_u or url != db_u


def mark_need_sync(url: str) -> None:
    NEED_SYNC_FILE.parent.mkdir(parents=True, exist_ok=True)
    NEED_SYNC_FILE.write_text(url + "\n", encoding="utf-8")


def clear_need_sync() -> None:
    if NEED_SYNC_FILE.is_file():
        NEED_SYNC_FILE.unlink()


def container_daemon(interval: int) -> int:
    print(f"[url-sync] 容器监视启动，间隔 {interval}s", flush=True)
    print(f"[url-sync] 监视: {sc.URL_FILE}", flush=True)
    last = ""
    while True:
        try:
            url = current_tunnel_url()
            if url and url != last:
                print(f"[url-sync] 隧道 URL: {url}", flush=True)
                last = url
            if url and is_out_of_sync(url):
                print("[url-sync] 检测到不一致，更新 .env 并请求宿主机同步…", flush=True)
                sc.update_env(url)
                sc.URL_FILE.write_text(url + "\n", encoding="utf-8")
                mark_need_sync(url)
        except Exception as e:
            print(f"[url-sync] 错误: {e}", flush=True)
        time.sleep(interval)


def maybe_fix_model_labels() -> None:
    """Cursor 运行时会从 /v1/models 刷新并把小写 id 写回；退出后补 DeepSeek 显示名。"""
    if sc.cursor_running():
        return
    subprocess.run(
        [sys.executable, str(APPLY_PY), "--labels-only"],
        cwd=str(sc.PROJECT_ROOT),
        capture_output=True,
        text=True,
    )


def host_bridge(interval: int, launch: bool) -> int:
    if sys.platform != "darwin":
        print("host-bridge 仅用于 macOS 宿主机", file=sys.stderr)
        return 1
    print(f"[url-sync] 宿主机桥接启动，间隔 {interval}s", flush=True)
    while True:
        try:
            url = None
            if NEED_SYNC_FILE.is_file():
                url = normalize(NEED_SYNC_FILE.read_text(encoding="utf-8"))
            if not url:
                url = current_tunnel_url()
            if url and is_out_of_sync(url):
                print(f"[url-sync] 同步 Cursor → {url}", flush=True)
                os.environ["CURSOR_BASE_URL"] = url
                rc = sc.sync(
                    wait=False,
                    check_only=False,
                    quit_app=True,
                    launch=launch,
                )
                if rc == 0:
                    clear_need_sync()
                    print("[url-sync] 同步完成", flush=True)
                else:
                    print(f"[url-sync] 同步失败 (exit {rc})，稍后重试", flush=True)
            else:
                maybe_fix_model_labels()
        except Exception as e:
            print(f"[url-sync] 错误: {e}", flush=True)
        time.sleep(interval)


def main() -> int:
    p = argparse.ArgumentParser(description="隧道 URL 自动监视")
    p.add_argument("--daemon", action="store_true", help="Docker 容器内监视模式")
    p.add_argument("--host-bridge", action="store_true", help="macOS 宿主机桥接模式")
    p.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help="轮询间隔秒")
    p.add_argument("--launch", action="store_true", help="宿主机同步后打开 Cursor")
    args = p.parse_args()

    if args.host_bridge:
        return host_bridge(args.interval, launch=args.launch)
    if args.daemon:
        return container_daemon(args.interval)
    p.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
