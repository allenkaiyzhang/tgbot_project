"""Project configuration loaded from OS environment and optional .env file.

Load priority:
1) OS environment variables
2) Local .env file
3) In-file placeholder defaults
"""

from __future__ import annotations

import os


def _load_dotenv(path: str = ".env") -> dict[str, str]:
    """Load KEY=VALUE pairs from a .env file."""

    if not os.path.exists(path):
        return {}

    env: dict[str, str] = {}
    with open(path, "r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def _split_csv(value: str) -> list[str]:
    """Split comma-separated string into a stripped list."""

    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _resolve(key: str, default: str, dotenv: dict[str, str]) -> str:
    """Resolve a setting value by priority: os env > .env > default."""

    return os.getenv(key, dotenv.get(key, default))


_DOTENV = _load_dotenv(".env")

# Placeholder defaults.
_DEFAULTS = {
    "TELEGRAM_BOT_TOKEN": "YOUR_BOT_TOKEN",
    "DEEPSEEK_API_KEY": "YOUR_DEEPSEEK_API_KEY",
    "LONGBRIDGE_CLIENT_ID": "YOUR_LONGBRIDGE_CLIENT_ID",
    "GMAIL_SENDER": "YOUR_GMAIL_ADDRESS",
    "GMAIL_APP_PASSWORD": "YOUR_GMAIL_APP_PASSWORD",
    "GMAIL_TO": "",
    "GMAIL_CC": "",
}

# Core app settings.
TELEGRAM_BOT_TOKEN = _resolve("TELEGRAM_BOT_TOKEN", _DEFAULTS["TELEGRAM_BOT_TOKEN"], _DOTENV)
DEEPSEEK_API_KEY = _resolve("DEEPSEEK_API_KEY", _DEFAULTS["DEEPSEEK_API_KEY"], _DOTENV)
LONGBRIDGE_CLIENT_ID = _resolve("LONGBRIDGE_CLIENT_ID", _DEFAULTS["LONGBRIDGE_CLIENT_ID"], _DOTENV)

# Gmail settings.
GMAIL_SENDER = _resolve("GMAIL_SENDER", _DEFAULTS["GMAIL_SENDER"], _DOTENV)
GMAIL_APP_PASSWORD = _resolve("GMAIL_APP_PASSWORD", _DEFAULTS["GMAIL_APP_PASSWORD"], _DOTENV)
GMAIL_TO = _resolve("GMAIL_TO", _DEFAULTS["GMAIL_TO"], _DOTENV)
GMAIL_CC = _resolve("GMAIL_CC", _DEFAULTS["GMAIL_CC"], _DOTENV)
GMAIL_TO_LIST = _split_csv(GMAIL_TO)
GMAIL_CC_LIST = _split_csv(GMAIL_CC)

# Other app defaults.
DEFAULT_SYMBOLS = ["QQQ.US"]


__all__ = [
    "TELEGRAM_BOT_TOKEN",
    "DEEPSEEK_API_KEY",
    "LONGBRIDGE_CLIENT_ID",
    "GMAIL_SENDER",
    "GMAIL_APP_PASSWORD",
    "GMAIL_TO",
    "GMAIL_CC",
    "GMAIL_TO_LIST",
    "GMAIL_CC_LIST",
    "DEFAULT_SYMBOLS",
]
