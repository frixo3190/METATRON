#!/usr/bin/env python3
"""
METATRON - prompts.py
Charge les prompts depuis config/prompt.json (externalisés).
"""

import json
import os

PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "config", "prompt.json"
)

_cache = None


def load_prompts() -> dict:
    """Retourne le contenu de config/prompt.json (ou {} si absent)."""
    global _cache
    if _cache is not None:
        return _cache
    try:
        with open(PROMPT_PATH, "r", encoding="utf-8") as f:
            _cache = json.load(f)
    except Exception:
        _cache = {}
    return _cache


def get(key: str, default: str = "") -> str:
    return load_prompts().get(key, default)
