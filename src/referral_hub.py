"""
src/referral_hub.py
===================
Engine for finding company seniors, alumni, tech leads, and recruiters on LinkedIn & Google X-Ray
and generating high-converting employee referral pitches for Indian Tech roles.
"""

import re
import urllib.parse
from typing import Dict, Any, Optional, List

def clean_company_name(company: str) -> str:
    """Clean company name for cleaner search query matching on LinkedIn and Google."""
    if not company:
        return "Tech Company"
    c = company.strip()

    # Common Indian tech company alias cleanups
    low = c.lower()
    if "tata consultancy" in low or low == "tcs":
        return "TCS"
    if "cognizant" in low:
        return "Cognizant"
    if "accenture" in low:
        return "Accenture"
    if "amazon" in low:
        return "Amazon"
    if "microsoft" in low:
        return "Microsoft"
    if "google" in low:
        return "Google"
    if "jpmorgan" in low or "jp morgan" in low:
        return "JPMorgan"
    if "hcl" in low:
        return "HCLTech"
    if "wipro" in low:
        return "Wipro"
    if "infosys" in low:
        return "Infosys"
    if "lloyds" in low:
        return "Lloyds"
    if "kellton" in low:
        return "Kellton Tech"

    # Remove common corporate legal suffixes
    c = re.sub(
        r'(?i)\b(pvt\.?\s*ltd\.?|private\s+limited|limited|ltd\.?|inc\.?|llc|technologies|technology|solutions|services|corp\.?|corporation|enterprises|in\s+india|india)\b',
        ' ',
        c
    )
    # Remove parenthetical text e.g. "Amazon (India)"
    c = re.sub(r'\(.*?\)', ' ', c)
    # Remove extra spaces
    cleaned = ' '.join(c.split())
    return cleaned or company.strip()

def build_linkedin_search_urls(
    company: str,
    role: str = "Software Engineer",
    college: Optional[str] = None
) -> Dict[str, str]:
    """
    Generates targeted LinkedIn and Google X-Ray search URLs that work reliably
    for free, non-premium LinkedIn users in India.
    """
    c_clean = clean_company_name(company)

    # 1. Senior Software Engineers in India
    # Note: avoid strict quotes as they cause "No results found" on standard LinkedIn accounts
    seniors_query = f"{c_clean} Senior Software Engineer India"
    seniors_url = f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(seniors_query)}&origin=GLOBAL_SEARCH_HEADER"

    # 2. Tech Leads & Lead Engineers
    leads_query = f"{c_clean} Tech Lead India"
    leads_url = f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(leads_query)}&origin=GLOBAL_SEARCH_HEADER"

    # 3. Engineering Managers & Directors
    managers_query = f"{c_clean} Engineering Manager India"
    managers_url = f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(managers_query)}&origin=GLOBAL_SEARCH_HEADER"

    # 4. Technical Recruiters & Talent Acquisition
    recruiters_query = f"{c_clean} Recruiter India"
    recruiters_url = f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(recruiters_query)}&origin=GLOBAL_SEARCH_HEADER"

    # 5. College Alumni / Seniors
    if college and college.strip():
        alumni_query = f"{c_clean} {college.strip()} India"
    else:
        alumni_query = f"{c_clean} Software Engineer India"
    alumni_url = f"https://www.linkedin.com/search/results/people/?keywords={urllib.parse.quote(alumni_query)}&origin=GLOBAL_SEARCH_HEADER"

    # 6. Google X-Ray Search for LinkedIn Profiles (Bypasses LinkedIn login walls and 0-results bugs)
    google_seniors_q = f'site:linkedin.com/in "{c_clean}" "Software Engineer" OR "Tech Lead" India'
    google_xray_url = f"https://www.google.com/search?q={urllib.parse.quote(google_seniors_q)}"

    # 7. Google X-Ray Alumni Search
    if college and college.strip():
        google_alumni_q = f'site:linkedin.com/in "{c_clean}" "{college.strip()}" India'
    else:
        google_alumni_q = f'site:linkedin.com/in "{c_clean}" "Software Engineer" India'
    google_alumni_url = f"https://www.google.com/search?q={urllib.parse.quote(google_alumni_q)}"

    # 8. Direct Company Page People Tab
    company_slug = re.sub(r'[^a-zA-Z0-9]+', '-', c_clean.lower()).strip('-')
    company_page_url = f"https://www.linkedin.com/company/{company_slug}/people/"

    return {
        "seniors_url": seniors_url,
        "leads_url": leads_url,
        "managers_url": managers_url,
        "recruiters_url": recruiters_url,
        "alumni_url": alumni_url,
        "google_xray_url": google_xray_url,
        "google_alumni_url": google_alumni_url,
        "company_page_url": company_page_url,
        "cleaned_company": c_clean
    }

def generate_referral_pitch_suite(
    job: Dict[str, Any],
    user: Dict[str, Any],
    senior_name: str = "",
    college_name: str = "",
    senior_role: str = ""
) -> Dict[str, Any]:
    """
    Generates 6 distinct, high-converting referral pitch formats tailored for Indian Tech.
    Automatically handles missing names/colleges gracefully with polished phrasing.
    """
    candidate_name = (user.get("name") or "Candidate").strip()
    candidate_email = (user.get("email") or "").strip()
    candidate_phone = (user.get("phone") or "").strip()
    github_url = (user.get("github_url") or "").strip()
    linkedin_url = (user.get("linkedin_url") or "").strip()
    portfolio_url = (user.get("portfolio_url") or "").strip()
    notice_period = (user.get("notice_period") or "Immediate / 15 Days").strip()
    exp_level = (user.get("experience_level") or "fresher").strip()

    skills = user.get("skills") or ["Python", "JavaScript", "SQL", "Git"]
    if isinstance(skills, str):
        try:
            import json
            skills = json.loads(skills)
        except Exception:
            skills = ["Software Development"]

    skills_highlight = ", ".join(skills[:4])
    primary_skill = skills[0] if skills else "Software Engineering"
    secondary_skill = skills[1] if len(skills) > 1 else "Modern Tech"

    company = (job.get("company") or "the company").strip()
    clean_comp = clean_company_name(company)
    title = (job.get("title") or "Software Engineer").strip()
    job_id = job.get("id") or "REQ-REF"
    short_ref = job_id[:8].upper() if len(job_id) > 12 else job_id
    apply_url = job.get("job_url") or ""
    location = job.get("location") or "India"

    # Intelligent name greeting
    if senior_name and senior_name.strip():
        s_name = senior_name.strip()
        senior_greeting = f"Hi {s_name},"
        senior_thanks = f"Thank you so much for your time and guidance, {s_name}!"
        manager_greeting = f"Hi {s_name},"
    else:
        senior_greeting = "Hi there,"
        senior_thanks = "Thank you so much for your time and consideration!"
        manager_greeting = "Dear Hiring Lead,"

    # Intelligent college phrasing
    active_college = college_name.strip() if college_name.strip() else (user.get("college_name") or "").strip()
    if active_college:
        college_intro = f"I am reaching out as a student/alumnus from {active_college}. I came across your profile and was really inspired by your journey at {clean_comp}."
    else:
        college_intro = f"I came across your profile while exploring the engineering team at {clean_comp} and was really inspired by your journey."

    # Portfolio / Resume line helper
    links_list = []
    if linkedin_url:
        links_list.append(f"• LinkedIn: {linkedin_url}")
    if github_url:
        links_list.append(f"• GitHub: {github_url}")
    if portfolio_url:
        links_list.append(f"• Portfolio: {portfolio_url}")
    links_block = "\n".join(links_list) if links_list else "• Resume & Projects: [Attached / Drive Link]"

    # --------------------------------------------------------------------------
    # 1. 🎓 Student / Fresher -> Senior / Alumni Referral Pitch
    # --------------------------------------------------------------------------
    fresher_pitch = f"""{senior_greeting}

Hope you are doing well!

{college_intro}

I noticed {clean_comp} has an active opening for the {title} role (Ref: {short_ref} in {location}). Having built practical projects using {skills_highlight}, I believe my skills align closely with what the team is looking for.

Quick Overview:
• Core Stack: Hands-on with {skills_highlight}
• Project Experience: Built scalable applications with clean code and REST APIs
• Availability: Ready for immediate technical assessment / joining

Could you please consider referring my profile for this opening? I would be extremely grateful for your support. Here are my credentials:

{links_block}
Job Link: {apply_url}

{senior_thanks}

Warm regards,
{candidate_name}
{candidate_email}{f' | {candidate_phone}' if candidate_phone else ''}"""

    # --------------------------------------------------------------------------
    # 2. 💼 Experienced Professional -> Tech Lead / Peer Pitch
    # --------------------------------------------------------------------------
    professional_pitch = f"""{senior_greeting}

Hope you are having a productive week.

I came across your profile while learning more about {clean_comp}'s engineering work. I am a software engineer with hands-on experience in {skills_highlight}, and I noticed an active opening for {title} (Req: {short_ref}).

Given your experience at {clean_comp}, I wanted to check if you would be open to referring me internally for this role.

A quick snapshot of my background:
• Technical Focus: Strong expertise in {skills_highlight} and scalable backend/web architectures
• Impact: Track record of delivering production features and maintainable code
• Notice Period: {notice_period}

Job Requisition Link:
{apply_url}

My Profile Links:
{links_block}

If you feel my profile meets the team's bar, I would really appreciate an internal referral. Happy to share my resume PDF directly or answer any quick questions.

Thank you,
{candidate_name}
{candidate_email}"""

    # --------------------------------------------------------------------------
    # 3. ⚡ 300-Char LinkedIn Connection Request Note (Free connection invite limit)
    # --------------------------------------------------------------------------
    s_label = senior_name.strip() if senior_name.strip() else "there"
    note_candidates = [
        f"Hi {s_label}! Inspired by your journey at {clean_comp}. I'm a developer skilled in {primary_skill} & {secondary_skill} and saw the {title} opening. Would be honored to connect and explore if my profile fits for an internal referral! Thanks, {candidate_name}",
        f"Hi {s_label}, I saw your work at {clean_comp}. I'm a developer skilled in {primary_skill} interested in the {title} role. Would love to connect and share my resume for a potential referral! Best, {candidate_name}",
        f"Hi {s_label}! Fellow engineer skilled in {primary_skill}. Saw the {title} opening at {clean_comp} and would love to connect for guidance or a referral. Thanks!"
    ]
    linkedin_note = note_candidates[0]
    for nc in note_candidates:
        if len(nc) <= 295:
            linkedin_note = nc
            break

    # --------------------------------------------------------------------------
    # 4. 👔 Direct Engineering Manager / Lead InMail Pitch
    # --------------------------------------------------------------------------
    manager_pitch = f"""{manager_greeting}

I am reaching out regarding the {title} opening in your engineering organization at {clean_comp} (Req ID: {short_ref}).

With hands-on proficiency in {skills_highlight}, I am very interested in contributing to your team's engineering goals.

Why I believe I can make an immediate impact:
1. Technical Match: Proficient in {skills_highlight} with end-to-end implementation experience.
2. Fast Execution: Experienced in writing maintainable code and solving complex technical problems.
3. Availability: {notice_period}.

Job Requisition: {title} ({apply_url})
{links_block}

Would you be open to a brief introductory conversation or reviewing my resume for this opening?

Best regards,
{candidate_name}
{candidate_email}"""

    # --------------------------------------------------------------------------
    # 5. ✉️ Cold Referral Email Pitch
    # --------------------------------------------------------------------------
    email_subject = f"Employee Referral Request: {title} (Req ID: {short_ref}) - {candidate_name}"
    email_body = f"""{senior_greeting}

I hope you are doing well.

I am writing to respectfully request an employee referral for the {title} position at {clean_comp} ({location}), under Requisition ID: {short_ref}.

I am specializing in {skills_highlight}. I have been following {clean_comp}'s growth and would love the opportunity to contribute my skills to your team.

Here are the key details for the referral portal:
• Candidate Name: {candidate_name}
• Email: {candidate_email}
• Phone: {candidate_phone or '[Your Phone Number]'}
• Target Role: {title}
• Job Link: {apply_url}
{links_block}

I have attached my updated resume PDF to this email. Please let me know if any additional details are required.

Thank you sincerely for your time, support, and consideration.

Warm regards,
{candidate_name}
{candidate_email}"""

    # --------------------------------------------------------------------------
    # 6. 💬 3-Day Follow-Up Message (Polite reminder)
    # --------------------------------------------------------------------------
    followup_msg = f"""Hi {s_label}, just following up gently on my previous message regarding the {title} opening at {clean_comp}. I know your schedule is busy! Please let me know if you would like me to send my resume PDF directly. Thank you again for your time! - {candidate_name}"""

    search_urls = build_linkedin_search_urls(company, title, active_college)

    return {
        "company": company,
        "clean_company": clean_comp,
        "role_title": title,
        "job_id": job_id,
        "short_ref": short_ref,
        "apply_url": apply_url,
        "senior_name": senior_name.strip(),
        "college_name": active_college,
        "search_urls": search_urls,
        "pitches": {
            "fresher_alumni": {
                "title": "🎓 Student / Fresher → Senior / Alumni Referral",
                "description": "Warm, respectful, highlights your college connection and project hands-on skills.",
                "text": fresher_pitch
            },
            "experienced_peer": {
                "title": "💼 Experienced Professional → Tech Lead / Peer Referral",
                "description": "Peer-to-peer technical tone highlighting stack expertise, impact, and notice period.",
                "text": professional_pitch
            },
            "linkedin_connection_note": {
                "title": "⚡ LinkedIn Free Connection Invite (<300 Chars)",
                "description": "Strictly under 300 characters to send free connection request notes on LinkedIn.",
                "text": linkedin_note,
                "char_count": len(linkedin_note),
                "char_limit": 300
            },
            "manager_inmail": {
                "title": "👔 Engineering Manager / Lead InMail",
                "description": "Executive summary with 3 key pillars of impact and availability.",
                "text": manager_pitch
            },
            "cold_email": {
                "title": "✉️ Cold Referral Email",
                "description": "Complete ready-to-dispatch email with high-open-rate subject line.",
                "subject": email_subject,
                "body": email_body,
                "text": f"Subject: {email_subject}\n\n{email_body}"
            },
            "followup": {
                "title": "💬 3-Day Polite Follow-Up Note",
                "description": "Gentle reminder to send if the senior hasn't responded after 3 days.",
                "text": followup_msg
            }
        }
    }
