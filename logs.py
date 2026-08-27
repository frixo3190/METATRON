#!/usr/bin/env python3
"""
METATRON - logs.py
Simple log hook: lets the Textual TUI capture the progress/status lines that
were previously written to stdout. Defaults to print() so the legacy CLI is
unchanged.
"""

import re

_log_fn = None


def emit(message: str) -> None:
    """Émet une ligne de progression/statut (vers le hook TUI ou print)."""
    if _log_fn is not None:
        _log_fn(message)
    else:
        print(message)


def set_log(fn) -> None:
    """Définit le callback qui reçoit les messages émis (None → retour à print)."""
    global _log_fn
    _log_fn = fn


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

def strip_ansi(text: str) -> str:
    """Retire les séquences de couleur ANSI d'un texte."""
    return _ANSI_RE.sub("", text)
