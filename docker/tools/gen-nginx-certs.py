#!/usr/bin/env python3
"""生成本地 HTTPS 证书（含 127.0.0.1 与本机局域网 IP）。"""
from __future__ import annotations

import ipaddress
import socket
import subprocess
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "nginx" / "certs"


def is_usable_lan(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if addr.is_loopback or not addr.is_private:
        return False
    # Clash 等 VPN 常用的 fake-ip 段，不能给 Cursor 当 LAN 地址
    if addr in ipaddress.ip_network("198.18.0.0/15"):
        return False
    return True


def lan_ips() -> list[str]:
    ips: list[str] = ["127.0.0.1"]
    import platform
    import subprocess

    if platform.system() == "Darwin":
        for iface in ("en0", "en1", "en2", "bridge0"):
            r = subprocess.run(
                ["ipconfig", "getifaddr", iface],
                capture_output=True,
                text=True,
            )
            ip = (r.stdout or "").strip()
            if is_usable_lan(ip) and ip not in ips:
                ips.append(ip)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if is_usable_lan(ip) and ip not in ips:
                ips.append(ip)
    except OSError:
        pass
    return ips


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cert = OUT / "cert.pem"
    key = OUT / "key.pem"
    sans = []
    for ip in lan_ips():
        try:
            ipaddress.ip_address(ip)
            sans.append(f"IP:{ip}")
        except ValueError:
            pass
    sans.extend(["DNS:localhost", "DNS:host.docker.internal"])
    subj = "/CN=cursor-deepseek-local"
    cmd = [
        "openssl",
        "req",
        "-x509",
        "-nodes",
        "-days",
        "3650",
        "-newkey",
        "rsa:2048",
        "-keyout",
        str(key),
        "-out",
        str(cert),
        "-subj",
        subj,
        "-addext",
        f"subjectAltName={','.join(sans)}",
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except FileNotFoundError:
        sys.exit("需要 openssl，macOS 一般已自带")
    except subprocess.CalledProcessError as e:
        sys.exit(e.stderr.decode() or str(e))
    print(f"证书已写入 {OUT}")
    for ip in lan_ips():
        print(f"  可尝试 Base URL: https://{ip}:8443/v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
