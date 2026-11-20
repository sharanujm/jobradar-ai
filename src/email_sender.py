import os
import json
import socket
import smtplib
import logging
import urllib.request
import urllib.error
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Tuple
from .database import get_system_setting

logger = logging.getLogger("EmailSender")

def send_via_resend(
    api_key: str, 
    recipient: str, 
    subject: str, 
    html_content: str, 
    text_content: str, 
    from_email: Optional[str] = None
) -> Tuple[bool, str]:
    """Delivers email via Resend REST API over HTTPS (port 443) - works seamlessly on Render Free Tier."""
    try:
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
            "User-Agent": "JobRadar-AI/2.0"
        }
        # Resend free tier default test sender is onboarding@resend.dev
        sender = "onboarding@resend.dev"
        if from_email and "@resend.dev" in from_email:
            sender = from_email
        elif from_email and not any(from_email.lower().endswith(d) for d in ("@gmail.com", "@yahoo.com", "@outlook.com", "@hotmail.com")):
            sender = f"JobRadar AI <{from_email}>"

        payload = {
            "from": sender,
            "to": [recipient.strip()],
            "subject": subject,
            "html": html_content,
            "text": text_content
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp_body = resp.read().decode("utf-8", errors="ignore")
            if resp.status in (200, 201):
                logger.info(f"✅ [RESEND HTTPS] Digest successfully delivered to {recipient} via HTTPS API (port 443)!")
                return True, "Delivered via Resend HTTPS API (Port 443)"
            else:
                logger.error(f"❌ [RESEND HTTPS] HTTP {resp.status}: {resp_body}")
                return False, f"Resend HTTP {resp.status}: {resp_body[:160]}"
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        logger.error(f"❌ [RESEND HTTP ERROR] {e.code}: {err_msg}")
        try:
            err_json = json.loads(err_msg)
            readable = err_json.get("message") or err_msg
        except Exception:
            readable = err_msg
        return False, f"Resend API Error ({e.code}): {readable}"
    except Exception as e:
        logger.error(f"❌ [RESEND HTTPS FAILED] {e}")
        return False, f"Resend Error: {e}"

def send_via_brevo(
    api_key: str, 
    recipient: str, 
    subject: str, 
    html_content: str, 
    text_content: str, 
    from_email: Optional[str] = None
) -> Tuple[bool, str]:
    """Delivers email via Brevo REST API over HTTPS (port 443) - works seamlessly on Render Free Tier."""
    try:
        url = "https://api.brevo.com/v3/smtp/email"
        headers = {
            "api-key": api_key.strip(),
            "Content-Type": "application/json",
            "User-Agent": "JobRadar-AI/2.0"
        }
        sender_email = from_email or "sharanujm@gmail.com"
        payload = {
            "sender": {"name": "JobRadar AI Digest", "email": sender_email},
            "to": [{"email": recipient.strip()}],
            "subject": subject,
            "htmlContent": html_content,
            "textContent": text_content
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp_body = resp.read().decode("utf-8", errors="ignore")
            if resp.status in (200, 201):
                logger.info(f"✅ [BREVO HTTPS] Digest successfully delivered to {recipient} via Brevo HTTPS API!")
                return True, "Delivered via Brevo HTTPS API (Port 443)"
            else:
                logger.error(f"❌ [BREVO HTTPS] HTTP {resp.status}: {resp_body}")
                return False, f"Brevo HTTP {resp.status}: {resp_body[:160]}"
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        logger.error(f"❌ [BREVO HTTP ERROR] {e.code}: {err_msg}")
        return False, f"Brevo API Error ({e.code}): {err_msg[:160]}"
    except Exception as e:
        logger.error(f"❌ [BREVO HTTPS FAILED] {e}")
        return False, f"Brevo Error: {e}"

def send_via_gas_webhook(
    webhook_url: str, 
    recipient: str, 
    subject: str, 
    html_content: str, 
    text_content: str
) -> Tuple[bool, str]:
    """Delivers email via user Google Apps Script Web App over HTTPS (port 443)."""
    try:
        payload = {
            "to": recipient.strip(),
            "subject": subject,
            "html": html_content,
            "text": text_content
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url.strip(),
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "JobRadar-AI/2.0"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            if resp.status in (200, 201, 302):
                logger.info(f"✅ [WEBHOOK HTTPS] Digest delivered to {recipient} via Webhook!")
                return True, "Delivered via Webhook (Port 443)"
            return False, f"Webhook HTTP {resp.status}: {body[:160]}"
    except Exception as e:
        logger.error(f"❌ [WEBHOOK FAILED] {e}")
        return False, f"Webhook Error: {e}"

def send_digest_email(
    subject: str,
    html_content: str,
    plain_text_content: str,
    config: Optional[dict] = None,
    recipient_override: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Sends the generated job digest to the candidate's email address.
    Supports:
      1. HTTPS REST API (Resend / Brevo / Webhook) via Port 443 (recommended for Render Free Tier)
      2. Direct Gmail SMTP via Port 465 (works on local machine and non-blocked environments)
    Returns (success_bool, status_message).
    """
    cfg = config or {}
    email_cfg = cfg.get("email", {})
    
    # Retrieve credentials with fallbacks (config -> env -> database)
    sender = (
        email_cfg.get("sender_email") or 
        os.getenv("SENDER_EMAIL") or 
        get_system_setting("sender_email") or 
        "sharanujm@gmail.com"
    ).strip()

    password = (
        email_cfg.get("sender_password") or 
        os.getenv("SENDER_APP_PASSWORD") or 
        get_system_setting("sender_password") or 
        get_system_setting("sender_app_password") or 
        ""
    ).strip()

    recipient = (recipient_override or email_cfg.get("recipient_email", "") or sender).strip()
    smtp_host = email_cfg.get("smtp_host") or os.getenv("SMTP_HOST") or get_system_setting("smtp_host") or "smtp.gmail.com"
    smtp_port_val = email_cfg.get("smtp_port") or os.getenv("SMTP_PORT") or get_system_setting("smtp_port") or 465
    try:
        smtp_port = int(smtp_port_val)
    except Exception:
        smtp_port = 465
    use_ssl = email_cfg.get("use_ssl", True)

    # 1. Check for HTTPS Email APIs (Resend / Brevo / Webhook) - never blocked by cloud firewalls
    resend_key = (os.getenv("RESEND_API_KEY") or get_system_setting("resend_api_key") or "").strip()
    brevo_key = (os.getenv("BREVO_API_KEY") or get_system_setting("brevo_api_key") or "").strip()
    webhook_url = (os.getenv("EMAIL_WEBHOOK_URL") or get_system_setting("email_webhook_url") or "").strip()

    resend_err = None
    if resend_key:
        logger.info(f"Connecting to Resend HTTPS API (port 443) to deliver to {recipient}...")
        ok, msg = send_via_resend(resend_key, recipient, subject, html_content, plain_text_content, from_email=sender)
        if ok:
            return True, msg
        resend_err = msg
        logger.warning(f"Resend delivery attempt failed: {msg}.")

    brevo_err = None
    if brevo_key:
        logger.info(f"Connecting to Brevo HTTPS API (port 443) to deliver to {recipient}...")
        ok, msg = send_via_brevo(brevo_key, recipient, subject, html_content, plain_text_content, from_email=sender)
        if ok:
            return True, msg
        brevo_err = msg
        logger.warning(f"Brevo delivery attempt failed: {msg}.")

    webhook_err = None
    if webhook_url:
        logger.info(f"Connecting to Webhook (port 443) to deliver to {recipient}...")
        ok, msg = send_via_gas_webhook(webhook_url, recipient, subject, html_content, plain_text_content)
        if ok:
            return True, msg
        webhook_err = msg
        logger.warning(f"Webhook delivery attempt failed: {msg}.")

    # 2. Check if running on Render Free Tier
    is_render = bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID"))
    if is_render:
        if resend_err:
            return False, f"Resend API Failed: {resend_err}"
        if brevo_err:
            return False, f"Brevo API Failed: {brevo_err}"
        if webhook_err:
            return False, f"Webhook Delivery Failed: {webhook_err}"

        diag = (
            "Render Free Tier blocks outbound SMTP ports 25, 465, and 587. "
            "To send emails directly from Render, enter a free Resend API key (from resend.com) "
            "in Cloud Delivery Settings, or run JobRadar locally with python server.py."
        )
        logger.error(f"❌ [RENDER SMTP BLOCKED] {diag}")
        return False, diag

    # 3. Traditional SMTP Delivery (works on local machine and non-blocked hosts)
    if not sender or not password or "your_email" in sender or "your_16_char" in password:
        diag = (
            "Email credentials not yet configured! "
            "Please configure SENDER_EMAIL and SENDER_APP_PASSWORD, or add a free RESEND_API_KEY."
        )
        logger.warning(f"⚠️ {diag}")
        return False, diag

    # Compose message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"JobRadar AI Digest <{sender}>"
    msg["To"] = recipient

    part_text = MIMEText(plain_text_content, "plain", "utf-8")
    part_html = MIMEText(html_content, "html", "utf-8")
    msg.attach(part_text)
    msg.attach(part_html)

    logger.info(f"Connecting to SMTP server {smtp_host}:{smtp_port} to deliver to {recipient}...")

    try:
        if use_ssl and smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=12) as server:
                server.login(sender, password)
                server.sendmail(sender, [recipient], msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=12) as server:
                server.starttls()
                server.login(sender, password)
                server.sendmail(sender, [recipient], msg.as_string())

        logger.info(f"✅ Job digest email sent successfully to {recipient} via Gmail SMTP!")
        return True, f"Delivered to {recipient} via Gmail SMTP (port {smtp_port})"

    except smtplib.SMTPAuthenticationError:
        diag = "Gmail authentication failed! Make sure you are using a 16-character Google App Password (not standard account password)."
        logger.error(f"❌ {diag}")
        return False, diag
    except (socket.timeout, TimeoutError, OSError) as e:
        diag = (
            f"SMTP connection to {smtp_host}:{smtp_port} timed out ({e}). "
            "Note: Render Free Tier blocks outbound SMTP ports 25, 465, and 587. "
            "To send emails from Render, please enter a free RESEND_API_KEY from resend.com in Cloud Delivery Settings."
        )
        logger.error(f"❌ {diag}")
        return False, diag
    except Exception as e:
        diag = f"Failed to send email to {recipient}: {e}"
        logger.error(f"❌ {diag}")
        return False, diag
