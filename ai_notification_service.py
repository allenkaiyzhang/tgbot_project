"""AI + notification service.

Main APIs:
- get_llm_response(...)
- send_gmail(...)
"""

from __future__ import annotations

import argparse
import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable

from openai import OpenAI

import config

_DEEPSEEK_CLIENT = OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)

_CHATGPT_CLIENT = OpenAI(
    api_key=config.CHATGPT_API_KEY,
    base_url=config.CHATGPT_BASE_URL,
)


def get_llm_response(
    prompt: str,
    *,
    provider: str = "deepseek",
    model: str | None = None,
    system_prompt: str = "You are a helpful assistant",
) -> str:
    """Call DeepSeek/ChatGPT and return plain text content."""

    key = provider.strip().lower()
    if key == "deepseek":
        client = _DEEPSEEK_CLIENT
        resolved_model = model or "deepseek-chat"
    elif key in {"chatgpt", "openai"}:
        client = _CHATGPT_CLIENT
        resolved_model = model or config.CHATGPT_MODEL
    else:
        raise ValueError(f"Unsupported provider: {provider}")

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
        raise ValueError("Parameter 'to' cannot be empty.")

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

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, app_password)
        smtp.send_message(msg, from_addr=sender, to_addrs=to_list + cc_list)


def main() -> None:
    """Manual test entrypoint for llm/email."""

    parser = argparse.ArgumentParser(description="Test AI + notification service.")
    parser.add_argument(
        "--mode",
        choices=["llm", "email"],
        default="llm",
        help="Test mode",
    )
    parser.add_argument(
        "--provider",
        default="deepseek",
        choices=["deepseek", "chatgpt", "openai"],
        help="LLM provider name (llm mode only)",
    )
    parser.add_argument(
        "--prompt",
        default="Say hello in one short sentence.",
        help="Prompt text for llm mode",
    )
    parser.add_argument("--model", default=None, help="Optional model override for llm mode")
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
            print(f"LLM test failed: {error}")
        return

    try:
        send_gmail(
            sender=config.GMAIL_SENDER,
            app_password=config.GMAIL_APP_PASSWORD,
            to=config.GMAIL_TO_LIST,
            subject="ai_notification_service test",
            body="This is a test email from ai_notification_service.py",
            cc=config.GMAIL_CC_LIST,
        )
        print("Test email sent.")
    except Exception as error:
        print(f"Email test failed: {error}")


if __name__ == "__main__":
    main()
