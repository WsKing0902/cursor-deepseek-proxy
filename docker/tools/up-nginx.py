#!/usr/bin/env python3
"""
启动 Docker：proxy + nginx(HTTPS:8443)，并提示可在 Cursor 里尝试的 Base URL。

用法:
  python3 ~/deepseek-cursor-docker/up-nginx.py
  python3 ~/deepseek-cursor-docker/up-nginx.py --apply   # Cursor 已 Cmd+Q 时写入 DB
"""
from __future__ import annotations

import argparse
import json
import socket
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

DOCKER_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = DOCKER_DIR.parent
COMPOSE = DOCKER_DIR / "docker-compose.nginx.yml"
GEN_CERTS = DOCKER_DIR / "tools/gen-nginx-certs.py"
ENV_FILE = PROJECT_ROOT / ".env"
DB = Path.home() / "Library/Application Support/Cursor/User/globalStorage/state.vscdb"
APP_KEY = (
    "src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl"
    ".persistentStorage.applicationUser"
)


def lan_ips() -> list[str]:
    import ipaddress
    import platform
    import subprocess

    ips: list[str] = []

    def add(ip: str) -> None:
        try:
            a = ipaddress.ip_address(ip)
        except ValueError:
            return
        if a.is_loopback or not a.is_private:
            return
        if a in ipaddress.ip_network("198.18.0.0/15"):
            return
        if ip not in ips:
            ips.append(ip)

    if platform.system() == "Darwin":
        for iface in ("en0", "en1", "en2"):
            r = subprocess.run(
                ["ipconfig", "getifaddr", iface],
                capture_output=True,
                text=True,
            )
            add((r.stdout or "").strip())
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            add(s.getsockname()[0])
    except OSError:
        pass
    return ips


def candidate_urls() -> list[str]:
    urls = [f"https://{ip}:8443/v1" for ip in lan_ips()]
    urls.extend(
        [
            "https://127.0.0.1:8443/v1",
            "https://localhost:8443/v1",
        ]
    )
    return urls


def probe(url: str, key: str) -> bool:
    req = urllib.request.Request(
        f"{url.rstrip('/')}/models",
        headers={"Authorization": f"Bearer {key}"},
    )
    ctx = __import__("ssl")._create_unverified_context()
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(context=ctx),
    )
    try:
        with opener.open(req, timeout=8) as r:
            return r.status == 200
    except Exception:
        return False


def load_key() -> str:
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip().replace("\r", "")
        if line.startswith("DEEPSEEK_API_KEY="):
            return line.split("=", 1)[1].strip()
    sys.exit(f"请配置 {ENV_FILE}")


def apply_db(url: str, key: str) -> None:
    conn = sqlite3.connect(DB)
    data = json.loads(
        conn.execute("SELECT value FROM ItemTable WHERE key=?", (APP_KEY,)).fetchone()[0]
    )
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
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    out = [
        (f"CURSOR_BASE_URL={url}" if l.startswith("CURSOR_BASE_URL=") else l)
        for l in lines
    ]
    if not any(l.startswith("CURSOR_BASE_URL=") for l in out):
        out.append(f"CURSOR_BASE_URL={url}")
    ENV_FILE.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true", help="写入 Cursor DB（需先退出 Cursor）")
    args = p.parse_args()

    subprocess.run([sys.executable, str(GEN_CERTS)], check=True)
    subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE), "up", "-d", "--build"],
        cwd=DOCKER_DIR,
        check=True,
    )

    key = load_key()
    print()
    print("Docker 已启动: proxy(内网) + nginx → 主机 :8443 (HTTPS)")
    print()
    print("重要：nginx 只是把 HTTP 包一层 TLS，不能绕过 Cursor 对 127.0.0.1 的 SSRF。")
    print("若 Cursor 仍报错，仍需 cloudflared/ngrok 公网地址。")
    print()
    working: list[str] = []
    for url in candidate_urls():
        ok = probe(url, key)
        mark = "✓" if ok else "✗"
        print(f"  [{mark}] {url}")
        if ok:
            working.append(url)
    print()
    if not working:
        print("本机 curl 未通过（自签证书或 Cursor 限制）。可在终端试:")
        print(f"  curl -k {candidate_urls()[0]}/models -H 'Authorization: Bearer <key>'")
        return 0
    best = working[0]
    print(f"建议先在 Cursor Settings 填: {best}")
    if args.apply:
        if subprocess.run(["pgrep", "-x", "Cursor"], capture_output=True).returncode == 0:
            print("请先 Cmd+Q 退出 Cursor，再运行: python3 up-nginx.py --apply")
            return 1
        apply_db(best, key)
        print(f"已写入 Cursor DB: {best}")
    else:
        print("写入 DB: python3 ~/deepseek-cursor-docker/up-nginx.py --apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
