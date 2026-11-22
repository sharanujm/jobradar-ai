import logging
import re
import html
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger("MultiPlatformScraper")

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, application/xhtml+xml, application/xml;q=0.9, */*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

def clean_html_text(raw_html: str) -> str:
    """Strips HTML tags and unescapes entities."""
    if not raw_html:
        return ""
    text = re.sub(r'<[^>]+>', ' ', str(raw_html))
    text = html.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()

# ------------------------------------------------------------------------------
# 1. Instahyre Scraper (Top Indian Tech & Startup Platform)
# ------------------------------------------------------------------------------
def scrape_instahyre(roles_or_skills: List[str] = None, limit_per_skill: int = 25) -> List[Dict[str, Any]]:
    """
    Scrapes fresh India tech opportunities from Instahyre's job search API.
    Covers top tech companies in Bangalore, Hyderabad, Pune, Gurgaon, Remote.
    """
    if not roles_or_skills:
        roles_or_skills = ["Python", "Java", "React", "Frontend", "Backend", "Full Stack"]

    jobs = []
    seen_ids = set()

    for skill in roles_or_skills[:5]:
        try:
            url = f"https://www.instahyre.com/api/v1/job_search?skills={skill.replace(' ', '+')}&offset=0"
            res = requests.get(url, headers=REQUEST_HEADERS, timeout=12)
            if res.status_code != 200:
                continue
            data = res.json()
            raw_jobs = data.get("objects", []) if isinstance(data, dict) else []

            for item in raw_jobs[:limit_per_skill]:
                job_id = str(item.get("id") or "")
                if not job_id or job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                employer = item.get("employer", {}) or {}
                company = employer.get("company_name") or "Leading Tech Startup"
                title = item.get("title") or f"{skill} Developer"

                # Locations can be a string or list
                loc_raw = item.get("locations")
                if isinstance(loc_raw, list):
                    loc_str = ", ".join(str(l) for l in loc_raw if l)
                elif isinstance(loc_raw, str):
                    loc_str = loc_raw
                else:
                    loc_str = "India"

                is_remote = 1 if "remote" in loc_str.lower() or "work from home" in loc_str.lower() else 0

                # Keywords / Skills
                keywords = item.get("keywords") or []
                if isinstance(keywords, list):
                    snippet = f"Skills: {', '.join(keywords[:7])}."
                else:
                    snippet = f"Skills: {keywords}."

                job_url = item.get("public_url")
                if not job_url:
                    company_slug = company.lower().replace(" ", "-")
                    job_url = f"https://www.instahyre.com/job-{job_id}-at-{company_slug}"

                jobs.append({
                    "id": f"instahyre_{job_id}",
                    "site": "instahyre",
                    "title": title,
                    "company": company,
                    "location": loc_str,
                    "job_url": job_url,
                    "date_posted": datetime.now().strftime("%Y-%m-%d"),
                    "job_type": "Full-time",
                    "salary": "",
                    "is_remote": is_remote,
                    "snippet": snippet[:500]
                })

        except Exception as e:
            logger.warning(f"Error scraping Instahyre for '{skill}': {e}")

    logger.info(f"Instahyre fetched {len(jobs)} active Indian tech roles.")
    return jobs

# ------------------------------------------------------------------------------
# 2. RemoteOK Scraper (Premier Global Remote Platform)
# ------------------------------------------------------------------------------
def scrape_remoteok(limit: int = 30) -> List[Dict[str, Any]]:
    """
    Fetches verified global remote software engineering positions from RemoteOK.
    """
    jobs = []
    try:
        url = "https://remoteok.com/api"
        res = requests.get(url, headers=REQUEST_HEADERS, timeout=12)
        if res.status_code != 200:
            return []
        items = res.json()
        if not isinstance(items, list):
            return []

        # First item is legal notice; skip it
        for item in items[1:]:
            if not isinstance(item, dict):
                continue
            position = item.get("position", "")
            if not position:
                continue

            company = item.get("company", "Remote Tech Co")
            job_id = str(item.get("id") or item.get("epoch") or "")
            tags = item.get("tags") or []
            tags_str = ", ".join(tags[:6])

            location = item.get("location") or "Worldwide / Remote"
            if not location.strip():
                location = "Worldwide / Remote"

            salary_min = item.get("salary_min")
            salary_max = item.get("salary_max")
            salary_str = ""
            if salary_min and salary_max:
                salary_str = f"${salary_min:,} - ${salary_max:,} USD"
            elif salary_min:
                salary_str = f"${salary_min:,}+ USD"

            desc = clean_html_text(item.get("description", ""))
            snippet = f"Skills: {tags_str}. " + desc[:300] if desc else f"Skills: {tags_str}"

            job_url = item.get("url") or f"https://remoteok.com/remote-jobs/{job_id}"
            if not job_url.startswith("http"):
                job_url = f"https://remoteok.com{job_url}"

            jobs.append({
                "id": f"remoteok_{job_id}",
                "site": "remoteok",
                "title": position,
                "company": company,
                "location": location,
                "job_url": job_url,
                "date_posted": item.get("date", "")[:10] or datetime.now().strftime("%Y-%m-%d"),
                "job_type": "Full-time",
                "salary": salary_str,
                "is_remote": 1,
                "snippet": snippet[:500]
            })

            if len(jobs) >= limit:
                break

    except Exception as e:
        logger.warning(f"Error scraping RemoteOK: {e}")

    logger.info(f"RemoteOK fetched {len(jobs)} global remote positions.")
    return jobs

# ------------------------------------------------------------------------------
# 3. WeWorkRemotely (WWR) RSS Scraper
# ------------------------------------------------------------------------------
def scrape_weworkremotely(limit: int = 30) -> List[Dict[str, Any]]:
    """
    Fetches verified programming jobs from WeWorkRemotely's programming RSS feed.
    """
    jobs = []
    try:
        url = "https://weworkremotely.com/categories/remote-programming-jobs.rss"
        res = requests.get(url, headers=REQUEST_HEADERS, timeout=12)
        if res.status_code != 200:
            return []

        root = ET.fromstring(res.content)
        items = root.findall(".//item")

        for item in items[:limit]:
            title_elem = item.find("title")
            link_elem = item.find("link")
            desc_elem = item.find("description")
            pub_elem = item.find("pubDate")

            raw_title = title_elem.text if title_elem is not None else ""
            if not raw_title:
                continue

            # Title is formatted as "Company Name: Job Title"
            if ":" in raw_title:
                company, title = raw_title.split(":", 1)
                company = company.strip()
                title = title.strip()
            else:
                company = "Remote Tech"
                title = raw_title.strip()

            job_url = link_elem.text if link_elem is not None else ""
            raw_desc = desc_elem.text if desc_elem is not None else ""
            clean_desc = clean_html_text(raw_desc)[:450]

            job_id_match = re.search(r'/remote-jobs/(\d+)', job_url)
            job_id = job_id_match.group(1) if job_id_match else str(abs(hash(job_url)))[:12]

            jobs.append({
                "id": f"wwr_{job_id}",
                "site": "weworkremotely",
                "title": title,
                "company": company,
                "location": "Remote / Worldwide",
                "job_url": job_url,
                "date_posted": datetime.now().strftime("%Y-%m-%d"),
                "job_type": "Full-time",
                "salary": "",
                "is_remote": 1,
                "snippet": clean_desc
            })

    except Exception as e:
        logger.warning(f"Error scraping WeWorkRemotely RSS: {e}")

    logger.info(f"WeWorkRemotely fetched {len(jobs)} remote roles.")
    return jobs

# ------------------------------------------------------------------------------
# 4. Remotive API Scraper
# ------------------------------------------------------------------------------
def scrape_remotive(limit: int = 30) -> List[Dict[str, Any]]:
    """
    Fetches software engineering roles from Remotive's public developer API.
    """
    jobs = []
    try:
        url = "https://remotive.com/api/remote-jobs?category=software-dev&limit=40"
        res = requests.get(url, headers=REQUEST_HEADERS, timeout=12)
        if res.status_code != 200:
            return []
        data = res.json()
        raw_jobs = data.get("jobs", []) if isinstance(data, dict) else []

        for item in raw_jobs[:limit]:
            job_id = str(item.get("id") or "")
            title = item.get("title") or "Software Engineer"
            company = item.get("company_name") or "Remote Tech"
            req_loc = item.get("candidate_required_location") or "Worldwide / Anywhere"
            job_url = item.get("url") or f"https://remotive.com/remote-jobs/software-dev/{job_id}"
            salary = item.get("salary") or ""
            desc = clean_html_text(item.get("description", ""))[:450]

            jobs.append({
                "id": f"remotive_{job_id}",
                "site": "remotive",
                "title": title,
                "company": company,
                "location": f"Remote / {req_loc}",
                "job_url": job_url,
                "date_posted": (item.get("publication_date") or "")[:10] or datetime.now().strftime("%Y-%m-%d"),
                "job_type": "Full-time",
                "salary": salary,
                "is_remote": 1,
                "snippet": desc
            })

    except Exception as e:
        logger.warning(f"Error scraping Remotive: {e}")

    logger.info(f"Remotive fetched {len(jobs)} remote software positions.")
    return jobs

# ------------------------------------------------------------------------------
# 5. Arbeitnow API Scraper
# ------------------------------------------------------------------------------
def scrape_arbeitnow(limit: int = 30) -> List[Dict[str, Any]]:
    """
    Fetches engineering roles from Arbeitnow's public job API.
    """
    jobs = []
    try:
        url = "https://www.arbeitnow.com/api/job-board-api"
        res = requests.get(url, headers=REQUEST_HEADERS, timeout=12)
        if res.status_code != 200:
            return []
        data = res.json()
        raw_jobs = data.get("data", []) if isinstance(data, dict) else []

        for item in raw_jobs:
            title = item.get("title") or ""
            if not title:
                continue

            slug = item.get("slug") or str(abs(hash(item.get("url", ""))))
            company = item.get("company_name") or "Tech Firm"
            is_remote = 1 if item.get("remote") else 0
            loc = item.get("location") or ("Remote" if is_remote else "Global")
            tags = item.get("tags") or []
            tags_str = ", ".join(tags[:5])
            desc = clean_html_text(item.get("description", ""))[:400]
            snippet = f"Tags: {tags_str}. " + desc if tags_str else desc

            jobs.append({
                "id": f"arbeitnow_{slug[:32]}",
                "site": "arbeitnow",
                "title": title,
                "company": company,
                "location": loc,
                "job_url": item.get("url") or f"https://www.arbeitnow.com/view/{slug}",
                "date_posted": datetime.now().strftime("%Y-%m-%d"),
                "job_type": "Full-time",
                "salary": "",
                "is_remote": is_remote,
                "snippet": snippet
            })

            if len(jobs) >= limit:
                break

    except Exception as e:
        logger.warning(f"Error scraping Arbeitnow: {e}")

    logger.info(f"Arbeitnow fetched {len(jobs)} active engineering positions.")
    return jobs

# ------------------------------------------------------------------------------
# Aggregator
# ------------------------------------------------------------------------------
def scrape_all_additional_sources(roles: List[str] = None) -> List[Dict[str, Any]]:
    """
    Runs all 5 expanded job scrapers (Instahyre, RemoteOK, Remotive, WWR, Arbeitnow)
    and returns a combined list of deduplicated, normalized jobs.
    """
    all_jobs = []
    all_jobs.extend(scrape_instahyre(roles_or_skills=roles, limit_per_skill=25))
    all_jobs.extend(scrape_remoteok(limit=30))
    all_jobs.extend(scrape_weworkremotely(limit=30))
    all_jobs.extend(scrape_remotive(limit=30))
    all_jobs.extend(scrape_arbeitnow(limit=30))

    logger.info(f"Total jobs collected across expanded platforms: {len(all_jobs)}")
    return all_jobs
