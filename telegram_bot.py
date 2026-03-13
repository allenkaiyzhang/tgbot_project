"""Telegram bot entry layer.

This module only:
- creates the Telegram bot instance
- registers command handlers
- routes message processing to `bot_flow.py`
"""

from __future__ import annotations

import telebot

import bot_flow
import config

BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)


@bot.message_handler(commands=["start", "help"])
def handle_help(message):
    """Show command usage instructions."""

    bot.reply_to(message, bot_flow.get_help_text())


@bot.message_handler(commands=["askds"])
def handle_askds(message):
    """Enter DeepSeek query mode for current chat."""

    bot_flow.set_askds_pending(message.chat.id)
    bot.reply_to(message, bot_flow.get_askds_prompt())


@bot.message_handler(commands=["askchatgpt"])
def handle_askchatgpt(message):
    """Enter ChatGPT query mode for current chat."""

    bot_flow.set_askchatgpt_pending(message.chat.id)
    bot.reply_to(message, bot_flow.get_askchatgpt_prompt())


@bot.message_handler(commands=["askstock"])
def handle_askstock(message):
    """Enter stock-query mode for current chat."""

    bot_flow.set_askstock_pending(message.chat.id)
    bot.reply_to(message, bot_flow.get_askstock_prompt())


@bot.message_handler(func=lambda m: True)
def handle_echo(message):
    """Fallback handler for all messages not consumed by command flows."""

    if bot_flow.process_message(bot, message):
        return
    bot.reply_to(message, "1")


def main() -> None:
    """Run bot polling loop."""

    print("Bot 已启动，开始 polling ... (CTRL+C 可停止)")
    bot.infinity_polling(timeout=60)


if __name__ == "__main__":
    main()
