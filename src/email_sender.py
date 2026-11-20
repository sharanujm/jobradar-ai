import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger("EmailSender")

def send_digest_email(
    subject: str,
    html_content: str,
    plain_text_content: str,
    config: dict,
    recipient_override: Optional[str] = None
) -> bool:
    """
    Sends the generated job digest to the user's email using Gmail SMTP.
    Supports individual recipient overrides for multi-user personalized dispatches.
    Returns True if sent successfully, False otherwise.
    """
    email_cfg = config.get("email", {})
    sender = email_cfg.get("sender_email", "")
    password = email_cfg.get("sender_password", "")
    recipient = (recipient_override or email_cfg.get("recipient_email", "")).strip()
    smtp_host = email_cfg.get("smtp_host", "smtp.gmail.com")
    smtp_port = email_cfg.get("smtp_port", 465)
    use_ssl = email_cfg.get("use_ssl", True)

    # Validate credentials
    if not sender or not password or "your_email" in sender or "your_16_char" in password:
        logger.warning(
            "⚠️  Email credentials not yet configured in .env file! "
            "Please update SENDER_EMAIL and SENDER_APP_PASSWORD in .env."
        )
        return False

    if not recipient:
        recipient = sender

    # Compose message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"JobRadar AI Digest <{sender}>"
    msg["To"] = recipient

    # Attach both plain text and HTML versions
    part_text = MIMEText(plain_text_content, "plain", "utf-8")
    part_html = MIMEText(html_content, "html", "utf-8")
    msg.attach(part_text)
    msg.attach(part_html)

    logger.info(f"Connecting to SMTP server {smtp_host}:{smtp_port} to send to {recipient}...")

    try:
        if use_ssl and smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30) as server:
                server.login(sender, password)
                server.sendmail(sender, [recipient], msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                server.starttls()
                server.login(sender, password)
                server.sendmail(sender, [recipient], msg.as_string())

        logger.info(f"✅ Job digest email sent successfully to {recipient}!")
        return True

    except smtplib.SMTPAuthenticationError as e:
        logger.error(
            "❌ Gmail Authentication Failed! Make sure you are using a 16-character Google App Password, "
            "not your regular Gmail login password. See instructions in .env.example."
        )
        return False
    except Exception as e:
        logger.error(f"❌ Failed to send email to {recipient}: {e}")
        return False
