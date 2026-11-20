import html
import re
from urllib.parse import quote
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

def build_job_card(job: dict) -> str:
    """Builds a single HTML job card for the digest."""
    title = html.escape(job.get("title") or "Software Engineer")
    company = html.escape(job.get("company") or "Company")
    location = html.escape(job.get("location") or "Location Not Specified")
    source = html.escape(str(job.get("site") or "Web").capitalize())
    apply_url = html.escape(job.get("job_url") or "#")
    date_posted = html.escape(str(job.get("date_posted") or "Recently"))
    salary = html.escape(str(job.get("salary") or ""))
    snippet = html.escape(job.get("snippet") or "")
    is_remote = bool(job.get("is_remote"))
    match_score = job.get("match", {}).get("score") if isinstance(job.get("match"), dict) else None

    # Experience Badge
    exp_badge = job.get("exp_badge")
    if not exp_badge:
        try:
            from src.filter import get_job_experience_badge
            exp_badge = get_job_experience_badge(job)
        except Exception:
            exp_badge = {"label": "🎯 1-2 Yrs Exp"}
    exp_label = exp_badge.get("label", "🎯 1-2 Yrs Exp")
    exp_html = f"""
        <span style="display:inline-block; background-color:#F0FDF4; color:#166534; font-size:11px; font-weight:700; padding:2px 8px; border-radius:10px; margin-right:6px; border:1px solid #BBF7D0;">
            {html.escape(exp_label)}
        </span>
    """

    # Source platform tag colors
    badge_colors = {
        "Linkedin": "#0A66C2",
        "Indeed": "#003A9B",
        "Glassdoor": "#0CAA41",
        "Google": "#EA4335",
        "Naukri": "#1F497D",
        "Internshala": "#008BDC",
        "Web": "#64748B"
    }
    badge_color = badge_colors.get(source, "#4F46E5")

    match_badge = ""
    if match_score:
        score_color = "#059669" if match_score >= 80 else ("#2563EB" if match_score >= 65 else "#D97706")
        match_badge = f"""
            <span style="display:inline-block; background-color:#EFF6FF; color:{score_color}; font-size:11px; font-weight:700; padding:3px 8px; border-radius:12px; margin-right:6px; border:1px solid #BFDBFE;">
                ⚡ {match_score}% Fit
            </span>
        """

    remote_badge = """
        <span style="display:inline-block; background-color:#ECFDF5; color:#065F46; font-size:11px; font-weight:600; padding:3px 8px; border-radius:12px; margin-right:6px;">
            🌐 Remote
        </span>
    """ if is_remote else ""

    salary_badge = f"""
        <span style="display:inline-block; background-color:#FEF3C7; color:#92400E; font-size:11px; font-weight:600; padding:3px 8px; border-radius:12px; margin-right:6px;">
            💰 {salary}
        </span>
    """ if salary else ""

    snippet_html = f"""
        <p style="margin: 8px 0 12px 0; font-size: 13px; line-height: 1.5; color: #475569;">
            {snippet}
        </p>
    """ if snippet else ""

    # LinkedIn Referral URL
    raw_company = str(job.get("company") or "").strip()
    clean_comp = re.sub(r'(?i)\b(pvt|ltd|private|limited|technologies|solutions|inc)\b', '', raw_company).strip() or raw_company
    kw_seniors = f'"{clean_comp}" ("Senior Software Engineer" OR "Tech Lead" OR "Lead Engineer") India'
    linkedin_referral_url = f"https://www.linkedin.com/search/results/people/?keywords={quote(kw_seniors)}&origin=GLOBAL_SEARCH_HEADER"

    return f"""
    <div style="background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 18px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr>
                <td style="vertical-align: top;">
                    <div style="margin-bottom: 4px;">
                        <span style="display:inline-block; background-color:{badge_color}; color:#ffffff; font-size:11px; font-weight:700; padding:2px 8px; border-radius:10px; margin-right:6px;">
                            {source}
                        </span>
                        {exp_html}
                        {match_badge}
                        {remote_badge}
                        {salary_badge}
                    </div>
                    <h2 style="margin: 4px 0 2px 0; font-size: 17px; font-weight: 700; color: #0f172a; line-height: 1.3;">
                        {title}
                    </h2>
                    <div style="font-size: 13px; color: #64748b; margin-bottom: 6px;">
                        <strong style="color: #1e293b;">{company}</strong> &bull; {location} &bull; <span style="color:#94a3b8;">📅 {date_posted}</span>
                    </div>
                </td>
                <td style="vertical-align: top; text-align: right; width: 140px; padding-left: 10px;">
                    <a href="{apply_url}" target="_blank" style="display: block; text-align: center; background: linear-gradient(135deg, #4F46E5, #6366F1); color: #ffffff; text-decoration: none; font-size: 13px; font-weight: 600; padding: 8px 14px; border-radius: 8px; box-shadow: 0 2px 4px rgba(79, 70, 229, 0.25); white-space: nowrap; margin-bottom: 6px;">
                        Apply Now &rarr;
                    </a>
                    <a href="{linkedin_referral_url}" target="_blank" style="display: block; text-align: center; background: #0A66C2; color: #ffffff; text-decoration: none; font-size: 11px; font-weight: 600; padding: 6px 10px; border-radius: 6px; white-space: nowrap;">
                        🤝 Ask Referral &rarr;
                    </a>
                </td>
            </tr>
        </table>
        {snippet_html}
    </div>
    """

def build_email_digest(
    jobs: List[Dict], 
    user_name: str = "Candidate",
    target_role: str = "Software Engineer",
    experience_level: str = "fresher",
    email_exp_filter: str = "1_year",
    email_roles: Optional[List[str]] = None,
    email_languages: Optional[List[str]] = None,
    skills: Optional[List[str]] = None
) -> tuple[str, str]:
    """
    Builds both HTML and Plain-Text representations of the personalized job digest.
    Returns (html_content, plain_text_content).
    """
    current_date = datetime.now().strftime("%A, %B %d, %Y")
    job_count = len(jobs)
    skills_preview = ", ".join(skills[:5]) if skills else "General Tech Stack"

    roles_display = ", ".join(email_roles[:3]) if email_roles else target_role
    langs_display = ", ".join(email_languages[:5]) if email_languages else (", ".join(skills[:4]) if skills else "All Tech")

    exp_filter_names = {
        "1_year": "🎯 1 Year Exp (0-2 Yrs)",
        "fresher": "🎓 Freshers Only (0-1 Yrs)",
        "junior": "💼 Junior Roles (1-2 Yrs)",
        "mid": "🚀 Mid-Level Roles (2-5 Yrs)",
        "senior": "⭐ Senior & Lead Roles (5+ Yrs)",
        "all": "🌐 All Experience Levels"
    }
    filter_label = exp_filter_names.get(email_exp_filter, f"🎯 {email_exp_filter} Experience")

    if job_count == 0:
        cards_html = f"""
        <div style="background-color: #ffffff; border-radius: 12px; padding: 32px; text-align: center; border: 1px dashed #cbd5e1;">
            <p style="font-size: 16px; color: #64748b; margin: 0;">
                No brand-new unemailed jobs matched your exact criteria ({filter_label} &bull; {html.escape(roles_display)} &bull; {html.escape(langs_display)}) today, {html.escape(user_name)}. We'll keep scanning automatically!
            </p>
        </div>
        """
        plain_text = f"No new matching jobs found today ({current_date}) for {user_name} with filter {filter_label} (Roles: {roles_display}, Tech: {langs_display})."
    else:
        cards_html = "\n".join(build_job_card(j) for j in jobs)
        
        # Build plain text fallback
        plain_lines = [
            f"DAILY JOB DIGEST FOR {user_name.upper()} - {current_date}",
            f"Target Roles: {roles_display}",
            f"Tech Stack / Languages: {langs_display}",
            f"Experience Filter: {filter_label}",
            f"Found {job_count} personalized matching positions for you.\n",
            "=" * 60
        ]
        for idx, j in enumerate(jobs, 1):
            plain_lines.append(f"{idx}. {j.get('title')} at {j.get('company')}")
            plain_lines.append(f"   Location: {j.get('location')} | Source: {j.get('site')}")
            if j.get('salary'):
                plain_lines.append(f"   Salary: {j.get('salary')}")
            plain_lines.append(f"   Apply Link: {j.get('job_url')}")
            plain_lines.append("-" * 40)
        plain_text = "\n".join(plain_lines)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JobRadar AI Digest - {html.escape(user_name)}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f8fafc; padding: 24px 12px;">
        <tr>
            <td align="center">
                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width: 680px; text-align: left;">
                    <!-- HEADER -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%); border-radius: 16px; padding: 28px 24px; color: #ffffff; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                            <div style="font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #a5b4fc; margin-bottom: 6px;">
                                JobRadar AI &bull; Personalized Digest for {html.escape(user_name)}
                            </div>
                            <h1 style="margin: 0 0 8px 0; font-size: 24px; font-weight: 800; color: #ffffff;">
                                🎯 {job_count} Curated Positions Found
                            </h1>
                            <div style="font-size: 14px; color: #e0e7ff; line-height: 1.4;">
                                Tailored for <strong>{html.escape(roles_display)}</strong> &bull; Stack: <strong>{html.escape(langs_display)}</strong>
                            </div>
                            <div style="margin-top: 12px;">
                                <span style="display:inline-block; background:rgba(255,255,255,0.18); border:1px solid rgba(255,255,255,0.35); padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700; color:#ffffff; margin-right:6px; margin-bottom:4px;">
                                    {html.escape(filter_label)}
                                </span>
                                <span style="display:inline-block; background:rgba(255,255,255,0.18); border:1px solid rgba(255,255,255,0.35); padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700; color:#ffffff; margin-right:6px; margin-bottom:4px;">
                                    💼 {html.escape(roles_display)}
                                </span>
                                <span style="display:inline-block; background:rgba(255,255,255,0.18); border:1px solid rgba(255,255,255,0.35); padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700; color:#ffffff; margin-bottom:4px;">
                                    💻 {html.escape(langs_display)}
                                </span>
                            </div>
                        </td>
                    </tr>

                    <!-- SPACER -->
                    <tr><td height="20"></td></tr>

                    <!-- JOB LIST -->
                    <tr>
                        <td>
                            {cards_html}
                        </td>
                    </tr>

                    <!-- SPACER -->
                    <tr><td height="12"></td></tr>

                    <!-- FOOTER -->
                    <tr>
                        <td style="text-align: center; padding: 16px; font-size: 12px; color: #94a3b8;">
                            <p style="margin: 0 0 6px 0;">
                                Powered by <strong>JobRadar AI Platform</strong> &bull; Aggregated from LinkedIn, Indeed, Internshala, Naukri & Google Jobs
                            </p>
                            <p style="margin: 0;">
                                Jobs are deduplicated and tracked per candidate in your database so you never get repeats.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
    return html_content, plain_text

def save_html_preview(html_content: str, output_path: str = "latest_digest.html") -> Path:
    """Saves HTML digest to a local file for fast browser viewing."""
    path = Path(__file__).resolve().parent.parent / output_path
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_content)
    return path
