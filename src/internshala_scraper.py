import logging
import re
import requests
from bs4 import BeautifulSoup
from typing import List, Dict

logger = logging.getLogger("InternshalaScraper")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

INTERNSHALA_ENDPOINTS = [
    ("https://internshala.com/jobs/software-development-jobs/", "Software Development"),
    ("https://internshala.com/jobs/python-django-jobs/", "Python / Backend"),
    ("https://internshala.com/jobs/reactjs-jobs/", "React / Frontend"),
    ("https://internshala.com/jobs/work-from-home-software-development-jobs/", "Remote Software Engineer"),
    ("https://internshala.com/internships/software-development-internship/", "Software Development Intern")
]

def scrape_internshala(limit_per_category: int = 15) -> List[Dict]:
    """
    Scrapes software developer roles and internships from Internshala.
    Returns list of normalized raw job dictionaries.
    """
    logger.info("Scraping fresh software roles & internships from Internshala...")
    results: List[Dict] = []
    seen_urls = set()

    for url, category_name in INTERNSHALA_ENDPOINTS:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=12)
            if resp.status_code != 200:
                logger.warning(f"Internshala returned status {resp.status_code} for {url}")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select(".individual_internship")
            logger.info(f"  Found {len(cards)} listings on Internshala for '{category_name}'")

            count = 0
            for card in cards:
                if count >= limit_per_category:
                    break

                # Title
                title_el = (
                    card.select_one(".job-internship-name") or 
                    card.select_one(".profile") or 
                    card.select_one("h3.job-internship-name")
                )
                title = title_el.get_text(strip=True) if title_el else ""
                if not title:
                    continue

                # Company
                comp_el = (
                    card.select_one(".company-name") or 
                    card.select_one(".link_display_like_text") or 
                    card.select_one(".company_name")
                )
                company = comp_el.get_text(strip=True) if comp_el else "Tech Company"

                # Link
                link_el = card.select_one("a.job-title-href") or card.select_one("a.view_detail_button") or card.select_one("a[href*='/job/detail/']") or card.select_one("a[href*='/internship/detail/']")
                raw_href = link_el["href"] if link_el and "href" in link_el.attrs else ""
                if not raw_href:
                    continue
                if not raw_href.startswith("http"):
                    job_url = "https://internshala.com" + raw_href
                else:
                    job_url = raw_href

                clean_url = job_url.split("?")[0]
                if clean_url in seen_urls:
                    continue
                seen_urls.add(clean_url)

                # Location & Remote
                loc_el = card.select_one(".row-1-item.locations") or card.select_one(".location_link")
                loc_text = loc_el.get_text(strip=True) if loc_el else "India"
                is_remote = bool(
                    "work from home" in loc_text.lower() or 
                    "remote" in loc_text.lower() or 
                    "work from home" in title.lower()
                )
                if is_remote and "remote" not in loc_text.lower():
                    loc_text = f"{loc_text} (Work from home)"

                # Salary / Stipend
                sal_el = card.select_one(".row-1-item.salary") or card.select_one(".stipend")
                salary_text = sal_el.get_text(strip=True) if sal_el else ""
                if salary_text:
                    # Clean duplicate symbols
                    salary_text = re.sub(r"\s+", " ", salary_text).strip()

                # Experience
                exp_el = card.select_one(".row-1-item.experience") or card.select_one(".experience")
                exp_text = exp_el.get_text(strip=True) if exp_el else "0-1 years"

                snippet = f"{category_name} role at {company}. Experience: {exp_text}. Location: {loc_text}."
                if salary_text:
                    snippet += f" Package: {salary_text}."

                job_item = {
                    "site": "Internshala",
                    "title": title,
                    "company": company,
                    "location": loc_text,
                    "job_url": clean_url,
                    "date_posted": "Recently",
                    "job_type": "Internship" if "internship" in clean_url else "Full-time",
                    "salary": salary_text,
                    "is_remote": is_remote,
                    "snippet": snippet
                }
                results.append(job_item)
                count += 1

        except Exception as e:
            logger.error(f"Error scraping Internshala for {category_name}: {e}")

    logger.info(f"Internshala scraping finished: fetched {len(results)} valid roles.")
    return results

if __name__ == "__main__":
    jobs = scrape_internshala(5)
    for j in jobs[:3]:
        print(j["title"], "@", j["company"], "|", j["location"], "|", j["salary"])
