"""Project startup entrypoint.

Current routing:
- default startup target -> telegram_bot.main
"""

from telegram_bot import main as run_telegram_bot


def main() -> None:
    # 统一从这里启动，后续如果增加 Web/API 模式可在此处切换入口。
    run_telegram_bot()


if __name__ == "__main__":
    main()
