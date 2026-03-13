"""最小 Gmail 发件模块（可被其他 Python 文件直接引用）。

示例：
    from gmail_sender import send_gmail

    send_gmail(
        sender="you@gmail.com",
        app_password="xxxx xxxx xxxx xxxx",
        to=["to@example.com"],
        subject="测试标题",
        body="测试正文",
        cc=["cc@example.com"],
        attachments=["./demo.pdf"],
    )

注意：
- Gmail 通常需要使用“应用专用密码”（App Password），不要直接使用账号密码。
"""

from __future__ import annotations

import mimetypes
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Iterable


def send_gmail(
    sender: str,
    app_password: str,
    to: Iterable[str],
    subject: str,
    body: str,
    cc: Iterable[str] | None = None,
    attachments: Iterable[str] | None = None,
) -> None:
    """发送 Gmail 邮件。

    参数全部由调用方传入，适合在其他 Python 文件中直接引用。
    """
    to_list = list(to)
    cc_list = list(cc or [])
    attachment_list = list(attachments or [])

    if not to_list:
        raise ValueError("参数 to 不能为空")

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(to_list)
    msg["Subject"] = subject

    if cc_list:
        msg["Cc"] = ", ".join(cc_list)

    msg.set_content(body)

    for file_path in attachment_list:
        path = Path(file_path)
        with path.open("rb") as f:
            data = f.read()

        mime_type, _ = mimetypes.guess_type(path.name)
        if mime_type:
            maintype, subtype = mime_type.split("/", 1)
        else:
            maintype, subtype = "application", "octet-stream"

        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=path.name)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, app_password)
        smtp.send_message(msg, from_addr=sender, to_addrs=to_list + cc_list)
