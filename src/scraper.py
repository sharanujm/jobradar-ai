import logging
import time
from typing import List, Dict
import pandas as pd
from jobspy import scrape_jobs

from .database import save_job, get_stats
from .filter import clean_and_normalize_job, is_matching_job
from .internshala_scraper import scrape_internshala

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("JobScraper")

def scrape_all_sources(config: dict) -> int:
    """
    Executes job search across configured sites:
    LinkedIn, Indeed, Glassdoor, Google Jobs, Naukri, and Internshala
    for all target roles and locations.
    Saves newly found jobs to the SQLite database.
    Returns the total number of newly discovered jobs saved.
    """
    search_cfg = config.get("search", {})
    roles = search_cfg.get("roles", ["Software Engineer"])
    locations = search_cfg.get("locations", ["India"])
    configured_platforms = search_cfg.get("platforms", ["linkedin", "indeed", "glassdoor", "google", "naukri", "internshala"])
    country_indeed = search_cfg.get("country_indeed", "india")
    results_wanted = search_cfg.get("results_per_platform", 15)
    hours_old = search_cfg.get("hours_old", 48)

    # Separate platforms handled by JobSpy vs custom scrapers
    jobspy_supported = {"linkedin", "indeed", "glassdoor", "google", "naukri", "ziprecruiter"}
    jobspy_platforms = [p.lower() for p in configured_platforms if p.lower() in jobspy_supported]
    if not jobspy_platforms:
        jobspy_platforms = ["linkedin", "indeed", "google", "naukri"]

    logger.info(f"Starting Multi-Source Scraper: {len(roles)} roles, {len(locations)} locations.")
    logger.info(f"Active Platforms: JobSpy={jobspy_platforms}, Internshala={'internshala' in [p.lower() for p in configured_platforms]}")
    
    total_new_jobs = 0

    # 1. Scrape JobSpy sources (LinkedIn, Indeed, Glassdoor, Google Jobs, Naukri)
    for role in roles:
        for loc in locations:
            logger.info(f"🔎 Searching '{role}' in '{loc}' on {jobspy_platforms}...")
            try:
                df = scrape_jobs(
                    site_name=jobspy_platforms,
                    search_term=role,
                    location=loc,
                    results_wanted=results_wanted,
                    hours_old=hours_old,
                    country_indeed=country_indeed,
                    verbose=0
                )

                if df is not None and not df.empty:
                    records = df.to_dict(orient="records")
                    logger.info(f"  Raw jobs fetched from JobSpy: {len(records)}")

                    for raw_job in records:
                        normalized = clean_and_normalize_job(raw_job)
                        if not is_matching_job(normalized, config):
                            continue

                        is_new = save_job(normalized)
                        if is_new:
                            total_new_jobs += 1
                            logger.info(f"  ✨ [NEW] {normalized['title']} @ {normalized['company']} ({normalized['site']})")

            except Exception as e:
                logger.error(f"  Error searching '{role}' in '{loc}': {e}", exc_info=False)

            time.sleep(2)

    # 2. Scrape Internshala (Software Developer, Fresher, Remote, Internships)
    if any("internshala" in p.lower() for p in configured_platforms):
        try:
            logger.info("🎓 Scraping fresh opportunities from Internshala...")
            internshala_jobs = scrape_internshala(limit_per_category=results_wanted)
            for j in internshala_jobs:
                if not is_matching_job(j, config):
                    continue
                is_new = save_job(j)
                if is_new:
                    total_new_jobs += 1
                    logger.info(f"  ✨ [NEW INTERNSHALA] {j['title']} @ {j['company']}")
        except Exception as e:
            logger.error(f"Error scraping Internshala: {e}")

    # 3. Scrape Expanded Sources: Instahyre, RemoteOK, Remotive, WeWorkRemotely, Arbeitnow
    try:
        logger.info("🌐 Scraping expanded tech platforms (Instahyre, RemoteOK, Remotive, WeWorkRemotely, Arbeitnow)...")
        from .multi_platform_scraper import scrape_all_additional_sources
        additional_jobs = scrape_all_additional_sources(roles=roles)
        for j in additional_jobs:
            if not is_matching_job(j, config):
                continue
            is_new = save_job(j)
            if is_new:
                total_new_jobs += 1
                logger.info(f"  ✨ [NEW {j['site'].upper()}] {j['title']} @ {j['company']}")
    except Exception as e:
        logger.error(f"Error scraping expanded platforms: {e}")

    stats = get_stats()
    logger.info(f"Scraping completed! Added {total_new_jobs} new jobs. Total in DB: {stats['total']}, Pending for email: {stats['pending']}")
    return total_new_jobs

if __name__ == "__main__":
    from .config_loader import load_config
    cfg = load_config()
    scrape_all_sources(cfg)
