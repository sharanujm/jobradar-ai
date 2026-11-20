import sys
from datetime import datetime

# Configure Windows console for UTF-8 encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.config_loader import load_config
from src.email_builder import build_email_digest
from src.email_sender import send_digest_email

def test_email():
    print("=" * 60)
    print("Testing Email Configuration...")
    print("=" * 60)

    config = load_config()
    sender = config.get("email", {}).get("sender_email")
    recipient = config.get("email", {}).get("recipient_email")

    print(f"Sender: {sender}")
    print(f"Recipient: {recipient}")

    sample_jobs = [
        {
            "id": "sample-1",
            "site": "LinkedIn",
            "title": "Software Engineer - Backend",
            "company": "Google / Tech Demo",
            "location": "Bangalore, Karnataka, India (Hybrid)",
            "job_url": "https://www.linkedin.com/jobs/",
            "date_posted": "Today",
            "salary": "INR 1,800,000 - 2,500,000 / year",
            "is_remote": True,
            "snippet": "We are seeking a talented Software Engineer to design, develop, and deploy scalable cloud backend systems and APIs."
        },
        {
            "id": "sample-2",
            "site": "Indeed",
            "title": "Full Stack Developer",
            "company": "Fast-Growing Tech Startup",
            "location": "Remote, India",
            "job_url": "https://in.indeed.com/",
            "date_posted": "1 day ago",
            "salary": "Competitive",
            "is_remote": True,
            "snippet": "Looking for a full stack engineer proficient in Python, TypeScript, and modern web application development."
        }
    ]

    subject = f"[TEST] Job Automation Email Check - {datetime.now().strftime('%H:%M:%S')}"
    html_content, plain_text = build_email_digest(sample_jobs)

    print("\nAttempting to send test email to Gmail...")
    success = send_digest_email(
        subject=subject,
        html_content=html_content,
        plain_text_content=plain_text,
        config=config
    )

    if success:
        print("\n[SUCCESS] Test email sent successfully! Please check your inbox at " + str(recipient) + " (or Spam folder).")
    else:
        print("\n[FAILED] Failed to send test email. Please check your credentials in .env.")

if __name__ == "__main__":
    test_email()
