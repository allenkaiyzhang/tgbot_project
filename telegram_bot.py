"""最小可用 Telegram Bot

功能：
- `/askds`：进入 DeepSeek Chat 模式，用户输入 prompt 后返回 AI 回复
- `/askstock`：进入股票行情查询模式，用户输入代码后返回行情数据
- 其他消息：统一回复 `1`

本示例旨在保持最简，易于初学者理解。
"""

import re

import telebot  # pyTelegramBotAPI 主库，用于创建 bot 和处理消息

import config  # 统一读取环境变量配置
import deepseek_client  # 用于调用 deepseek-chat API
import quote_status  # 用于获取行情信息并格式化输出

# Bot Token 从环境变量读取，未设置时使用占位符
BOT_TOKEN = config.TELEGRAM_BOT_TOKEN

# 创建 bot 实例，这是程序的核心对象
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# 记录正在等待用户输入 prompt 的聊天 (chat_id -> bool)
pending_askds = {}

# 记录正在等待用户输入股票代码的聊天 (chat_id -> bool)
pending_askstock = {}


def send_long_reply(message, text, max_len=4000):
    """如果文本过长，则分成多条消息发送。

    Telegram 单条消息最大约 4096 字符，这里留一点余量。
    """

    # 简单按字符切分（避免超长消息被拒绝）
    start = 0
    while start < len(text):
        chunk = text[start : start + max_len]
        bot.reply_to(message, chunk)
        start += max_len


def _parse_symbols(text: str) -> list[str]:
    """从用户输入中提取股票代码（支持逗号/空格分隔）。"""

    return [s.strip() for s in re.split(r"[\s,]+", text) if s.strip()]


def _handle_askds_reply(message) -> bool:
    """如果当前 chat 处于 /askds 等待状态，则发送 deepseek 回复并返回 True。"""

    chat_id = message.chat.id
    if not pending_askds.pop(chat_id, False):
        return False

    prompt = message.text or ""
    reply = deepseek_client.get_deepseek_response(prompt)
    send_long_reply(message, reply)
    return True


def _handle_askstock_reply(message) -> bool:
    """如果当前 chat 处于 /askstock 等待状态，则查询行情并发送回复。"""

    chat_id = message.chat.id
    if not pending_askstock.pop(chat_id, False):
        return False

    symbols = _parse_symbols(message.text or "")
    if not symbols:
        bot.reply_to(
            message,
            "格式错误，请输入股票代码，例如：QQQI.US 或 0700.HK（可用逗号/空格分隔多个）",
        )
        return True

    reply = quote_status.get_inspected_quotes_text(symbols=symbols)
    send_long_reply(message, reply)
    return True


def process_message(message) -> bool:
    """处理所有用户消息，返回 True 表示已处理（不需要 echo）。"""

    # /askds 模式（deepseek）
    if _handle_askds_reply(message):
        return True

    # /askstock 模式（行情查询）
    if _handle_askstock_reply(message):
        return True

    return False


# /askds 指令处理，进入 deepseek 询问模式（提示用户输入 prompt）
@bot.message_handler(commands=["askds"])
def handle_askds(message):
    chat_id = message.chat.id
    pending_askds[chat_id] = True

    bot.reply_to(
        message,
        "请输入你要让 AI 回答的 prompt（发送后会返回 deepseek-chat 的回答）：",
    )


# /askstock 指令处理，进入股票查询模式（提示用户输入股票代码）
@bot.message_handler(commands=["askstock"])
def handle_askstock(message):
    chat_id = message.chat.id
    pending_askstock[chat_id] = True

    bot.reply_to(
        message,
        "请输入要查询的股票代码（支持多个，用逗号或空格分隔，例如：QQQI.US 0700.HK）：",
    )


# 普通文本消息处理（func=lambda m: True 表示对所有消息都生效）
@bot.message_handler(func=lambda m: True)
def handle_echo(message):
    # 将判断逻辑交给 process_message 函数处理，避免 handler 内部过多逻辑。
    if process_message(message):
        return

    # 其他情况，统一回复“1”
    bot.reply_to(message, "1")


def main():
    # 启动 polling，开始循环接收新消息
    # timeout=60 表示长轮询最长等 60 秒（这是 telebot 的推荐写法）
    print("Bot 已启动，开始 polling ... (CTRL+C 可停止)")
    bot.infinity_polling(timeout=60)


if __name__ == "__main__":
    main()