import sys
import logging
from datetime import datetime
from pathlib import Path

# Configure Windows console for UTF-8 encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.config_loader import load_config
from src.scraper import scrape_all_sources
from src.database import get_unemailed_jobs, mark_jobs_as_emailed, get_stats
from src.email_builder import build_email_digest, save_html_preview
from src.email_sender import send_digest_email

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("JobRunner")

def run_job_pipeline():
    """
    Main job pipeline:
    1. Scrape matching jobs from LinkedIn, Indeed, Glassdoor, Google Jobs
    2. Filter & Deduplicate into SQLite
    3. Retrieve new pending jobs
    4. Build HTML digest & save local preview
    5. Send email to user (if credentials configured)
    """
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info(f"🚀 Job Search Automation Pipeline Started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    # 1. Load Config
    config = load_config()

    # 2. Run Scraper
    new_jobs_count = scrape_all_sources(config)
    logger.info(f"Scraper finished. Discovered {new_jobs_count} new unique jobs.")

    # 3. Retrieve Pending Jobs
    from src.filter import matches_experience_filter
    max_in_email = config.get("digest", {}).get("max_jobs_in_email", 100)
    exp_filter = config.get("filtering", {}).get("email_experience_filter", "1_year")
    all_pending = get_unemailed_jobs(limit=max_in_email * 4)
    pending_jobs = [j for j in all_pending if matches_experience_filter(j, exp_filter)][:max_in_email]
    logger.info(f"Found {len(pending_jobs)} unemailed matching jobs ready for digest (Filter: {exp_filter}).")

    # 4. Build Email Content
    html_content, plain_text = build_email_digest(
        jobs=pending_jobs,
        email_exp_filter=exp_filter
    )

    # 5. Save Local Preview
    preview_path = save_html_preview(html_content, config.get("digest", {}).get("preview_file", "latest_digest.html"))
    logger.info(f"📄 Generated local HTML preview at: {preview_path.resolve()}")

    if not pending_jobs:
        logger.info("No new unemailed jobs to send right now. Database is up to date!")
        return

    # 6. Format Subject Line
    subject_template = config.get("digest", {}).get(
        "email_subject", 
        "🚀 Daily Job Alert: {count} New Matching Opportunities ({date})"
    )
    today_str = datetime.now().strftime("%b %d, %Y")
    subject = subject_template.format(count=len(pending_jobs), date=today_str)

    # 7. Send Email
    email_sent = send_digest_email(
        subject=subject,
        html_content=html_content,
        plain_text_content=plain_text,
        config=config
    )

    if email_sent:
        # Mark these jobs as emailed so they won't be sent again tomorrow
        sent_ids = [j["id"] for j in pending_jobs]
        mark_jobs_as_emailed(sent_ids)
        logger.info(f"🎉 Successfully emailed {len(sent_ids)} jobs and marked them as sent.")
    else:
        logger.info(
            "ℹ️  Digest preview is available at 'latest_digest.html'. "
            "To send emails automatically, please configure your Gmail App Password in '.env'."
        )

    stats = get_stats()
    duration = (datetime.now() - start_time).total_seconds()
    logger.info("=" * 60)
    logger.info(f"🏁 Pipeline Finished in {duration:.1f}s | Total Tracked: {stats['total']} | Emailed: {stats['emailed']} | Pending: {stats['pending']}")
    logger.info("=" * 60)

if __name__ == "__main__":
    run_job_pipeline()
