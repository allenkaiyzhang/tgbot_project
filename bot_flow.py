"""Bot conversation flow and business logic.

This module is intentionally framework-light:
- It stores command waiting states.
- It executes command follow-up logic.
- It sends optional notification emails.
"""

from __future__ import annotations

import re
from typing import Any

import config
import llm_service
import longbridge_service
from gmail_service import send_gmail

# Help and prompt texts used by telegram_bot.py.
HELP_TEXT = (
    "可用命令与用法：\n"
    "1) /askds\n"
    "发送该命令后，再发送你的问题，Bot 会用 DeepSeek 返回结果。\n\n"
    "2) /askchatgpt\n"
    "发送该命令后，再发送你的问题，Bot 会用 ChatGPT 返回结果。\n\n"
    "3) /askstock\n"
    "发送该命令后，再发送股票代码，支持多个，空格或逗号分隔。\n"
    "示例：QQQ.US 0700.HK"
)

ASKDS_PROMPT = "请输入你要让 DeepSeek 回答的 prompt（发送后返回结果）"
ASKCHATGPT_PROMPT = "请输入你要让 ChatGPT 回答的 prompt（发送后返回结果）"
ASKSTOCK_PROMPT = "请输入要查询的股票代码（支持多个，用逗号或空格分隔，例如：QQQ.US 0700.HK）"
ASKSTOCK_INVALID = "格式错误，请输入股票代码，例如：QQQ.US 或 0700.HK（可用逗号或空格分隔多个）"

# Chat state: waiting for user's next input for specific commands.
pending_askds: dict[int, bool] = {}
pending_askchatgpt: dict[int, bool] = {}
pending_askstock: dict[int, bool] = {}

# Add function names here to enable email notification for new commands.
EMAIL_NOTIFY_FUNCTIONS = {"askds", "askchatgpt", "askstock"}


def mark_askds_pending(chat_id: int) -> None:
    """Mark current chat as waiting for /askds follow-up input."""

    pending_askds[chat_id] = True


def mark_askchatgpt_pending(chat_id: int) -> None:
    """Mark current chat as waiting for /askchatgpt follow-up input."""

    pending_askchatgpt[chat_id] = True


def mark_askstock_pending(chat_id: int) -> None:
    """Mark current chat as waiting for /askstock follow-up input."""

    pending_askstock[chat_id] = True


def send_long_reply(bot, message, text: str, max_len: int = 4000) -> None:
    """Split long text into chunks to satisfy Telegram message limit."""

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
    """Send usage email when enabled and response is non-empty."""

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
        # Keep bot path healthy even if email notification fails.
        print(f"Email notification failed for {function_name}: {email_error}")


def _handle_askds_reply(bot, message) -> bool:
    """Handle the follow-up message for /askds flow."""

    chat_id = message.chat.id
    if not pending_askds.pop(chat_id, False):
        return False

    prompt = (message.text or "").strip()
    try:
        reply = llm_service.get_llm_response(prompt, provider="deepseek")
        is_success = True
    except Exception as error:
        reply = f"askds 调用失败: {error}"
        is_success = False

    if reply:
        send_long_reply(bot, message, reply)

    _maybe_send_function_email(
        function_name="askds",
        chat_id=chat_id,
        user_query=prompt,
        response=reply,
        is_success=is_success,
    )
    return True


def _handle_askchatgpt_reply(bot, message) -> bool:
    """Handle the follow-up message for /askchatgpt flow."""

    chat_id = message.chat.id
    if not pending_askchatgpt.pop(chat_id, False):
        return False

    prompt = (message.text or "").strip()
    try:
        reply = llm_service.get_llm_response(prompt, provider="chatgpt")
        is_success = True
    except Exception as error:
        reply = f"askchatgpt 调用失败: {error}"
        is_success = False

    if reply:
        send_long_reply(bot, message, reply)

    _maybe_send_function_email(
        function_name="askchatgpt",
        chat_id=chat_id,
        user_query=prompt,
        response=reply,
        is_success=is_success,
    )
    return True


def _handle_askstock_reply(bot, message) -> bool:
    """Handle the follow-up message for /askstock flow."""

    chat_id = message.chat.id
    if not pending_askstock.pop(chat_id, False):
        return False

    user_text = (message.text or "").strip()
    symbols = _parse_symbols(user_text)
    if not symbols:
        bot.reply_to(message, ASKSTOCK_INVALID)
        return True

    try:
        reply = longbridge_service.get_inspected_quotes_text(symbols=symbols)
        is_success = True
    except Exception as error:
        reply = f"askstock 查询失败: {error}"
        is_success = False

    if reply:
        send_long_reply(bot, message, reply)

    _maybe_send_function_email(
        function_name="askstock",
        chat_id=chat_id,
        user_query=user_text,
        response=reply,
        is_success=is_success,
    )
    return True


def process_message(bot, message) -> bool:
    """Process all user messages and return whether consumed."""

    if _handle_askds_reply(bot, message):
        return True

    if _handle_askchatgpt_reply(bot, message):
        return True

    if _handle_askstock_reply(bot, message):
        return True

    return False
