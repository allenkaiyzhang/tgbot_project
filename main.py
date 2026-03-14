"""Project startup entrypoint.

Current routing:
- default startup target -> bot.telegram_bot.main
"""

from __future__ import annotations

import logging

import config

logger = logging.getLogger(__name__)


def _run_startup_preflight() -> None:
    """Validate startup config and fail fast on blocking issues."""

    errors, warnings = config.validate_startup_config()

    for warning in warnings:
        logger.warning(warning)

    if errors:
        logger.error("Startup preflight failed")
        for error in errors:
            logger.error(" - %s", error)
        raise RuntimeError("Startup preflight failed")


def main() -> None:
    """Start the default runtime target."""

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    _run_startup_preflight()

    # Import only after preflight to avoid partial startup with bad config.
    from bot.telegram_bot import main as run_telegram_bot

    run_telegram_bot()


if __name__ == "__main__":
    main()


