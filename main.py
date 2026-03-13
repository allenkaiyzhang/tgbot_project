"""Project startup entrypoint."""

from telegram_bot import main as run_telegram_bot


def main() -> None:
    run_telegram_bot()


if __name__ == "__main__":
    main()
