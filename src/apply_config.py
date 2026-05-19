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

# Cursor 下拉中同时注册；默认模型由 .env 的 DEEPSEEK_MODEL 决定
SUPPORTED_MODELS = ("deepseek-v4-pro", "deepseek-v4-flash")
DEFAULT_MODEL = "deepseek-v4-pro"

# API model id → Cursor 界面显示名（与 GPT/Claude 等品牌大小写一致）
MODEL_DISPLAY_NAMES: dict[str, str] = {
    "deepseek-v4-pro": "DeepSeek V4 Pro",
    "deepseek-v4-flash": "DeepSeek V4 Flash",
}


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


def _display_name(model_id: str) -> str:
    return MODEL_DISPLAY_NAMES.get(model_id, model_id)


def _apply_display_names(entry: dict, model_id: str) -> None:
    """界面显示 DeepSeek 品牌名；name/serverModelName 保持 API id。"""
    label = _display_name(model_id)
    entry["name"] = model_id
    entry["serverModelName"] = model_id
    entry["clientDisplayName"] = label
    entry["inputboxShortModelName"] = label
    entry["displayNameOutsidePicker"] = label
    entry["isUserAdded"] = True


def _model_catalog_entry(model_id: str, template: dict | None = None) -> dict:
    """Cursor 模型下拉读取 availableDefaultModels2，仅写 userAddedModels 不会出现 Flash。"""
    if template:
        entry = dict(template)
        # 避免从模板带入旧 displayName / variants
        entry.pop("variants", None)
        entry["variants"] = []
    else:
        entry = {
            "defaultOn": False,
            "parameterDefinitions": [],
            "variants": [],
            "legacySlugs": [],
            "idAliases": [],
            "supportsAgent": True,
            "degradationStatus": 0,
            "supportsThinking": True,
            "supportsImages": True,
            "supportsMaxMode": True,
            "supportsNonMaxMode": True,
            "isRecommendedForBackgroundComposer": False,
            "supportsPlanMode": True,
            "supportsSandboxing": True,
            "namedModelSectionIndex": 1,
        }
    _apply_display_names(entry, model_id)
    return entry


def register_models(data: dict, ai_settings: dict, model_ids: tuple[str, ...]) -> None:
    user_models = list(ai_settings.get("userAddedModels") or [])
    for mid in model_ids:
        if mid not in user_models:
            user_models.append(mid)
    ai_settings["userAddedModels"] = user_models

    enabled = list(ai_settings.get("modelOverrideEnabled") or [])
    for mid in model_ids:
        if mid not in enabled:
            enabled.append(mid)
    ai_settings["modelOverrideEnabled"] = enabled

    catalog = list(data.get("availableDefaultModels2") or [])
    by_name = {
        m.get("name"): m
        for m in catalog
        if isinstance(m, dict) and m.get("name")
    }
    template = by_name.get("deepseek-v4-pro") or by_name.get(model_ids[0])
    for mid in model_ids:
        if mid in by_name:
            _apply_display_names(by_name[mid], mid)
            continue
        catalog.append(_model_catalog_entry(mid, template if isinstance(template, dict) else None))
    data["availableDefaultModels2"] = catalog


def patch_application_user(data: dict, base_url: str, model_id: str) -> dict:
    data["openAIBaseUrl"] = base_url.rstrip("/")
    data["useOpenAIKey"] = True

    ai_settings = data.setdefault("aiSettings", {})
    register_models(data, ai_settings, SUPPORTED_MODELS)
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
    model_id = env.get("DEEPSEEK_MODEL", DEFAULT_MODEL).strip()
    if model_id not in SUPPORTED_MODELS:
        print(
            f"警告：DEEPSEEK_MODEL={model_id!r} 不在支持列表 {list(SUPPORTED_MODELS)}，"
            f"将使用 {DEFAULT_MODEL}。",
            file=sys.stderr,
        )
        model_id = DEFAULT_MODEL
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
    others = [m for m in SUPPORTED_MODELS if m != model_id]
    labels = [_display_name(m) for m in SUPPORTED_MODELS]
    print(f"请重新打开 Cursor → 默认: {_display_name(model_id)}")
    print(f"  模型下拉应可见: {', '.join(labels)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
