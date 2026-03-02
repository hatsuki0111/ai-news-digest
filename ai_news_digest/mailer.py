"""メール送信（smtplib）"""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def send_digest_email(
    html: str,
    subject: str,
    email_config: dict,
) -> None:
    """HTMLダイジェストをメール送信"""
    smtp_host = email_config.get("smtp_host", "smtp.gmail.com")
    smtp_port = email_config.get("smtp_port", 587)
    smtp_user = os.environ.get("SMTP_USER") or email_config.get("smtp_user", "")
    smtp_password = os.environ.get("SMTP_PASSWORD") or email_config.get("smtp_password", "")
    from_address = os.environ.get("DIGEST_FROM_ADDRESS") or email_config.get("from_address", smtp_user)
    to_addresses_env = os.environ.get("DIGEST_TO_ADDRESSES")
    to_addresses = [a.strip() for a in to_addresses_env.split(",") if a.strip()] if to_addresses_env else email_config.get("to_addresses", [])

    if not to_addresses:
        logger.warning("送信先が設定されていません。メール送信をスキップします。")
        return

    if not smtp_user or not smtp_password:
        logger.warning("SMTP認証情報が設定されていません。メール送信をスキップします。")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_address
    msg["To"] = ", ".join(to_addresses)

    # プレーンテキスト版（フォールバック）
    text_part = MIMEText(
        "このメールはHTML形式です。HTMLメールに対応したクライアントでご覧ください。",
        "plain",
        "utf-8",
    )
    html_part = MIMEText(html, "html", "utf-8")
    msg.attach(text_part)
    msg.attach(html_part)

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_address, to_addresses, msg.as_string())
        logger.info("メール送信完了: %s", ", ".join(to_addresses))
    except Exception:
        logger.exception("メール送信失敗")
        raise
