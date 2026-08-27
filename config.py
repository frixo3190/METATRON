#!/usr/bin/env python3
"""
METATRON - config.py
Persistent settings (AI provider, OpenRouter API key, selected model).
Stored as JSON in ~/.metatron/config.json (outside the repo).
"""

import json
import os

CONFIG_DIR  = os.path.join(os.path.expanduser("~"), ".metatron")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

DEFAULTS = {
    "provider": "ollama",          # "ollama" | "openrouter"
    "api_key":  "",                # OpenRouter API key
    "model":    "metatron-qwen",   # active model (Ollama name or OpenRouter id)
}


def _ensure_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load_config() -> dict:
    """Read config from disk. Returns defaults merged with saved values."""
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, "r") as f:
            saved = json.load(f)
        if isinstance(saved, dict):
            cfg.update(saved)
    except FileNotFoundError:
        pass
    except (json.JSONDecodeError, OSError):
        pass
    return cfg


def save_config(cfg: dict) -> None:
    """Write config to disk, merging with defaults first."""
    merged = dict(DEFAULTS)
    merged.update(cfg)
    _ensure_dir()
    with open(CONFIG_PATH, "w") as f:
        json.dump(merged, f, indent=2)


def get(key: str, default=None):
    return load_config().get(key, default)


def set(key: str, value) -> None:
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)


def mask_key(key: str) -> str:
    """Mask an API key for display, e.g. sk-or-...c96."""
    if not key:
        return "(none)"
    if len(key) <= 8:
        return key[:2] + "..." + key[-2:]
    return key[:6] + "..." + key[-3:]


if __name__ == "__main__":
    cfg = load_config()
    print(f"Provider : {cfg['provider']}")
    print(f"Model    : {cfg['model']}")
    print(f"API key  : {mask_key(cfg['api_key'])}")
