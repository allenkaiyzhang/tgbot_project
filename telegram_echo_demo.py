"""Simple Telegram echo bot demo."""

import telebot

import config

BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)


@bot.message_handler(commands=["start", "help"])
def handle_start_help(message):
    bot.reply_to(message, "你好，我是一个最简单的 Echo Bot。你发送什么我就回复什么。")


@bot.message_handler(func=lambda m: True)
def handle_echo(message):
    text = message.text or ""
    bot.reply_to(message, text)


def main() -> None:
    print("Echo Bot 已启动，开始 polling ... (CTRL+C 可停止)")
    bot.infinity_polling(timeout=60)


if __name__ == "__main__":
    main()
