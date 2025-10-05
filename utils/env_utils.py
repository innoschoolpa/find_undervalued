"""Environment helper utilities shared across modules."""

from __future__ import annotations

import logging
import os
from typing import Optional


def safe_env_int(key: str, default: int, min_val: Optional[int] = None) -> int:
    try:
        value = int(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        value = default
    if min_val is None:
        return value
    return max(min_val, value)


def safe_env_float(key: str, default: float, min_val: float = 0.0) -> float:
    try:
        value = float(os.getenv(key, str(default)))
        return max(min_val, value)
    except (ValueError, TypeError):
        return max(min_val, default)


def safe_env_bool(key: str, default: bool = False) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def safe_env_ms_to_seconds(key: str, default_ms: float, min_ms: float = 0.0) -> float:
    try:
        ms = float(os.getenv(key, str(default_ms)))
        ms = max(min_ms, ms)
    except (ValueError, TypeError):
        ms = max(min_ms, default_ms)
    return ms / 1000.0


# Global cache used by the analyzer; populated elsewhere.
_ENV_CACHE = {
    'current_ratio_ambiguous_strategy': os.getenv("CURRENT_RATIO_AMBIGUOUS_STRATEGY", "as_is"),
    'current_ratio_force_percent': os.getenv("CURRENT_RATIO_FORCE_PERCENT", "false"),
}


def _refresh_env_cache():
    logging.debug("[env] Cache refresh triggered")
    _ENV_CACHE.update({
        'current_ratio_ambiguous_strategy': os.getenv("CURRENT_RATIO_AMBIGUOUS_STRATEGY", "as_is"),
        'current_ratio_force_percent': os.getenv("CURRENT_RATIO_FORCE_PERCENT", "false"),
    })

