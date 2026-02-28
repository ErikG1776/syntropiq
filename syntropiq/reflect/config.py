from __future__ import annotations

import os


def get_reflect_mode() -> str:
    mode = (os.getenv("REFLECT_MODE") or "off").strip().lower()
    if mode in {"off", "score", "integrate"}:
        return mode
    return "off"


def get_reflect_consensus_mode() -> str:
    mode = (os.getenv("REFLECT_CONSENSUS_MODE") or "off").strip().lower()
    if mode in {"off", "log", "integrate"}:
        return mode
    return "off"
