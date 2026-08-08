#!/usr/bin/env python3
"""
LLM configuration and OpenAI-compatible API calls.

Configuration is read from a local .env file in the project root:
  LLM_API_KEY=sk-xxxx
  LLM_BASE_URL=https://api.deepseek.com/v1
  LLM_MODEL=deepseek-chat

Command-line arguments (passed to generate_summary) override .env values.
"""

import json
import os
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
DEFAULT_MODEL = "deepseek-chat"


def load_env() -> None:
    """Load .env file if present. Fallback to a tiny parser if python-dotenv is missing."""
    if not ENV_PATH.exists():
        return
    try:
        from dotenv import load_dotenv

        load_dotenv(ENV_PATH)
    except ImportError:
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value:
                os.environ.setdefault(key, value)


def get_config(api_key: str = "", base_url: str = "", model: str = "") -> dict:
    """Merge .env and CLI overrides. Returns None-ish keys as empty strings."""
    load_env()
    return {
        "api_key": api_key or os.environ.get("LLM_API_KEY", ""),
        "base_url": base_url or os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL),
        "model": model or os.environ.get("LLM_MODEL", DEFAULT_MODEL),
    }


def is_configured(config: dict) -> bool:
    """Return True when an API key is available."""
    return bool(config.get("api_key", "").strip())


def generate_summary(prompt: str, config: dict, timeout: int = 120) -> str:
    """Call an OpenAI-compatible chat completions endpoint. Returns the reply text."""
    if not is_configured(config):
        raise RuntimeError("LLM not configured: set LLM_API_KEY in .env")

    base_url = config["base_url"].rstrip("/")
    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config["model"],
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": 0.3,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(f"Unexpected LLM response: {json.dumps(data, ensure_ascii=False)[:500]}")


def print_config_hint() -> None:
    print("\n[提示] 未检测到 LLM_API_KEY，跳过自动总结。")
    print("      当前已生成 summary_prompt.md，可将内容复制给任意 AI 生成总结。")
    print(f"      如需自动总结，请在 {ENV_PATH} 中配置 LLM_API_KEY（参考 .env.example）。")


if __name__ == "__main__":
    load_env()
    cfg = get_config()
    print(f"base_url={cfg['base_url']}")
    print(f"model={cfg['model']}")
    print(f"api_key={'***' if cfg['api_key'] else '(empty)'}")
