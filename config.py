"""Project configuration loaded from OS environment, .env, and app_texts.json."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

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


def _load_app_texts(path: str = "app_texts.json") -> dict[str, Any]:
    """Load app-level fixed texts/templates from JSON file."""

    text_path = Path(path)
    if not text_path.exists():
        raise FileNotFoundError(f"Missing required text config file: {path}")

    with text_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError("app_texts.json must be a JSON object")
    return data


def get_text(key: str) -> Any:
    """Read nested key from APP_TEXTS by dot path, e.g. 'bot.help_text'."""

    current: Any = APP_TEXTS
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(f"Missing required text key: {key}")
        current = current[part]
    return current


def _split_csv(value: str) -> list[str]:
    """Split comma-separated string into a stripped list."""

    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _resolve(key: str, dotenv: dict[str, str]) -> str:
    """Resolve setting value by priority: os env > .env > empty string."""

    value = os.getenv(key)
    if value is not None:
        return value
    return dotenv.get(key, "")


def _resolve_bool(key: str, dotenv: dict[str, str]) -> bool:
    """Resolve boolean setting from env/.env with common true/false strings."""

    raw = _resolve(key, dotenv).strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


_DOTENV = _load_dotenv(".env")
APP_TEXTS = _load_app_texts("app_texts.json")

# Core app settings.
TELEGRAM_BOT_TOKEN = _resolve("TELEGRAM_BOT_TOKEN", _DOTENV)
DEEPSEEK_API_KEY = _resolve("DEEPSEEK_API_KEY", _DOTENV)
LONGBRIDGE_CLIENT_ID = _resolve("LONGBRIDGE_CLIENT_ID", _DOTENV)

# Gmail settings.
GMAIL_SENDER = _resolve("GMAIL_SENDER", _DOTENV)
GMAIL_APP_PASSWORD = _resolve("GMAIL_APP_PASSWORD", _DOTENV)
GMAIL_TO = _resolve("GMAIL_TO", _DOTENV)
GMAIL_CC = _resolve("GMAIL_CC", _DOTENV)
GMAIL_TO_LIST = _split_csv(GMAIL_TO)
GMAIL_CC_LIST = _split_csv(GMAIL_CC)

# ChatGPT-compatible gateway settings.
CHATGPT_API_KEY = _resolve("CHATGPT_API_KEY", _DOTENV)
CHATGPT_BASE_URL = _resolve("CHATGPT_BASE_URL", _DOTENV)
CHATGPT_MODEL = _resolve("CHATGPT_MODEL", _DOTENV)
LONGBRIDGE_PRINT_QUOTE_PACKAGES = _resolve_bool("LONGBRIDGE_PRINT_QUOTE_PACKAGES", _DOTENV)

# Other app settings.
SYMBOLS = list(get_text("config.symbols"))


# LongBridge auth/config helpers.
AuthUrlHandler = Callable[[str], None]


def _auth_url_handler(url: str) -> None:
    """Callback for OAuth URL."""

    print(get_text("config.oauth_open_url_template").format(url=url))


def build_oauth_config(
    client_id: str | None = None,
    on_auth_url: AuthUrlHandler | None = None,
) -> Config:
    """Build LongBridge Config from OAuth flow."""

    resolved_client_id = client_id or LONGBRIDGE_CLIENT_ID
    handler = on_auth_url or _auth_url_handler
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
        print(get_text("config.oauth_fallback_log").format(error=oauth_error))
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
    "SYMBOLS",
    "APP_TEXTS",
    "get_text",
    "build_oauth_config",
    "build_apikey_env_config",
    "build_config_with_fallback",
]
