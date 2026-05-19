#!/usr/bin/env python3
"""将 .env 中的配置写入 Cursor 的 BYOK 设置。请先完全退出 Cursor（Cmd+Q）再运行。

用法:
  python3 src/apply_config.py                    # 使用项目根目录 .env
  python3 src/apply_config.py --env /path/.env   # 指定 .env 路径
  CURSOR_BASE_URL=... python3 src/apply_config.py  # 从环境变量读取
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = Path(os.environ.get("ENV_FILE", str(PROJECT_ROOT / ".env")))
_default_db = Path.home() / "Library/Application Support/Cursor/User/globalStorage/state.vscdb"
CURSOR_DB = Path(os.environ.get("CURSOR_DB", str(_default_db)))
APP_USER_KEY = (
    "src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl"
    ".persistentStorage.applicationUser"
)
OPENAI_KEY_STORAGE = "cursorAuth/openAIKey"

AGENT_MODES = (
    "composer",
    "quick-agent",
    "cmd-k",
    "background-composer",
    "plan-execution",
)


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.is_file():
        raise FileNotFoundError(f"未找到 {path}，请先创建并填写 API Key")
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip().replace("\r", "")
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def cursor_running() -> bool:
    try:
        import subprocess

        result = subprocess.run(
            ["pgrep", "-x", "Cursor"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def set_default_model(ai_settings: dict, model_id: str) -> None:
    model_config = ai_settings.setdefault("modelConfig", {})
    selected = [{"modelId": model_id, "parameters": []}]
    for mode in AGENT_MODES:
        if mode not in model_config:
            continue
        model_config[mode]["modelName"] = model_id
        model_config[mode]["selectedModels"] = selected
    ai_settings["composerModel"] = model_id
    ai_settings["cmdKModel"] = model_id
    ai_settings["backgroundComposerModel"] = model_id


def patch_application_user(data: dict, base_url: str, model_id: str) -> dict:
    data["openAIBaseUrl"] = base_url.rstrip("/")
    data["useOpenAIKey"] = True

    ai_settings = data.setdefault("aiSettings", {})
    user_models = list(ai_settings.get("userAddedModels") or [])
    if model_id not in user_models:
        user_models.append(model_id)
    ai_settings["userAddedModels"] = user_models

    enabled = list(ai_settings.get("modelOverrideEnabled") or [])
    if model_id not in enabled:
        enabled.append(model_id)
    ai_settings["modelOverrideEnabled"] = enabled

    set_default_model(ai_settings, model_id)
    return data


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="将 .env 写入 Cursor BYOK 配置")
    p.add_argument("--env", help="指定 .env 文件路径", default=None)
    args = p.parse_args()

    env_file = Path(args.env) if args.env else ENV_FILE
    env = load_env(env_file)
    api_key = env.get("DEEPSEEK_API_KEY", "")
    model_id = env.get("DEEPSEEK_MODEL", "deepseek-v4-pro")
    cursor_base = env.get("CURSOR_BASE_URL", "").strip().rstrip("/")
    direct_base = env.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip().rstrip("/")

    # 环境变量优先（CURSOR_BASE_URL 可由 setup.sh 传入）
    if os.environ.get("CURSOR_BASE_URL"):
        cursor_base = os.environ["CURSOR_BASE_URL"].strip().rstrip("/")

    if cursor_base:
        base_url = cursor_base
    else:
        base_url = direct_base
        print(
            "警告：未设置 CURSOR_BASE_URL，仍指向 DeepSeek 官方。\n"
            "Agent 多轮会报 reasoning_content 错误，请先运行 redeploy.sh。",
            file=sys.stderr,
        )

    if not api_key or api_key.startswith("sk-your"):
        print("请先在 .env 中填写有效的 DEEPSEEK_API_KEY，然后重新运行。", file=sys.stderr)
        return 1

    if "api.deepseek.com" in base_url.lower():
        print(
            "错误：CURSOR_BASE_URL 不能是 api.deepseek.com。\n"
            "请先运行: bash deploy.sh 启动代理和隧道。",
            file=sys.stderr,
        )
        return 1

    if not CURSOR_DB.is_file():
        print(f"未找到 Cursor 数据库：{CURSOR_DB}", file=sys.stderr)
        return 1

    if cursor_running():
        print("检测到 Cursor 仍在运行。请先 Cmd+Q 完全退出，再执行本脚本。", file=sys.stderr)
        return 1

    try:
        os.chmod(ENV_FILE, 0o600)
    except OSError:
        pass

    conn = sqlite3.connect(CURSOR_DB)
    try:
        row = conn.execute(
            "SELECT value FROM ItemTable WHERE key = ?",
            (APP_USER_KEY,),
        ).fetchone()
        if not row:
            print(f"未找到 Cursor 配置项：{APP_USER_KEY}", file=sys.stderr)
            return 1

        app_user = json.loads(row[0])
        app_user = patch_application_user(app_user, base_url, model_id)
        conn.execute(
            "INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
            (APP_USER_KEY, json.dumps(app_user, separators=(",", ":"))),
        )
        conn.execute(
            "INSERT OR REPLACE INTO ItemTable (key, value) VALUES (?, ?)",
            (OPENAI_KEY_STORAGE, api_key),
        )
        conn.commit()
    finally:
        conn.close()

    print("配置已写入 Cursor。")
    print(f"  Base URL : {base_url}")
    print(f"  Model    : {model_id}")
    print(f"  API Key  : {api_key[:8]}...{api_key[-4:]}")
    print()
    print("请重新打开 Cursor → 聊天窗口左上角选择", model_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
