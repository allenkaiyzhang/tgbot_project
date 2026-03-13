"""Project startup entrypoint.

Current routing:
- default startup target -> telegram_bot.main
"""

from telegram_bot import main as run_telegram_bot


def main() -> None:
    """Start the default runtime target."""

    run_telegram_bot()


if __name__ == "__main__":
    main()
