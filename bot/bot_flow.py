"""Bot conversation flow and business logic."""

from __future__ import annotations

import csv
import io
import json
import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from services import ai_notification_service
import config
from services import longbridge_service

logger = logging.getLogger(__name__)

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
LOG_INDEX_FILE = "query_index.csv"
LOG_DIR_NAME = "log"

KEYWORD_GROUPS: dict[str, list[str]] = {
    "stock": ["stock", "quote", "kline", "candlestick"],
    "analysis": ["analysis", "analyze", "technical"],
    "chatgpt": ["chatgpt", "gpt", "openai"],
    "deepseek": ["deepseek", "ds"],
}


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
        log_dir: str | Path | None = None,
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
        self._log_dir = (
            Path(log_dir)
            if log_dir is not None
            else Path(__file__).resolve().parents[1] / LOG_DIR_NAME
        )
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._log_index_path = self._log_dir / LOG_INDEX_FILE
        self._ensure_log_index_header()

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
    def send_text_as_file(bot, message, text: str, *, filename_prefix: str = "askstock_response") -> bool:
        if not hasattr(bot, "send_document"):
            return False
        try:
            file_obj = io.BytesIO(text.encode("utf-8"))
            file_obj.name = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            bot.send_document(message.chat.id, file_obj)
            return True
        except Exception as error:
            logger.warning("send_document failed, fallback to text reply: %s", error)
            return False

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

    def _ensure_log_index_header(self) -> None:
        if self._log_index_path.exists():
            return
        with self._log_index_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "record_id",
                    "timestamp",
                    "category",
                    "keywords",
                    "function_name",
                    "chat_id",
                    "is_success",
                    "response_is_empty",
                    "request_length",
                    "response_length",
                    "request_tokens",
                    "response_tokens",
                    "detail_file",
                ]
            )

    @staticmethod
    def _extract_keywords(text: str) -> tuple[str, list[str]]:
        normalized = text.lower()
        best_category = "general"
        best_hits: list[str] = []
        for category, keywords in KEYWORD_GROUPS.items():
            hits = [kw for kw in keywords if kw.lower() in normalized]
            if len(hits) > len(best_hits):
                best_category = category
                best_hits = hits
        return best_category, best_hits

    @staticmethod
    def _sanitize_name(text: str) -> str:
        return re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_") or "general"

    def _write_query_record(
        self,
        *,
        function_name: str,
        chat_id: int,
        user_query: str,
        response: Any,
        is_success: bool,
    ) -> dict[str, Any]:
        response_text = self._serialize_text(response)
        request_text = user_query or ""
        request_tokens = self._count_tokens(request_text, function_name=function_name)
        response_tokens = self._count_tokens(response_text, function_name=function_name)
        category, keywords = self._extract_keywords(f"{function_name} {request_text}")
        now = datetime.now()
        timestamp = now.isoformat(timespec="seconds")
        file_stamp = now.strftime("%Y%m%d_%H%M%S")
        record_id = uuid4().hex[:12]
        category_dir = self._log_dir / self._sanitize_name(category)
        category_dir.mkdir(parents=True, exist_ok=True)
        detail_path = category_dir / f"{file_stamp}_{chat_id}_{function_name}_{record_id}.txt"

        detail_lines = [
            f"record_id: {record_id}",
            f"timestamp: {timestamp}",
            f"function_name: {function_name}",
            f"chat_id: {chat_id}",
            f"category: {category}",
            f"keywords: {','.join(keywords)}",
            f"is_success: {is_success}",
            f"response_is_empty: {not self._is_non_empty_response(response)}",
            f"request_length: {len(request_text)}",
            f"response_length: {len(response_text)}",
            f"request_tokens: {request_tokens}",
            f"response_tokens: {response_tokens}",
            "",
            "[REQUEST]",
            request_text,
            "",
            "[RESPONSE]",
            response_text,
            "",
        ]
        detail_path.write_text("\n".join(detail_lines), encoding="utf-8")

        with self._log_index_path.open("a", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    record_id,
                    timestamp,
                    category,
                    ",".join(keywords),
                    function_name,
                    chat_id,
                    is_success,
                    not self._is_non_empty_response(response),
                    len(request_text),
                    len(response_text),
                    request_tokens if request_tokens is not None else "",
                    response_tokens if response_tokens is not None else "",
                    str(detail_path),
                ]
            )

        return {
            "record_id": record_id,
            "timestamp": timestamp,
            "category": category,
            "keywords": keywords,
            "detail_path": detail_path,
            "response_text": response_text,
            "response_non_empty": self._is_non_empty_response(response),
        }

    def _count_tokens(self, text: str, *, function_name: str) -> int | None:
        if not text:
            return 0

        provider = "deepseek" if function_name == "askds" else "chatgpt"
        force_for_askds = function_name == "askds"

        if not hasattr(self._llm, "count_tokens"):
            if force_for_askds:
                logger.warning("Tokenizer unavailable for askds; fallback token count=-1")
                return -1
            return None

        try:
            tokens = self._llm.count_tokens(text, provider=provider)
            if tokens is None and force_for_askds:
                logger.warning("Tokenizer returned None for askds; fallback token count=-1")
                return -1
            return tokens
        except Exception as error:
            if force_for_askds:
                logger.warning("Tokenizer failed for askds; fallback token count=-1 error=%s", error)
                return -1
            logger.debug("Token counting failed function=%s error=%s", function_name, error)
            return None

    @staticmethod
    def _build_email_summary_prompt(user_query: str, response_text: str) -> str:
        template = config.get_text("bot.email_summary_prompt_template")
        return template.format(user_query=user_query, response_text=response_text)

    def _call_llm_result(
        self,
        prompt: str,
        *,
        provider: str,
        model: str | None = None,
    ):
        if hasattr(self._llm, "get_llm_response_result"):
            return self._llm.get_llm_response_result(prompt, provider=provider, model=model)

        from services.service_result import failure, success

        try:
            data = self._llm.get_llm_response(prompt, provider=provider, model=model)
            return success(data)
        except Exception as error:
            return failure("LLM_CALL_FAILED", str(error))

    def _call_longbridge_quote_result(self, *, symbols: list[str]):
        if hasattr(self._longbridge, "get_inspected_quotes_result"):
            return self._longbridge.get_inspected_quotes_result(symbols=symbols)

        from services.service_result import failure, success

        try:
            data = self._longbridge.get_inspected_quotes_text(symbols=symbols)
            return success(data)
        except Exception as error:
            return failure("LONGBRIDGE_SNAPSHOT_FAILED", str(error))

    def _maybe_send_function_email(
        self,
        *,
        function_name: str,
        chat_id: int,
        user_query: str,
        response: Any,
        is_success: bool,
    ) -> None:
        record = self._write_query_record(
            function_name=function_name,
            chat_id=chat_id,
            user_query=user_query,
            response=response,
            is_success=is_success,
        )

        if is_success:
            return

        if function_name not in self._email_notify_functions:
            return

        if not self._is_gmail_configured():
            logger.warning(config.get_text("email.gmail_incomplete_log"))
            return

        subject_template = config.get_text("bot.email_subject_template")
        subject = subject_template.format(chat_id=chat_id, function_name=function_name)

        summary_text = config.get_text("email.summary_generation_failed")
        try:
            llm_result = self._call_llm_result(
                self._build_email_summary_prompt(user_query=user_query, response_text=record["response_text"]),
                model=DEEPSEEK_MODEL,
                provider="deepseek",
            )
            if llm_result.ok:
                summary_text = str(llm_result.data or "").strip()
            else:
                template = config.get_text("email.summary_generation_failed_log")
                logger.error(
                    template.format(
                        function_name=function_name,
                        error=llm_result.error_msg or llm_result.error_code,
                    )
                )
        except Exception as summary_error:
            template = config.get_text("email.summary_generation_failed_log")
            logger.error(template.format(function_name=function_name, error=summary_error))

        body_template = config.get_text("bot.email_body_template")
        body = body_template.format(
            summary=summary_text,
            response_is_empty=(not record["response_non_empty"]),
            is_success=is_success,
        )
        body = "\n".join(
            [
                body,
                f"record_id: {record['record_id']}",
                f"category: {record['category']}",
                f"keywords: {','.join(record['keywords'])}",
                f"detail_file: {record['detail_path']}",
            ]
        )
        attachment_paths = [str(record["detail_path"])]

        try:
            if hasattr(self._llm, "send_gmail_result"):
                send_result = self._llm.send_gmail_result(
                    sender=self._config.GMAIL_SENDER,
                    app_password=self._config.GMAIL_APP_PASSWORD,
                    to=self._config.GMAIL_TO_LIST,
                    subject=subject,
                    body=body,
                    cc=self._config.GMAIL_CC_LIST,
                    attachments=attachment_paths,
                )
            else:
                self._gmail_sender(
                    sender=self._config.GMAIL_SENDER,
                    app_password=self._config.GMAIL_APP_PASSWORD,
                    to=self._config.GMAIL_TO_LIST,
                    subject=subject,
                    body=body,
                    cc=self._config.GMAIL_CC_LIST,
                    attachments=attachment_paths,
                )
                from services.service_result import success

                send_result = success()
            if not send_result.ok:
                template = config.get_text("email.email_notification_failed_log")
                logger.error(
                    template.format(
                        function_name=function_name,
                        error=send_result.error_msg or send_result.error_code,
                    )
                )
        except Exception as email_error:
            template = config.get_text("email.email_notification_failed_log")
            logger.error(template.format(function_name=function_name, error=email_error))

    def _handle_askds_reply(self, bot, message) -> bool:
        chat_id = message.chat.id
        if not self._consume_pending(self._pending_askds, chat_id):
            return False

        prompt = (message.text or "").strip()
        llm_result = self._call_llm_result(
            prompt,
            model=DEEPSEEK_MODEL,
            provider="deepseek",
        )
        if llm_result.ok:
            reply = str(llm_result.data or "")
            is_success = True
        else:
            template = config.get_text("bot.askds_error_template")
            reply = template.format(error=llm_result.error_msg or llm_result.error_code)
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
        llm_result = self._call_llm_result(
            prompt,
            model=config.CHATGPT_MODEL,
            provider="chatgpt",
        )
        if llm_result.ok:
            reply = str(llm_result.data or "")
            is_success = True
        else:
            template = config.get_text("bot.askchatgpt_error_template")
            reply = template.format(error=llm_result.error_msg or llm_result.error_code)
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

        llm_result = self._call_llm_result(
            prompt,
            model=config.CHATGPT_MODEL,
            provider="chatgpt",
        )
        if llm_result.ok:
            analysis_reply = str(llm_result.data or "")
            is_success = True
        else:
            template = config.get_text("bot.askstock_analysis_error_template")
            analysis_reply = template.format(error=llm_result.error_msg or llm_result.error_code)
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
            invalid_text = self.get_askstock_invalid_text()
            bot.reply_to(message, invalid_text)
            self._maybe_send_function_email(
                function_name="askstock",
                chat_id=chat_id,
                user_query=user_text,
                response=invalid_text,
                is_success=False,
            )
            return True

        stock_result = self._call_longbridge_quote_result(symbols=symbols)

        if stock_result.ok:
            reply = str(stock_result.data or "")
            is_success = True
        else:
            template = config.get_text("bot.askstock_error_template")
            reply = template.format(error=stock_result.error_msg or stock_result.error_code)
            is_success = False

        if reply:
            # askstock-specific behavior: send .txt instead of chunked text for very long responses.
            if len(reply) > 4000:
                sent = self.send_text_as_file(bot, message, reply, filename_prefix="askstock")
                if not sent:
                    self.send_long_reply(bot, message, reply)
            else:
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

