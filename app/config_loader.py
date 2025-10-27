from __future__ import annotations
import os
import re
import json
from typing import Any, Dict


_SIMPLE_YAML_LINE = re.compile(r"^\s*([A-Za-z0-9_.\-]+)\s*:\s*(.*?)\s*$")


def _convert_value(raw_val: str) -> Any:
    """Convert raw string value to bool, number, or string."""
    val = raw_val.strip()
    lower = val.lower()

    if not val:
        return ""
    if lower in {"true", "false"}:
        return lower == "true"
    if (val.startswith('"') and val.endswith('"')) or (
        val.startswith("'") and val.endswith("'")
    ):
        return val[1:-1]
    try:
        return float(val) if "." in val else int(val)
    except ValueError:
        return val


def _parse_simple_yaml(text: str) -> Dict[str, Any]:
    """
    Minimal YAML parser for flat key:value pairs.
    Supports numbers, booleans, and quoted/unquoted strings.
    Ignores blank lines and comments starting with '#'.
    """
    cfg: Dict[str, Any] = {}

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        match = _SIMPLE_YAML_LINE.match(line)
        if not match:
            continue

        key, raw_val = match.groups()
        cfg[key] = _convert_value(raw_val)

    return cfg


def load_config(path: str) -> Dict[str, Any]:
    """Load configuration from JSON or minimal YAML file."""
    if not os.path.isfile(path):
        return {}

    with open(path, encoding="utf-8") as f:
        text = f.read().strip()

    if not text:
        return {}

    if path.endswith(".json"):
        return json.loads(text)

    return _parse_simple_yaml(text)


def get(path_env: str, default_path: str) -> Dict[str, Any]:
    """Load config using environment override if present."""
    return load_config(os.environ.get(path_env, default_path))
