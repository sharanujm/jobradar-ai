import logging
import requests
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("JobRadarTelegram")

def test_telegram_connection(bot_token: str, chat_id: str) -> Tuple[bool, str]:
    """
    Tests Telegram bot connection by sending a verified hello test message.
    100% Free - uses official Telegram Bot API without any charges.
    """
    token = (bot_token or "").strip()
    cid = (chat_id or "").strip()

    if not token or not cid:
        return False, "Bot Token and Chat ID are required."

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    text = (
        "🤖 <b>JobRadar AI &bull; Telegram Alerts Connected!</b>\n\n"
        "✅ Your Telegram alerts are now configured successfully!\n"
        "You will receive instant alerts for high-matching Software Developer roles directly to your phone.\n\n"
        "<i>Happy Job Hunting! 🚀</i>"
    )

    try:
        resp = requests.post(
            url,
            json={
                "chat_id": cid,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            },
            timeout=10
        )
        data = resp.json()
        if resp.status_code == 200 and data.get("ok"):
            return True, "Test alert sent successfully to your Telegram!"
        else:
            err_desc = data.get("description", "Unknown Telegram API error")
            return False, f"Telegram API error: {err_desc}"
    except Exception as e:
        logger.error(f"Telegram connection error: {e}")
        return False, f"Connection failed: {str(e)}"

def send_telegram_job_alert(
    bot_token: str, 
    chat_id: str, 
    job: dict, 
    match_score: int = 0, 
    skills: Optional[List[str]] = None
) -> bool:
    """
    Sends an instant, beautifully formatted alert for a high-match job opportunity.
    """
    token = (bot_token or "").strip()
    cid = (chat_id or "").strip()

    if not token or not cid:
        return False

    title = job.get("title", "Software Engineer")
    company = job.get("company", "Company")
    location = job.get("location", "India / Remote")
    site = (job.get("site", "Web")).capitalize()
    job_url = job.get("job_url", "#")
    salary = job.get("salary")
    is_remote = job.get("is_remote")

    score_badge = f"⚡ <b>{match_score}% Match</b>" if match_score else "✨ <b>New Role</b>"
    remote_tag = " | 🌐 Remote" if is_remote else ""
    salary_tag = f"\n💰 <b>Compensation:</b> {salary}" if salary else ""

    skills_text = ""
    if skills:
        matched = [s for s in skills if s.lower() in (job.get("snippet", "") + " " + title).lower()]
        if matched:
            skills_text = f"\n🎯 <b>Matching Skills:</b> {', '.join(matched[:5])}"

    msg = (
        f"🚀 <b>New Opportunity Found!</b> ({score_badge})\n\n"
        f"💼 <b>Role:</b> {title}\n"
        f"🏢 <b>Company:</b> {company}\n"
        f"📍 <b>Location:</b> {location}{remote_tag}\n"
        f"📌 <b>Source:</b> {site}"
        f"{salary_tag}"
        f"{skills_text}\n\n"
        f"👉 <a href=\"{job_url}\"><b>View &amp; Apply Now &rarr;</b></a>"
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={
                "chat_id": cid,
                "text": msg,
                "parse_mode": "HTML",
                "disable_web_page_preview": False
            },
            timeout=10
        )
        return resp.status_code == 200 and resp.json().get("ok", False)
    except Exception as e:
        logger.error(f"Error sending Telegram job alert: {e}")
        return False
