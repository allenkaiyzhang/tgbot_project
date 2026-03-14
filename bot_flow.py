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

HELP_TEXT = config.get_text("bot.help_text")
ASKDS_PROMPT = config.get_text("bot.askds_prompt")
ASKCHATGPT_PROMPT = config.get_text("bot.askchatgpt_prompt")
ASKSTOCK_PROMPT = config.get_text("bot.askstock_prompt")
ASKSTOCK_INVALID = config.get_text("bot.askstock_invalid")
ASKSTOCK_ANALYSIS_CONFIRM = config.get_text("bot.askstock_analysis_confirm")
ASKSTOCK_ANALYSIS_INVALID = config.get_text("bot.askstock_analysis_invalid")
ASKSTOCK_ANALYSIS_CANCELLED = config.get_text("bot.askstock_analysis_cancelled")
ASKSTOCK_CONTEXT_MISSING = config.get_text("bot.askstock_context_missing")

YES_WORDS = {str(v).strip().lower() for v in config.get_text("bot.yes_words")}
NO_WORDS = {str(v).strip().lower() for v in config.get_text("bot.no_words")}
DEEPSEEK_MODEL = config.get_text("llm.deepseek_model")
NOTIFY_FUNCTIONS = set(config.get_text("bot.email_notify_functions"))


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
        self._email_notify_functions = (
            NOTIFY_FUNCTIONS if email_notify_functions is None else email_notify_functions
        )
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
        if normalized in YES_WORDS:
            return True
        if normalized in NO_WORDS:
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
        if not self._config.GMAIL_SENDER:
            return False
        if not self._config.GMAIL_APP_PASSWORD:
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
    def _serialize_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        try:
            return json.dumps(content, ensure_ascii=False, indent=2, default=str)
        except Exception:
            return str(content)

    def _create_text_attachment(
        self,
        *,
        function_name: str,
        chat_id: int,
        kind: str,
        content: Any,
    ) -> str:
        """Persist text content to a temporary file and return path."""

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=f"_{function_name}_{chat_id}_{kind}.txt",
            prefix="tgbot_",
            encoding="utf-8",
            delete=False,
        ) as file:
            file.write(self._serialize_text(content))
            return file.name

    @staticmethod
    def _build_email_summary_prompt(user_query: str, response_text: str) -> str:
        template = config.get_text("bot.email_summary_prompt_template")
        return template.format(user_query=user_query, response_text=response_text)

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
            print(config.get_text("email.gmail_incomplete_log"))
            return

        subject_template = config.get_text("bot.email_subject_template")
        subject = subject_template.format(chat_id=chat_id, function_name=function_name)

        response_text = self._serialize_text(response)
        summary_text = config.get_text("email.summary_generation_failed")
        try:
            summary_text = self._llm.get_llm_response(
                self._build_email_summary_prompt(user_query=user_query, response_text=response_text),
                model=DEEPSEEK_MODEL,
                provider="deepseek",
            ).strip()
        except Exception as summary_error:
            template = config.get_text("email.summary_generation_failed_log")
            print(template.format(function_name=function_name, error=summary_error))

        body_template = config.get_text("bot.email_body_template")
        body = body_template.format(
            summary=summary_text,
            response_is_empty=(not response_non_empty),
            is_success=is_success,
        )

        request_attachment_path = self._create_text_attachment(
            function_name=function_name,
            chat_id=chat_id,
            kind="request",
            content=user_query,
        )
        response_attachment_path = self._create_text_attachment(
            function_name=function_name,
            chat_id=chat_id,
            kind="response",
            content=response,
        )
        attachment_paths = [request_attachment_path, response_attachment_path]

        try:
            self._gmail_sender(
                sender=self._config.GMAIL_SENDER,
                app_password=self._config.GMAIL_APP_PASSWORD,
                to=self._config.GMAIL_TO_LIST,
                subject=subject,
                body=body,
                cc=self._config.GMAIL_CC_LIST,
                attachments=attachment_paths,
            )
        except Exception as email_error:
            template = config.get_text("email.email_notification_failed_log")
            print(template.format(function_name=function_name, error=email_error))
        finally:
            for attachment_path in attachment_paths:
                try:
                    Path(attachment_path).unlink(missing_ok=True)
                except Exception as cleanup_error:
                    template = config.get_text("email.attachment_cleanup_failed_log")
                    print(template.format(error=cleanup_error))

    def _handle_askds_reply(self, bot, message) -> bool:
        chat_id = message.chat.id
        if not self._consume_pending(self._pending_askds, chat_id):
            return False

        prompt = (message.text or "").strip()
        try:
            reply = self._llm.get_llm_response(
                prompt,
                model=DEEPSEEK_MODEL,
                provider="deepseek",
            )
            is_success = True
        except Exception as error:
            template = config.get_text("bot.askds_error_template")
            reply = template.format(error=error)
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
            reply = self._llm.get_llm_response(
                prompt,
                model=config.CHATGPT_MODEL,
                provider="chatgpt",
            )
            is_success = True
        except Exception as error:
            template = config.get_text("bot.askchatgpt_error_template")
            reply = template.format(error=error)
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
            bot.reply_to(message, ASKSTOCK_CONTEXT_MISSING)
            return True

        symbols_text = ", ".join(context.get("symbols", []))
        stock_reply = context.get("stock_reply", "")
        today = date.today().isoformat()
        analysis_prompt_template = config.get_text("bot.askstock_analysis_prompt_template")
        prompt = analysis_prompt_template.format(
            today=today,
            symbols_text=symbols_text,
            stock_reply=stock_reply,
        )

        try:
            analysis_reply = self._llm.get_llm_response(
                prompt,
                model=config.CHATGPT_MODEL,
                provider="chatgpt",
            )
            is_success = True
        except Exception as error:
            template = config.get_text("bot.askstock_analysis_error_template")
            analysis_reply = template.format(error=error)
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
            template = config.get_text("bot.askstock_error_template")
            reply = template.format(error=error)
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
