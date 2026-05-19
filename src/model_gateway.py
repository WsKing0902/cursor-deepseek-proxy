#!/usr/bin/env python3
"""
轻量反向代理：在 /v1/models 响应中为 DeepSeek 模型注入友好显示名。

Cursor 启动时会拉取 BYOK 的 models 列表；若只有小写 id，界面会显示 deepseek-v4-pro。
本网关把 id 保留给 API，同时写入 OpenAI 兼容的 name / owned_by 字段。
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = os.environ.get("MODEL_GATEWAY_UPSTREAM", "http://127.0.0.1:9001").rstrip("/")
LISTEN_HOST = os.environ.get("MODEL_GATEWAY_HOST", "0.0.0.0")
LISTEN_PORT = int(os.environ.get("MODEL_GATEWAY_PORT", "9000"))

MODEL_LABELS: dict[str, str] = {
    "deepseek-v4-pro": "DeepSeek V4 Pro",
    "deepseek-v4-flash": "DeepSeek V4 Flash",
}


def patch_models_payload(raw: bytes) -> bytes:
    try:
        body = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return raw
    items = body.get("data")
    if not isinstance(items, list):
        return raw
    for item in items:
        if not isinstance(item, dict):
            continue
        mid = item.get("id")
        if not isinstance(mid, str):
            continue
        label = MODEL_LABELS.get(mid)
        if label:
            item["name"] = label
            item["owned_by"] = "DeepSeek"
    return json.dumps(body, separators=(",", ":")).encode("utf-8")


class GatewayHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write(f"[model-gateway] {self.address_string()} - {fmt % args}\n")

    def _forward(self, method: str) -> None:
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(length) if length else None
        url = f"{UPSTREAM}{self.path}"
        headers = {k: v for k, v in self.headers.items() if k.lower() != "host"}
        req = urllib.request.Request(url, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=600) as upstream:
                data = upstream.read()
                if method == "GET" and self.path.rstrip("/").endswith("/models"):
                    data = patch_models_payload(data)
                self.send_response(upstream.status)
                for k, v in upstream.headers.items():
                    if k.lower() in ("transfer-encoding", "connection"):
                        continue
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            err_body = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", e.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(err_body)))
            self.end_headers()
            self.wfile.write(err_body)

    def do_GET(self) -> None:
        self._forward("GET")

    def do_POST(self) -> None:
        self._forward("POST")

    def do_PUT(self) -> None:
        self._forward("PUT")

    def do_PATCH(self) -> None:
        self._forward("PATCH")

    def do_DELETE(self) -> None:
        self._forward("DELETE")

    def do_OPTIONS(self) -> None:
        self._forward("OPTIONS")


def main() -> int:
    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), GatewayHandler)
    print(
        f"[model-gateway] listening {LISTEN_HOST}:{LISTEN_PORT} → {UPSTREAM}",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
