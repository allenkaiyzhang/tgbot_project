"""Simple Telegram echo bot demo.

This file is independent from the main bot flow and can be used for
quick smoke tests of Telegram connectivity.
"""

from __future__ import annotations

import telebot

import config

BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)


@bot.message_handler(commands=["start", "help"])
def handle_start_help(message):
    """Show a short intro message."""

    bot.reply_to(message, "你好，我是一个最简单的 Echo Bot。你发送什么我就回复什么。")


@bot.message_handler(func=lambda m: True)
def handle_echo(message):
    """Echo back any text message."""

    text = message.text or ""
    bot.reply_to(message, text)


def main() -> None:
    """Run echo bot polling loop."""

    print("Echo Bot 已启动，开始 polling ... (CTRL+C 可停止)")
    bot.infinity_polling(timeout=60)


if __name__ == "__main__":
    main()
