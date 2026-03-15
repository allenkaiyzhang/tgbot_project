"""Telegram bot entry layer.

This module only:
- creates the Telegram bot instance
- registers command handlers
- routes message processing to `bot_flow.py`
"""

from __future__ import annotations

import logging
import time

import telebot

from bot import bot_flow
import config

BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
FALLBACK_TEXT = config.get_text("telegram.unmatched_reply")
STARTUP_MESSAGE = config.get_text("telegram.startup_message")
logger = logging.getLogger(__name__)
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
    bot.reply_to(message, FALLBACK_TEXT)


def main() -> None:
    """Run bot polling loop."""

    logger.info(STARTUP_MESSAGE)
    retry_delay_seconds = 5
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
        except Exception as error:
            logger.exception("Bot polling crashed, retrying in %ss: %s", retry_delay_seconds, error)
            time.sleep(retry_delay_seconds)


if __name__ == "__main__":
    main()

