"""Minimal Telegram bot with DeepSeek + LongBridge features."""

from __future__ import annotations

import re
from typing import Any

import telebot

import config
import deepseek_service
import longbridge_service
from gmail_service import send_gmail

BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# Chat state: waiting for user's follow-up input.
pending_askds: dict[int, bool] = {}
pending_askstock: dict[int, bool] = {}

# Future-friendly toggle list: add function names here to enable email notification.
EMAIL_NOTIFY_FUNCTIONS = {"askds", "askstock"}


def send_long_reply(message, text: str, max_len: int = 4000) -> None:
    """Split and send long text to avoid Telegram single-message limits."""

    start = 0
    while start < len(text):
        chunk = text[start : start + max_len]
        bot.reply_to(message, chunk)
        start += max_len


def _parse_symbols(text: str) -> list[str]:
    """Extract stock symbols separated by comma/space."""

    return [s.strip() for s in re.split(r"[\s,]+", text) if s.strip()]


def _is_non_empty_response(response: Any) -> bool:
    """Return True when response should be considered non-empty."""

    if response is None:
        return False
    if isinstance(response, str):
        return bool(response.strip())
    if isinstance(response, (list, tuple, set, dict)):
        return len(response) > 0
    return True


def _is_gmail_configured() -> bool:
    """Check whether Gmail sender credentials and recipients are usable."""

    if not config.GMAIL_TO_LIST:
        return False
    if not config.GMAIL_SENDER or config.GMAIL_SENDER == "YOUR_GMAIL_ADDRESS":
        return False
    if not config.GMAIL_APP_PASSWORD or config.GMAIL_APP_PASSWORD == "YOUR_GMAIL_APP_PASSWORD":
        return False
    return True


def _maybe_send_function_email(
    *,
    function_name: str,
    chat_id: int,
    user_query: str,
    response: Any,
    is_success: bool,
) -> None:
    """Send function-usage email when enabled and response is non-empty."""

    if function_name not in EMAIL_NOTIFY_FUNCTIONS:
        return

    response_non_empty = _is_non_empty_response(response)
    if not response_non_empty:
        return

    if not _is_gmail_configured():
        print("Email notification skipped: Gmail settings are incomplete.")
        return

    subject = f"{chat_id}用户调用了一次{function_name}函数"
    body = "\n".join(
        [
            f"用户查询内容为：{user_query}",
            f"response是否为空：{not response_non_empty}",
            f"本次查询是否成功：{is_success}",
        ]
    )

    try:
        send_gmail(
            sender=config.GMAIL_SENDER,
            app_password=config.GMAIL_APP_PASSWORD,
            to=config.GMAIL_TO_LIST,
            subject=subject,
            body=body,
            cc=config.GMAIL_CC_LIST,
        )
    except Exception as email_error:
        # Keep bot response path healthy even if email fails.
        print(f"Email notification failed for {function_name}: {email_error}")


def _handle_askds_reply(message) -> bool:
    """If current chat is waiting for /askds input, call DeepSeek and reply."""

    chat_id = message.chat.id
    if not pending_askds.pop(chat_id, False):
        return False

    prompt = (message.text or "").strip()
    try:
        reply = deepseek_service.get_deepseek_response(prompt)
        is_success = True
    except Exception as e:
        reply = f"askds 调用失败: {e}"
        is_success = False

    if reply:
        send_long_reply(message, reply)

    _maybe_send_function_email(
        function_name="askds",
        chat_id=chat_id,
        user_query=prompt,
        response=reply,
        is_success=is_success,
    )
    return True


def _handle_askstock_reply(message) -> bool:
    """If current chat is waiting for /askstock input, fetch quotes and reply."""

    chat_id = message.chat.id
    if not pending_askstock.pop(chat_id, False):
        return False

    user_text = (message.text or "").strip()
    symbols = _parse_symbols(user_text)
    if not symbols:
        bot.reply_to(
            message,
            "格式错误，请输入股票代码，例如：QQQ.US 或 0700.HK（可用逗号或空格分隔多个）",
        )
        return True

    try:
        reply = longbridge_service.get_inspected_quotes_text(symbols=symbols)
        is_success = True
    except Exception as e:
        reply = f"askstock 查询失败: {e}"
        is_success = False

    if reply:
        send_long_reply(message, reply)

    _maybe_send_function_email(
        function_name="askstock",
        chat_id=chat_id,
        user_query=user_text,
        response=reply,
        is_success=is_success,
    )
    return True


def process_message(message) -> bool:
    """Process all user messages. Return True if consumed."""

    if _handle_askds_reply(message):
        return True

    if _handle_askstock_reply(message):
        return True

    return False


@bot.message_handler(commands=["askds"])
def handle_askds(message):
    chat_id = message.chat.id
    pending_askds[chat_id] = True
    bot.reply_to(message, "请输入你要让 AI 回答的 prompt（发送后会返回 deepseek-chat 的结果）")


@bot.message_handler(commands=["askstock"])
def handle_askstock(message):
    chat_id = message.chat.id
    pending_askstock[chat_id] = True
    bot.reply_to(message, "请输入要查询的股票代码（支持多个，用逗号或空格分隔，例如：QQQ.US 0700.HK）")


@bot.message_handler(func=lambda m: True)
def handle_echo(message):
    if process_message(message):
        return
    bot.reply_to(message, "1")


def main() -> None:
    print("Bot 已启动，开始 polling ... (CTRL+C 可停止)")
    bot.infinity_polling(timeout=60)


if __name__ == "__main__":
    main()
