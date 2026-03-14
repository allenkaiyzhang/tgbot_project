"""AI + notification service.

Main APIs:
- get_llm_response(...)
- send_gmail(...)
"""

from __future__ import annotations

import argparse
import logging
import mimetypes
import smtplib
from functools import lru_cache
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable

from openai import OpenAI

import config
from services.service_result import ServiceResult, failure, success

logger = logging.getLogger(__name__)
TOKENIZER_DIR = Path(__file__).resolve().parents[1] / "tools" / "deepseek_v3_tokenizer"

_DEEPSEEK_CLIENT = OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.get_text("llm.deepseek_base_url"),
)

_CHATGPT_CLIENT = OpenAI(
    api_key=config.CHATGPT_API_KEY,
    base_url=config.CHATGPT_BASE_URL,
)


def get_llm_response(
    prompt: str,
    *,
    provider: str = config.get_text("llm.provider"),
    model: str | None = None,
    system_prompt: str = config.get_text("llm.system_prompt"),
) -> str:
    """Call DeepSeek/ChatGPT and return plain text content."""

    key = provider.strip().lower()
    if key == "deepseek":
        client = _DEEPSEEK_CLIENT
        resolved_model = model or config.get_text("llm.deepseek_model")
    elif key in set(config.get_text("llm.chatgpt_aliases")):
        client = _CHATGPT_CLIENT
        resolved_model = model or config.CHATGPT_MODEL
    else:
        template = config.get_text("llm.unsupported_provider_error")
        raise ValueError(template.format(provider=provider))

    response = client.chat.completions.create(
        model=resolved_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        stream=False,
    )
    return response.choices[0].message.content or ""


def send_gmail(
    sender: str,
    app_password: str,
    to: Iterable[str],
    subject: str,
    body: str,
    cc: Iterable[str] | None = None,
    attachments: Iterable[str] | None = None,
) -> None:
    """Send an email via Gmail SMTP SSL endpoint."""

    to_list = list(to)
    cc_list = list(cc or [])
    attachment_list = list(attachments or [])

    if not to_list:
        raise ValueError(config.get_text("email.to_empty_error"))

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(to_list)
    msg["Subject"] = subject
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    msg.set_content(body)

    for file_path in attachment_list:
        path = Path(file_path)
        with path.open("rb") as file:
            data = file.read()

        mime_type, _ = mimetypes.guess_type(path.name)
        if mime_type:
            maintype, subtype = mime_type.split("/", 1)
        else:
            maintype, subtype = "application", "octet-stream"
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=path.name)

    smtp_host = config.get_text("email.smtp_host")
    smtp_port = int(config.get_text("email.smtp_port"))
    with smtplib.SMTP_SSL(smtp_host, smtp_port) as smtp:
        smtp.login(sender, app_password)
        smtp.send_message(msg, from_addr=sender, to_addrs=to_list + cc_list)


@lru_cache(maxsize=1)
def _load_deepseek_tokenizer():
    try:
        import transformers  # type: ignore
    except Exception as error:
        logger.warning("DeepSeek tokenizer unavailable: transformers import failed: %s", error)
        return None

    if not TOKENIZER_DIR.exists():
        logger.warning("DeepSeek tokenizer unavailable: missing directory %s", TOKENIZER_DIR)
        return None

    try:
        return transformers.AutoTokenizer.from_pretrained(str(TOKENIZER_DIR), trust_remote_code=True)
    except Exception as error:
        logger.warning("DeepSeek tokenizer load failed: %s", error)
        return None


def count_tokens(text: str, *, provider: str = "deepseek") -> int | None:
    """Count tokens using DeepSeek tokenizer.

    Note:
    - accurate for DeepSeek-style tokenization
    - for ChatGPT/OpenAI this is only an approximation and may differ
    """

    tokenizer = _load_deepseek_tokenizer()
    if tokenizer is None:
        return None

    if provider.strip().lower() in set(config.get_text("llm.chatgpt_aliases")):
        logger.debug("Using DeepSeek tokenizer for ChatGPT text as approximation.")

    try:
        return len(tokenizer.encode(text))
    except Exception as error:
        logger.warning("DeepSeek tokenizer encode failed: %s", error)
        return None


def get_llm_response_result(
    prompt: str,
    *,
    provider: str = config.get_text("llm.provider"),
    model: str | None = None,
    system_prompt: str = config.get_text("llm.system_prompt"),
) -> ServiceResult:
    """Call LLM and return unified service result."""

    try:
        return success(
            get_llm_response(
                prompt,
                provider=provider,
                model=model,
                system_prompt=system_prompt,
            )
        )
    except Exception as error:
        logger.error("LLM call failed provider=%s error=%s", provider, error)
        return failure("LLM_CALL_FAILED", str(error))


def send_gmail_result(
    sender: str,
    app_password: str,
    to: Iterable[str],
    subject: str,
    body: str,
    cc: Iterable[str] | None = None,
    attachments: Iterable[str] | None = None,
) -> ServiceResult:
    """Send email and return unified service result."""

    try:
        send_gmail(
            sender=sender,
            app_password=app_password,
            to=to,
            subject=subject,
            body=body,
            cc=cc,
            attachments=attachments,
        )
        return success()
    except Exception as error:
        logger.error("Email send failed subject=%s error=%s", subject, error)
        return failure("EMAIL_SEND_FAILED", str(error))


def main() -> None:
    """Manual test entrypoint for llm/email."""

    parser = argparse.ArgumentParser(
        description=config.get_text("main.ai_notification_test_desc")
    )
    parser.add_argument(
        "--mode",
        choices=["llm", "email"],
        default="llm",
        help=config.get_text("main.ai_notification_mode_help"),
    )
    parser.add_argument(
        "--provider",
        default="deepseek",
        choices=["deepseek", "chatgpt", "openai"],
        help=config.get_text("main.ai_notification_provider_help"),
    )
    parser.add_argument(
        "--prompt",
        default=config.get_text("llm.test_llm_prompt"),
        help=config.get_text("main.ai_notification_prompt_help"),
    )
    parser.add_argument(
        "--model",
        default=None,
        help=config.get_text("main.ai_notification_model_help"),
    )
    args = parser.parse_args()

    if args.mode == "llm":
        try:
            response = get_llm_response(
                args.prompt,
                provider=args.provider,
                model=args.model,
            )
            print(response)
        except Exception as error:
            print(config.get_text("llm.test_llm_failed").format(error=error))
        return

    try:
        send_gmail(
            sender=config.GMAIL_SENDER,
            app_password=config.GMAIL_APP_PASSWORD,
            to=config.GMAIL_TO_LIST,
            subject=config.get_text("email.test_subject"),
            body=config.get_text("email.test_body"),
            cc=config.GMAIL_CC_LIST,
        )
        print(config.get_text("email.test_sent"))
    except Exception as error:
        print(config.get_text("email.test_failed").format(error=error))


if __name__ == "__main__":
    main()

