"""Reusable Gmail sending utility."""

from __future__ import annotations

import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable

import config


def send_gmail(
    sender: str,
    app_password: str,
    to: Iterable[str],
    subject: str,
    body: str,
    cc: Iterable[str] | None = None,
    attachments: Iterable[str] | None = None,
) -> None:
    """Send an email via Gmail SMTP (SSL)."""

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
    """Send a minimal test email using values from config/.env."""

    send_gmail(
        sender=config.GMAIL_SENDER,
        app_password=config.GMAIL_APP_PASSWORD,
        to=config.GMAIL_TO_LIST,
        subject="gmail_service test",
        body="This is a test email from gmail_service.py",
        cc=config.GMAIL_CC_LIST,
    )
    print("Test email sent.")


if __name__ == "__main__":
    main()
