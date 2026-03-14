"""Bot conversation flow and business logic."""

from __future__ import annotations

import json
import re
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

import ai_notification_service
import config
import longbridge_service

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

ASKDS_PROMPT = "请输入你要让 DeepSeek 回答的 prompt（发送后返回结果）："
ASKCHATGPT_PROMPT = "请输入你要让 ChatGPT 回答的 prompt（发送后返回结果）："
ASKSTOCK_PROMPT = "请输入要查询的股票代码（支持多个，用逗号或空格分隔，例如：QQQ.US 0700.HK）："
ASKSTOCK_INVALID = "格式错误，请输入股票代码，例如：QQQ.US 或 0700.HK（可用逗号或空格分隔多个）"


ASKSTOCK_ANALYSIS_CONFIRM = "是否需要用ChatGPT进行高级技术分析（是/否）"
ASKSTOCK_ANALYSIS_INVALID = "请回复 是 或 否。"
ASKSTOCK_ANALYSIS_CANCELLED = "好的，已取消高级技术分析。"


class BotFlow:
    """Stateful bot flow manager."""

    def __init__(
        self,
        *,
        config_module=config,
        llm_module=ai_notification_service,
        longbridge_module=longbridge_service,
        gmail_sender=ai_notification_service.send_gmail,
        email_notify_functions: set[str] | None = None,
    ) -> None:
        self._config = config_module
        self._llm = llm_module
        self._longbridge = longbridge_module
        self._gmail_sender = gmail_sender
        self._email_notify_functions = email_notify_functions or {"askds", "askchatgpt", "askstock"}
        self._pending_askds: set[int] = set()
        self._pending_askchatgpt: set[int] = set()
        self._pending_askstock: set[int] = set()
        self._pending_askstock_analysis: set[int] = set()
        self._askstock_analysis_context: dict[int, dict[str, Any]] = {}

    @staticmethod
    def get_help_text() -> str:
        return HELP_TEXT

    @staticmethod
    def get_askds_prompt() -> str:
        return ASKDS_PROMPT

    @staticmethod
    def get_askchatgpt_prompt() -> str:
        return ASKCHATGPT_PROMPT

    @staticmethod
    def get_askstock_prompt() -> str:
        return ASKSTOCK_PROMPT

    @staticmethod
    def get_askstock_invalid_text() -> str:
        return ASKSTOCK_INVALID

    def set_askds_pending(self, chat_id: int) -> None:
        self._pending_askds.add(chat_id)

    def get_askds_pending(self, chat_id: int) -> bool:
        return chat_id in self._pending_askds

    def set_askchatgpt_pending(self, chat_id: int) -> None:
        self._pending_askchatgpt.add(chat_id)

    def get_askchatgpt_pending(self, chat_id: int) -> bool:
        return chat_id in self._pending_askchatgpt

    def set_askstock_pending(self, chat_id: int) -> None:
        self._pending_askstock.add(chat_id)
        self._pending_askstock_analysis.discard(chat_id)
        self._askstock_analysis_context.pop(chat_id, None)

    def get_askstock_pending(self, chat_id: int) -> bool:
        return chat_id in self._pending_askstock

    @staticmethod
    def _parse_symbols(text: str) -> list[str]:
        return [s.strip() for s in re.split(r"[\s,]+", text) if s.strip()]

    @staticmethod
    def _normalize_yes_no(text: str) -> bool | None:
        normalized = text.strip().lower()
        if normalized in {"是", "y", "yes"}:
            return True
        if normalized in {"否", "不", "n", "no"}:
            return False
        return None

    @staticmethod
    def _is_non_empty_response(response: Any) -> bool:
        if response is None:
            return False
        if isinstance(response, str):
            return bool(response.strip())
        if isinstance(response, (list, tuple, set, dict)):
            return len(response) > 0
        return True

    def _is_gmail_configured(self) -> bool:
        if not self._config.GMAIL_TO_LIST:
            return False
        if not self._config.GMAIL_SENDER or self._config.GMAIL_SENDER == "YOUR_GMAIL_ADDRESS":
            return False
        if not self._config.GMAIL_APP_PASSWORD or self._config.GMAIL_APP_PASSWORD == "YOUR_GMAIL_APP_PASSWORD":
            return False
        return True

    @staticmethod
    def send_long_reply(bot, message, text: str, max_len: int = 4000) -> None:
        start = 0
        while start < len(text):
            chunk = text[start : start + max_len]
            bot.reply_to(message, chunk)
            start += max_len

    @staticmethod
    def _consume_pending(pending: set[int], chat_id: int) -> bool:
        if chat_id not in pending:
            return False
        pending.remove(chat_id)
        return True

    @staticmethod
    def _create_response_attachment(
        *,
        function_name: str,
        chat_id: int,
        response: Any,
    ) -> str:
        """Persist response content to a temporary text file and return path."""

        if isinstance(response, str):
            content = response
        else:
            try:
                content = json.dumps(response, ensure_ascii=False, indent=2, default=str)
            except Exception:
                content = str(response)

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=f"_{function_name}_{chat_id}_response.txt",
            prefix="tgbot_",
            encoding="utf-8",
            delete=False,
        ) as file:
            file.write(content)
            return file.name

    def _maybe_send_function_email(
        self,
        *,
        function_name: str,
        chat_id: int,
        user_query: str,
        response: Any,
        is_success: bool,
    ) -> None:
        if function_name not in self._email_notify_functions:
            return

        response_non_empty = self._is_non_empty_response(response)
        if not response_non_empty:
            return

        if not self._is_gmail_configured():
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

        attachment_path = self._create_response_attachment(
            function_name=function_name,
            chat_id=chat_id,
            response=response,
        )

        try:
            self._gmail_sender(
                sender=self._config.GMAIL_SENDER,
                app_password=self._config.GMAIL_APP_PASSWORD,
                to=self._config.GMAIL_TO_LIST,
                subject=subject,
                body=body,
                cc=self._config.GMAIL_CC_LIST,
                attachments=[attachment_path],
            )
        except Exception as email_error:
            print(f"Email notification failed for {function_name}: {email_error}")
        finally:
            try:
                Path(attachment_path).unlink(missing_ok=True)
            except Exception as cleanup_error:
                print(f"Attachment cleanup failed: {cleanup_error}")

    def _handle_askds_reply(self, bot, message) -> bool:
        chat_id = message.chat.id
        if not self._consume_pending(self._pending_askds, chat_id):
            return False

        prompt = (message.text or "").strip()
        try:
            reply = self._llm.get_llm_response(prompt,model="deepseek-chat" ,provider="deepseek")
            is_success = True
        except Exception as error:
            reply = f"askds 调用失败: {error}"
            is_success = False

        if reply:
            self.send_long_reply(bot, message, reply)

        self._maybe_send_function_email(
            function_name="askds",
            chat_id=chat_id,
            user_query=prompt,
            response=reply,
            is_success=is_success,
        )
        return True

    def _handle_askchatgpt_reply(self, bot, message) -> bool:
        chat_id = message.chat.id
        if not self._consume_pending(self._pending_askchatgpt, chat_id):
            return False

        prompt = (message.text or "").strip()
        try:
            reply = self._llm.get_llm_response(prompt,model=config.CHATGPT_MODEL,provider="chatgpt")
            is_success = True
        except Exception as error:
            reply = f"askchatgpt 调用失败: {error}"
            is_success = False

        if reply:
            self.send_long_reply(bot, message, reply)

        self._maybe_send_function_email(
            function_name="askchatgpt",
            chat_id=chat_id,
            user_query=prompt,
            response=reply,
            is_success=is_success,
        )
        return True

    def _handle_askstock_analysis_reply(self, bot, message) -> bool:
        chat_id = message.chat.id
        if chat_id not in self._pending_askstock_analysis:
            return False

        decision = self._normalize_yes_no(message.text or "")
        if decision is None:
            bot.reply_to(message, ASKSTOCK_ANALYSIS_INVALID)
            return True

        self._pending_askstock_analysis.discard(chat_id)
        context = self._askstock_analysis_context.pop(chat_id, None)

        if decision is False:
            bot.reply_to(message, ASKSTOCK_ANALYSIS_CANCELLED)
            return True
        if not context:
            bot.reply_to(message, "No askstock context found. Please run /askstock again.")
            return True

        symbols_text = ", ".join(context.get("symbols", []))
        stock_reply = context.get("stock_reply", "")
        today = date.today().isoformat()
        prompt = (
            f"Today is {today}. Please perform technical analysis for US/HK stocks "
            f"{symbols_text} using the following realtime quote, candlestick, and "
            f"offset-candlestick data:\n{stock_reply}"
        )

        try:
            analysis_reply = self._llm.get_llm_response(prompt, model=config.CHATGPT_MODEL,provider="chatgpt")
            is_success = True
        except Exception as error:
            analysis_reply = f"askstock advanced technical analysis failed: {error}"
            is_success = False

        if analysis_reply:
            self.send_long_reply(bot, message, analysis_reply)

        self._maybe_send_function_email(
            function_name="askchatgpt",
            chat_id=chat_id,
            user_query=prompt,
            response=analysis_reply,
            is_success=is_success,
        )
        return True

    def _handle_askstock_reply(self, bot, message) -> bool:
        chat_id = message.chat.id
        if not self._consume_pending(self._pending_askstock, chat_id):
            return False

        user_text = (message.text or "").strip()
        symbols = self._parse_symbols(user_text)
        if not symbols:
            bot.reply_to(message, self.get_askstock_invalid_text())
            return True

        try:
            reply = self._longbridge.get_inspected_quotes_text(symbols=symbols)
            is_success = True
        except Exception as error:
            reply = f"askstock 查询失败: {error}"
            is_success = False

        if reply:
            self.send_long_reply(bot, message, reply)

        self._maybe_send_function_email(
            function_name="askstock",
            chat_id=chat_id,
            user_query=user_text,
            response=reply,
            is_success=is_success,
        )

        if is_success and self._is_non_empty_response(reply):
            self._pending_askstock_analysis.add(chat_id)
            self._askstock_analysis_context[chat_id] = {
                "symbols": symbols,
                "stock_reply": reply,
            }
            bot.reply_to(message, ASKSTOCK_ANALYSIS_CONFIRM)
        else:
            self._pending_askstock_analysis.discard(chat_id)
            self._askstock_analysis_context.pop(chat_id, None)

        return True

    def process_message(self, bot, message) -> bool:
        if self._handle_askstock_analysis_reply(bot, message):
            return True
        if self._handle_askds_reply(bot, message):
            return True
        if self._handle_askchatgpt_reply(bot, message):
            return True
        if self._handle_askstock_reply(bot, message):
            return True
        return False


_flow: BotFlow = BotFlow()


def set_flow(flow: BotFlow) -> None:
    global _flow
    _flow = flow


def get_flow() -> BotFlow:
    return _flow


def get_help_text() -> str:
    return get_flow().get_help_text()


def get_askds_prompt() -> str:
    return get_flow().get_askds_prompt()


def get_askchatgpt_prompt() -> str:
    return get_flow().get_askchatgpt_prompt()


def get_askstock_prompt() -> str:
    return get_flow().get_askstock_prompt()


def set_askds_pending(chat_id: int) -> None:
    get_flow().set_askds_pending(chat_id)


def get_askds_pending(chat_id: int) -> bool:
    return get_flow().get_askds_pending(chat_id)


def set_askchatgpt_pending(chat_id: int) -> None:
    get_flow().set_askchatgpt_pending(chat_id)


def get_askchatgpt_pending(chat_id: int) -> bool:
    return get_flow().get_askchatgpt_pending(chat_id)


def set_askstock_pending(chat_id: int) -> None:
    get_flow().set_askstock_pending(chat_id)


def get_askstock_pending(chat_id: int) -> bool:
    return get_flow().get_askstock_pending(chat_id)


def process_message(bot, message) -> bool:
    return get_flow().process_message(bot, message)
