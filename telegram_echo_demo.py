# minimal_echo_bot.py
# 最小可用 Telegram Echo Bot，直接用 python 运行即可。

import telebot  # pyTelegramBotAPI 主库，用于创建 bot 和处理消息

# 这里写成占位符，运行前把 YOUR_BOT_TOKEN 换成你自己机器人的 token
BOT_TOKEN = "8550911740:AAFY_z7wPba_94fFiuoQXwZu1_ImRCE32Fc"

# 创建 bot 实例，这是程序的核心对象
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)


# /start 和 /help 指令处理（只要用户输入 "/start" 或 "/help" 就会触发）
@bot.message_handler(commands=["start", "help"])
def handle_start_help(message):
    # reply_to 会把消息发回给发消息的用户，并自动引用这条消息
    bot.reply_to(message, "你好，我是一个最简单的 Echo Bot。你发送什么我就回复什么。")


# 普通文本消息 echo 处理（func=lambda m: True 表示对所有消息都生效）
@bot.message_handler(func=lambda m: True)
def handle_echo(message):
    # message.text 是用户发送的文本；如果用户发送的不是文本，这里可能是 None
    text = message.text or ""
    bot.reply_to(message, text)  # 直接回复原文


def main():
    # 启动 polling，开始循环接收新消息
    # timeout=60 表示长轮询最长等 60 秒（这是 telebot 的推荐写法）
    print("Bot 已启动，开始 polling ... (CTRL+C 可停止)")
    bot.infinity_polling(timeout=60)


if __name__ == "__main__":
    main()