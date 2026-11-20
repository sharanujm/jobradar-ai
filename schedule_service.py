import time
import schedule
import logging
from datetime import datetime
from src.config_loader import load_config
from run_now import run_job_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SchedulerService")

def job_task():
    logger.info("⏰ Scheduled job triggered! Running job pipeline...")
    try:
        run_job_pipeline()
    except Exception as e:
        logger.error(f"Error during scheduled execution: {e}", exc_info=True)

def main():
    config = load_config()
    target_time = config.get("schedule", {}).get("time", "20:00")

    logger.info("=" * 60)
    logger.info(f"🕒 Job Automation Scheduler Service Active")
    logger.info(f"Daily execution configured for: {target_time} (8:00 PM)")
    logger.info("Press Ctrl+C at any time to stop this process.")
    logger.info("=" * 60)

    # Schedule daily task
    schedule.every().day.at(target_time).do(job_task)

    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    main()
