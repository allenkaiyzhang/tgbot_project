"""Project configuration loaded from OS environment and optional .env file.

Load priority:
1) OS environment variables
2) Local .env file
3) In-file placeholder defaults
"""

from __future__ import annotations

import os
from typing import Callable

from longbridge.openapi import Config, OAuthBuilder


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


def _resolve_bool(key: str, default: bool, dotenv: dict[str, str]) -> bool:
    """Resolve boolean setting from env/.env with common true/false strings."""

    raw = _resolve(key, "true" if default else "false", dotenv).strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


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
    # ChatGPT-compatible gateway settings (OpenAI format).
    "CHATGPT_API_KEY": "",
    "CHATGPT_BASE_URL": "https://burn.hair/v1",
    "CHATGPT_MODEL": "gpt-5.2",
    # Whether LongBridge SDK should print quote package table on connect.
    "LONGBRIDGE_PRINT_QUOTE_PACKAGES": "false",
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

# ChatGPT-compatible gateway settings.
CHATGPT_API_KEY = _resolve("CHATGPT_API_KEY", _DEFAULTS["CHATGPT_API_KEY"], _DOTENV)
CHATGPT_BASE_URL = _resolve("CHATGPT_BASE_URL", _DEFAULTS["CHATGPT_BASE_URL"], _DOTENV)
CHATGPT_MODEL = _resolve("CHATGPT_MODEL", _DEFAULTS["CHATGPT_MODEL"], _DOTENV)
LONGBRIDGE_PRINT_QUOTE_PACKAGES = _resolve_bool(
    "LONGBRIDGE_PRINT_QUOTE_PACKAGES",
    False,
    _DOTENV,
)

# Other app defaults.
DEFAULT_SYMBOLS = ["QQQ.US"]


# LongBridge auth/config helpers.
AuthUrlHandler = Callable[[str], None]


def _default_auth_url_handler(url: str) -> None:
    """Default callback for OAuth URL."""

    print(f"Open this URL to authorize: {url}")


def build_oauth_config(
    client_id: str | None = None,
    on_auth_url: AuthUrlHandler | None = None,
) -> Config:
    """Build LongBridge Config from OAuth flow."""

    resolved_client_id = client_id or LONGBRIDGE_CLIENT_ID
    handler = on_auth_url or _default_auth_url_handler
    oauth = OAuthBuilder(resolved_client_id).build(handler)
    return Config.from_oauth(
        oauth,
        enable_print_quote_packages=LONGBRIDGE_PRINT_QUOTE_PACKAGES,
    )


def build_apikey_env_config() -> Config:
    """Build LongBridge Config from LONGPORT_* or equivalent env vars."""

    # Force SDK quote-package table output behavior from project config.
    os.environ["LONGBRIDGE_PRINT_QUOTE_PACKAGES"] = (
        "true" if LONGBRIDGE_PRINT_QUOTE_PACKAGES else "false"
    )
    return Config.from_apikey_env()


def build_config_with_fallback(
    client_id: str | None = None,
    on_auth_url: AuthUrlHandler | None = None,
) -> tuple[Config, str]:
    """Try OAuth first, fallback to from_apikey_env() when OAuth fails."""

    try:
        return build_oauth_config(client_id=client_id, on_auth_url=on_auth_url), "oauth"
    except Exception as oauth_error:
        print(f"OAuth config failed, fallback to from_apikey_env(): {oauth_error}")
        return build_apikey_env_config(), "apikey_env"


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
    "CHATGPT_API_KEY",
    "CHATGPT_BASE_URL",
    "CHATGPT_MODEL",
    "LONGBRIDGE_PRINT_QUOTE_PACKAGES",
    "DEFAULT_SYMBOLS",
    "build_oauth_config",
    "build_apikey_env_config",
    "build_config_with_fallback",
]
