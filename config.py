"""Centralized runtime config loaded from env vars and .env."""

import os


def _load_dotenv(path: str = ".env") -> dict[str, str]:
    """Load KEY=VALUE entries from a local .env file."""

    if not os.path.exists(path):
        return {}

    env: dict[str, str] = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            env[key.strip()] = val.strip().strip('"').strip("'")
    return env


def _split_csv(value: str) -> list[str]:
    """Split comma-separated env values into a clean list."""

    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


# Placeholder defaults (env vars or .env should override these).
_DEFAULT_TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN"
_DEFAULT_DEEPSEEK_API_KEY = "YOUR_DEEPSEEK_API_KEY"
_DEFAULT_LONGBRIDGE_CLIENT_ID = "YOUR_LONGBRIDGE_CLIENT_ID"
_DEFAULT_GMAIL_SENDER = "YOUR_GMAIL_ADDRESS"
_DEFAULT_GMAIL_APP_PASSWORD = "YOUR_GMAIL_APP_PASSWORD"
_DEFAULT_GMAIL_TO = ""
_DEFAULT_GMAIL_CC = ""

_dotenv = _load_dotenv(".env")

# Priority: OS env > .env > placeholder default
TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    _dotenv.get("TELEGRAM_BOT_TOKEN", _DEFAULT_TELEGRAM_BOT_TOKEN),
)
DEEPSEEK_API_KEY = os.getenv(
    "DEEPSEEK_API_KEY",
    _dotenv.get("DEEPSEEK_API_KEY", _DEFAULT_DEEPSEEK_API_KEY),
)
LONGBRIDGE_CLIENT_ID = os.getenv(
    "LONGBRIDGE_CLIENT_ID",
    _dotenv.get("LONGBRIDGE_CLIENT_ID", _DEFAULT_LONGBRIDGE_CLIENT_ID),
)
GMAIL_SENDER = os.getenv(
    "GMAIL_SENDER",
    _dotenv.get("GMAIL_SENDER", _DEFAULT_GMAIL_SENDER),
)
GMAIL_APP_PASSWORD = os.getenv(
    "GMAIL_APP_PASSWORD",
    _dotenv.get("GMAIL_APP_PASSWORD", _DEFAULT_GMAIL_APP_PASSWORD),
)
GMAIL_TO = os.getenv(
    "GMAIL_TO",
    _dotenv.get("GMAIL_TO", _DEFAULT_GMAIL_TO),
)
GMAIL_CC = os.getenv(
    "GMAIL_CC",
    _dotenv.get("GMAIL_CC", _DEFAULT_GMAIL_CC),
)

GMAIL_TO_LIST = _split_csv(GMAIL_TO)
GMAIL_CC_LIST = _split_csv(GMAIL_CC)

DEFAULT_SYMBOLS = ["VIX.US"]
