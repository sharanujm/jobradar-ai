import sys
from datetime import datetime
from pathlib import Path

# Configure Windows console for UTF-8 encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.config_loader import load_config
from src.database import get_unemailed_jobs, mark_jobs_as_emailed, get_stats, get_user_by_email, get_unemailed_jobs_for_user
from src.email_builder import build_email_digest, save_html_preview
from src.email_sender import send_digest_email
from src.filter import matches_experience_filter

def send_digest_from_db():
    print("=" * 60)
    print("Dispatching Daily Job Digest from Database...")
    print("=" * 60)

    config = load_config()
    max_in_email = config.get("digest", {}).get("max_jobs_in_email", 100)
    recipient = config.get("email", {}).get("recipient_email") or "sharanujm@gmail.com"
    user = get_user_by_email(recipient) or {}
    exp_filter = user.get("email_experience_filter") or "1_year"
    email_roles = user.get("email_roles") or []
    email_languages = user.get("email_languages") or []
    user_name = user.get("name") or recipient.split("@")[0].capitalize()
    target_role = user.get("target_role", "Software Engineer")
    skills = user.get("skills", [])
    
    print(f"Target Recipient: {recipient} | Experience: {exp_filter} | Roles: {email_roles} | Stack: {email_languages}")
    from src.filter import matches_email_filter
    pending_jobs = get_unemailed_jobs_for_user(
        recipient, 
        limit=max_in_email, 
        experience_filter=exp_filter,
        target_roles=email_roles,
        target_languages=email_languages
    )
    if not pending_jobs:
        all_pending = get_unemailed_jobs(limit=max_in_email * 6)
        pending_jobs = [j for j in all_pending if matches_email_filter(j, exp_filter, email_roles, email_languages)][:max_in_email]

    if not pending_jobs:
        print(f"[INFO] No pending jobs matching criteria (Exp: {exp_filter}, Roles: {email_roles}, Stack: {email_languages}) to email.")
        return

    print(f"Preparing digest with {len(pending_jobs)} new matching roles...")
    
    html_content, plain_text = build_email_digest(
        jobs=pending_jobs,
        user_name=user_name,
        target_role=target_role,
        experience_level="1-2 Yrs",
        email_exp_filter=exp_filter,
        email_roles=email_roles,
        email_languages=email_languages,
        skills=skills
    )
    preview_path = save_html_preview(html_content, "latest_digest.html")
    print(f"HTML preview updated at: {preview_path}")

    today_str = datetime.now().strftime("%b %d, %Y")
    subject = f"🚀 Daily Job Alert: {len(pending_jobs)} New Software Roles Found ({today_str})"

    recipient = config.get("email", {}).get("recipient_email")
    print(f"Sending email digest to {recipient}...")

    success = send_digest_email(
        subject=subject,
        html_content=html_content,
        plain_text_content=plain_text,
        config=config
    )

    if success:
        sent_ids = [j["id"] for j in pending_jobs]
        mark_jobs_as_emailed(sent_ids)
        stats = get_stats()
        print(f"\n[SUCCESS] Daily Job Digest with {len(sent_ids)} positions was successfully sent to {recipient}!")
        print(f"Database Stats: Total Tracked: {stats['total']} | Emailed: {stats['emailed']} | Pending: {stats['pending']}")
    else:
        print("\n[ERROR] Could not send email digest. Please check your network or credentials.")

if __name__ == "__main__":
    send_digest_from_db()
