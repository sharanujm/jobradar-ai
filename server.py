import os
import sys
import json
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Configure Windows console for UTF-8 encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi import FastAPI, UploadFile, File, Form, Query, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.config_loader import load_config
from src.database import (
    get_jobs_list, get_stats, toggle_user_job_status, 
    get_user_by_email, upsert_user, get_unemailed_jobs_for_user,
    mark_jobs_delivered_for_user, update_user_schedule, get_connection,
    get_tracker_items_for_user, update_tracker_stage, delete_tracker_item,
    verify_user_credentials, update_user_profile, get_system_setting, set_system_setting,
    normalize_time_str, mark_user_digest_sent, reset_user_digest_tracking
)
from src.resume_matcher import (
    extract_text_from_pdf, extract_text_from_docx, extract_skills_from_text, calculate_job_match,
    analyze_resume_ats, enhance_resume_bullet
)
from src.email_builder import build_email_digest, save_html_preview
from src.email_sender import send_digest_email
from src.scraper import scrape_all_sources
from src.pitch_generator import generate_outreach_pitch
from src.study_vault import (
    get_resources_for_user, add_resource, 
    toggle_resource_completion, delete_resource, 
    update_resource_notes, get_resource_by_id, generate_ai_study_assist,
    RESOURCES_DIR, init_study_vault_db
)
from src.filter import is_india_location
from src.salary_studio import estimate_compensation, generate_counter_offer_scripts
from src.career_assistant import get_career_assistant_response
from src.telegram_sender import test_telegram_connection, send_telegram_job_alert
from src.referral_hub import generate_referral_pitch_suite, build_linkedin_search_urls
from src.interview_simulator import generate_mock_interview, evaluate_interview_answer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("JobRadarServer")

app = FastAPI(title="JobRadar AI - Automated Job Search Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# In-memory background task status & automated scheduling pipeline
SCAN_STATE = {
    "is_running": False,
    "last_run": None,
    "last_result": "Pipeline ready. Automated pre-digest scraper active across LinkedIn, Indeed, Internshala, Naukri & Google Jobs.",
    "auto_scrape_enabled": True,
    "lead_minutes": 30,
    "next_scheduled_scrape": "19:30"
}

SCHEDULED_LAST_SENT = set()
SCHEDULED_SCRAPE_LAST_RUN = set()

# Indian Standard Time (IST, UTC+5:30) for scheduled daily digests
from datetime import timezone, timedelta
IST = timezone(timedelta(hours=5, minutes=30))

def get_time_minus_minutes(time_str: str, minutes: int = 30) -> str:
    """Calculates HH:MM time minus specified minutes (for pre-digest auto-scrape)."""
    try:
        parts = time_str.strip().split(":")
        h, m = int(parts[0]), int(parts[1])
        total_m = (h * 60 + m - minutes) % (24 * 60)
        return f"{total_m // 60:02d}:{total_m % 60:02d}"
    except Exception:
        return "19:30"

def send_personalized_digest_to_user(user: Any, force_send: bool = False) -> tuple[bool, str, int]:
    """
    Builds and sends a personalized job digest email to a specific registered user
    based on their target role, experience level, and resume skills.
    Returns (success, message, job_count).
    """
    if isinstance(user, str):
        user = get_user_by_email(user)
    if not user:
        return False, "User not found", 0

    recipient_email = user.get("email", "").strip().lower()
    if not recipient_email:
        return False, "User has no email configured", 0

    user_name = user.get("name") or recipient_email.split("@")[0].capitalize()
    target_role = user.get("target_role", "Software Engineer")
    experience_level = user.get("experience_level", "fresher")
    email_exp_filter = user.get("email_experience_filter") or "1_year"
    
    email_roles = user.get("email_roles") or []
    if isinstance(email_roles, str):
        try:
            email_roles = json.loads(email_roles)
        except Exception:
            email_roles = [r.strip() for r in email_roles.split(",") if r.strip()]
    if not email_roles:
        if target_role and target_role.strip():
            email_roles = [target_role.strip(), "Python Developer", "Backend Developer"] if "software" in target_role.lower() else [target_role.strip()]
        else:
            email_roles = ["Software Engineer", "Python Developer", "Backend Developer"]
            
    email_languages = user.get("email_languages") or []
    if isinstance(email_languages, str):
        try:
            email_languages = json.loads(email_languages)
        except Exception:
            email_languages = [l.strip() for l in email_languages.split(",") if l.strip()]

    years_exp = user.get("years_experience", "1")
    user_skills = user.get("skills", [])
    if isinstance(user_skills, str):
        try:
            user_skills = json.loads(user_skills)
        except Exception:
            user_skills = []

    if not email_languages:
        tech_kw = {"python", "sql", "javascript", "typescript", "java", "c++", "c#", "golang", "go", "react", "node", "nodejs", "vue", "angular", "django", "flask", "fastapi"}
        matched_langs = [s for s in user_skills if str(s).lower() in tech_kw]
        email_languages = matched_langs if matched_langs else (user_skills[:4] if user_skills else ["Python", "SQL"])

    email_locations = user.get("email_locations", [])

    cfg = load_config()
    target_job_count = cfg.get("digest", {}).get("max_jobs_in_email", 100)

    logger.info(f"📧 [PERSONALIZED DIGEST] Preparing up to {target_job_count} India jobs for {user_name} <{recipient_email}> (Exp: {email_exp_filter}, Roles: {email_roles}, Stack: {email_languages}, Locs: {email_locations or 'All'})...")

    from src.filter import matches_email_filter
    # Fetch fresh unemailed jobs specifically matching user's email experience, roles, languages, and locations
    pending = get_unemailed_jobs_for_user(
        recipient_email, 
        limit=target_job_count * 2,
        experience_filter=email_exp_filter,
        target_roles=email_roles,
        target_languages=email_languages,
        target_locations=email_locations,
        years_exp=years_exp
    )
    # Strictly ensure only India locations and matching criteria
    pending = [
        j for j in pending 
        if is_india_location(j.get("location"), j.get("site")) and matches_email_filter(
            j, 
            exp_filter=email_exp_filter, 
            target_roles=email_roles, 
            target_languages=email_languages, 
            target_locations=email_locations,
            years_exp=years_exp
        )
    ]

    # If user has fewer unemailed jobs than target_job_count, supplement with matching India jobs from DB
    if len(pending) < target_job_count:
        logger.info(f"  Fewer than {target_job_count} unemailed jobs for {recipient_email} ({len(pending)} found). Supplementing with matching roles...")
        loc_arg = email_locations[0] if (email_locations and len(email_locations) == 1) else "all"
        supplementary, _ = get_jobs_list(
            limit=target_job_count * 15,
            experience=email_exp_filter if email_exp_filter != "all" else "",
            location=loc_arg,
            user_email=recipient_email
        )
        existing_ids = {j["id"] for j in pending}
        for s in supplementary:
            if s["id"] not in existing_ids and is_india_location(s.get("location"), s.get("site")) and matches_email_filter(
                s, 
                exp_filter=email_exp_filter, 
                target_roles=email_roles, 
                target_languages=email_languages, 
                target_locations=email_locations,
                years_exp=years_exp
            ):
                pending.append(s)
            if len(pending) >= target_job_count:
                break

    # Robust fallback: relax filters to ensure candidates always receive matching software roles
    if len(pending) < target_job_count:
        logger.info(f"  Relaxing facets to ensure full {target_job_count}-job digest delivery for {recipient_email} ({len(pending)} found so far)...")
        existing_ids = {j["id"] for j in pending}
        fallback_jobs, _ = get_jobs_list(
            limit=target_job_count * 5,
            experience=email_exp_filter if email_exp_filter != "all" else "",
            location="all",
            user_email=recipient_email
        )
        for f_job in fallback_jobs:
            if f_job["id"] not in existing_ids and is_india_location(f_job.get("location"), f_job.get("site")):
                pending.append(f_job)
                if len(pending) >= target_job_count:
                    break

    if not pending:
        # Ultimate fallback: top India software engineering jobs from database
        fallback_jobs, _ = get_jobs_list(limit=target_job_count, location="all")
        pending = [j for j in fallback_jobs if is_india_location(j.get("location"), j.get("site"))]

    if not pending:
        logger.warning(f"No India jobs found in database for {recipient_email}.")
        return False, "No jobs found in database", 0

    # Score and rank jobs according to user's resume and skills
    for j in pending:
        match_info = calculate_job_match(
            job=j,
            user_skills=user_skills,
            user_experience=email_exp_filter if email_exp_filter != "all" else experience_level,
            target_role=target_role
        )
        j["match"] = match_info

    pending.sort(key=lambda x: x["match"]["score"], reverse=True)
    selected_jobs = pending[:target_job_count]

    html_content, plain_text = build_email_digest(
        jobs=selected_jobs,
        user_name=user_name,
        target_role=target_role,
        experience_level=experience_level,
        email_exp_filter=email_exp_filter,
        email_roles=email_roles,
        email_languages=email_languages,
        skills=user_skills
    )
    save_html_preview(html_content, "latest_digest.html")

    today_str = datetime.now().strftime("%b %d, %Y")
    subject = f"🚀 JobRadar AI Digest: {len(selected_jobs)} Roles Found for {user_name} ({today_str})"

    cfg = load_config()
    result = send_digest_email(
        subject=subject,
        html_content=html_content,
        plain_text_content=plain_text,
        config=cfg,
        recipient_override=recipient_email
    )

    if isinstance(result, tuple):
        sent, detail_msg = result
    else:
        sent = bool(result)
        detail_msg = ""

    if sent:
        delivered_ids = [j["id"] for j in selected_jobs]
        mark_jobs_delivered_for_user(recipient_email, delivered_ids)
        logger.info(f"🎉 [DIGEST DELIVERED] Successfully delivered {len(selected_jobs)} jobs to {recipient_email}! ({detail_msg})")
        return True, f"Digest with {len(selected_jobs)} curated jobs sent to {recipient_email}! {detail_msg}", len(selected_jobs)
    else:
        logger.error(f"❌ [DIGEST FAILED] Could not deliver to {recipient_email}: {detail_msg}")
        return False, detail_msg or "Failed to send email. Check email credentials in settings.", len(selected_jobs)

def check_and_send_scheduled_digests() -> List[str]:
    """
    Evaluates all candidates with daily_email=1 against the current IST time.
    Uses catch-up logic:
    If today's digest has not yet been sent (u['last_digest_date'] != today_date)
    and current_time >= user_time, dispatches today's 100-job digest immediately.
    Guarantees email delivery even if Render was asleep or woke up after the exact minute.
    Returns list of recipients triggered.
    """
    triggered = []
    try:
        now_ist = datetime.now(IST)
        current_time = now_ist.strftime("%H:%M")
        today_date = now_ist.strftime("%Y-%m-%d")

        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE daily_email = 1")
            users = cursor.fetchall()
        finally:
            conn.close()

        for row in users:
            u = dict(row)
            user_email = (u.get("email") or "").strip().lower()
            if not user_email or "@" not in user_email:
                continue

            user_time = normalize_time_str(u.get("email_time") or "20:00")
            last_date = (u.get("last_digest_date") or "").strip()

            mem_key = f"{user_email}_{today_date}"
            # Catch-up check:
            # 1. Not sent today yet in database
            # 2. Scheduled time has arrived or passed (current_time >= user_time)
            # 3. Not in memory cache for today
            if last_date != today_date and current_time >= user_time and mem_key not in SCHEDULED_LAST_SENT:
                logger.info(f"⚡ [SCHEDULE HIT/CATCH-UP] Due 100-job digest for {user_email} (scheduled {user_time}, current {current_time}, last sent '{last_date}') -> Dispatching now...")
                SCHEDULED_LAST_SENT.add(mem_key)
                mark_user_digest_sent(user_email, today_date, current_time)
                try:
                    u["skills"] = json.loads(u.get("skills") or "[]")
                except Exception:
                    u["skills"] = []

                # Dispatch asynchronously whether inside or outside an active asyncio loop
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(asyncio.to_thread(send_personalized_digest_to_user, u))
                except RuntimeError:
                    import threading
                    t = threading.Thread(target=send_personalized_digest_to_user, args=(u,), daemon=True)
                    t.start()

                triggered.append(user_email)

    except Exception as e:
        logger.error(f"Error checking scheduled digests: {e}", exc_info=True)

    return triggered

async def background_scheduler_worker():
    """
    Multi-User Automated Job Pipeline:
    1. Pre-Digest Auto-Scrape: Automatically triggers multi-source job scraping
       (LinkedIn, Indeed, Internshala, Naukri, Google Jobs) strictly for India
       30 minutes (configurable) before each candidate's scheduled email dispatch.
    2. Daily 100-Job Digest Dispatch: Builds, scores, and delivers 100 fresh India roles
       directly to candidates' inboxes at their selected time with catch-up logic.
    """
    logger.info("🕒 Automated Pre-Digest Scraper & Daily Email Engine active (monitoring schedules every 20s in IST)...")
    while True:
        try:
            now_ist = datetime.now(IST)
            current_time = now_ist.strftime("%H:%M")
            today_date = now_ist.strftime("%Y-%m-%d")

            conn = get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE daily_email = 1")
                users = cursor.fetchall()
            finally:
                conn.close()

            lead_min = int(SCAN_STATE.get("lead_minutes", 30))
            active_scrape_times = []

            for row in users:
                u = dict(row)
                user_email = (u.get("email") or "").strip().lower()
                user_time = normalize_time_str(u.get("email_time") or "20:00")

                # Calculate pre-digest auto-scrape time (e.g. 19:30 for 20:00 digest)
                scrape_time = get_time_minus_minutes(user_time, lead_min)
                active_scrape_times.append(scrape_time)

                # Pre-Digest Automated Scraping (30m before daily email)
                if SCAN_STATE.get("auto_scrape_enabled", True) and current_time == scrape_time:
                    scrape_key = f"scrape_{today_date}_{scrape_time}"
                    if scrape_key not in SCHEDULED_SCRAPE_LAST_RUN:
                        if not SCAN_STATE["is_running"]:
                            SCHEDULED_SCRAPE_LAST_RUN.add(scrape_key)
                            logger.info(f"⚡ [AUTO-SCRAPE TRIGGERED] Pre-digest scraper launched at {current_time} ({lead_min}m before {user_time} email for {user_email})...")
                            asyncio.create_task(asyncio.to_thread(run_scrape_background))
                        else:
                            logger.info(f"ℹ️ Scraper already active in background at {current_time}.")

            if active_scrape_times:
                SCAN_STATE["next_scheduled_scrape"] = active_scrape_times[0]

            # Daily 100-Job Digest Catch-Up Delivery
            check_and_send_scheduled_digests()

        except Exception as e:
            logger.error(f"Error in background scheduler worker: {e}", exc_info=True)

        await asyncio.sleep(20)

@app.on_event("startup")
async def on_startup():
    try:
        from src.database import init_db, backfill_jobs_experience
        init_db()
        asyncio.create_task(asyncio.to_thread(backfill_jobs_experience, force=False))
    except Exception as e:
        logger.error(f"Startup experience backfill error: {e}")
    asyncio.create_task(background_scheduler_worker())

# Default user setup for onboarding
DEFAULT_EMAIL = "candidate@jobradar.ai"
existing_default = get_user_by_email(DEFAULT_EMAIL)
if not existing_default:
    upsert_user({
        "email": DEFAULT_EMAIL,
        "name": "Candidate",
        "password": "password123",
        "target_role": "Software Engineer",
        "experience_level": "fresher",
        "skills": ["Python", "JavaScript", "React", "SQL", "Git", "REST API", "HTML", "CSS"],
        "daily_email": True,
        "email_time": "20:00"
    })

# Pydantic models
class LoginRequest(BaseModel):
    email: str
    password: Optional[str] = ""

class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str

class SignupRequest(BaseModel):
    email: str
    name: str
    password: Optional[str] = ""
    target_role: Optional[str] = "Software Engineer"
    experience_level: Optional[str] = "fresher"
    skills: Optional[List[str]] = []
    email_time: Optional[str] = "20:00"
    daily_email: Optional[bool] = True

class ProfileUpdateRequest(BaseModel):
    email: str
    name: Optional[str] = None
    password: Optional[str] = None
    target_role: Optional[str] = None
    experience_level: Optional[str] = None
    skills: Optional[List[str]] = None
    email_time: Optional[str] = None
    daily_email: Optional[bool] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    telegram_alerts: Optional[bool] = None
    phone: Optional[str] = None
    github_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    years_experience: Optional[str] = None
    email_experience_filter: Optional[str] = None
    email_roles: Optional[Any] = None
    email_languages: Optional[Any] = None
    email_locations: Optional[Any] = None
    notice_period: Optional[str] = None
    expected_ctc: Optional[str] = None
    college_name: Optional[str] = None
    current_city: Optional[str] = None
    work_authorization: Optional[str] = None
    visa_sponsorship: Optional[str] = None
    summary_bio: Optional[str] = None

class AutofillCustomRequest(BaseModel):
    user_email: Optional[str] = DEFAULT_EMAIL
    company: str
    role: str
    job_snippet: Optional[str] = ""
    skills_context: Optional[List[str]] = None

class ReferralHubRequest(BaseModel):
    job_id: str
    user_email: Optional[str] = DEFAULT_EMAIL
    senior_name: Optional[str] = ""
    college_name: Optional[str] = ""
    senior_role: Optional[str] = ""
    company_keyword: Optional[str] = ""
    job_ref: Optional[str] = ""

class ReferralTrackRequest(BaseModel):
    user_email: str
    job_id: str
    senior_name: Optional[str] = ""
    senior_profile_url: Optional[str] = ""
    senior_role: Optional[str] = ""
    pitch_type: Optional[str] = ""
    notes: Optional[str] = ""

class ChatRequest(BaseModel):
    message: str
    email: Optional[str] = None

class TelegramTestRequest(BaseModel):
    bot_token: str
    chat_id: str

class TelegramJobAlertRequest(BaseModel):
    email: str
    job_id: str

class StatusRequest(BaseModel):
    user_email: str
    job_id: str
    status: str
    notes: Optional[str] = None
    applied_date: Optional[str] = None

class SendDigestRequest(BaseModel):
    user_email: str
    experience_filter: Optional[str] = None
    roles: Optional[Any] = None
    languages: Optional[Any] = None

class TrackerUpdateRequest(BaseModel):
    user_email: str
    job_id: str
    status: str
    notes: Optional[str] = None
    applied_date: Optional[str] = None

class TrackerDeleteRequest(BaseModel):
    user_email: str
    job_id: str

# Serve UI with explicit anti-cache headers
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        response = FileResponse(index_file)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    return "<h1>JobRadar AI UI loading...</h1>"


# ------------------------------------------------------------------------------
# Authentication & User Profile Endpoints
# ------------------------------------------------------------------------------
@app.post("/api/auth/login")
async def login(req: LoginRequest):
    email = req.email.strip().lower()
    password = (req.password or "").strip()

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    if not password:
        raise HTTPException(status_code=400, detail="Please enter your password.")

    existing = get_user_by_email(email)
    if not existing:
        raise HTTPException(
            status_code=404, 
            detail="No account found with this email. Please check your spelling or click 'Create Free Account' to register."
        )

    user = verify_user_credentials(email, password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect password. Please verify and try again.")

    return {"status": "ok", "user": user}

@app.post("/api/auth/signup")
async def signup(req: SignupRequest):
    email = req.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    password = (req.password or "").strip()
    if not password:
        raise HTTPException(status_code=400, detail="Please choose a password.")
    if len(password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters long.")

    name = req.name.strip()
    if not name:
        name = email.split("@")[0].capitalize()

    existing = get_user_by_email(email)
    if existing:
        raise HTTPException(
            status_code=409, 
            detail="An account with this email already exists. Please Sign In instead."
        )

    target_role = (req.target_role or "Software Engineer").strip()
    user = upsert_user({
        "email": email,
        "name": name,
        "password": password,
        "target_role": target_role,
        "experience_level": req.experience_level or "fresher",
        "skills": req.skills or ["Python", "JavaScript", "SQL", "Git", "REST API"],
        "email_time": req.email_time or "20:00",
        "daily_email": req.daily_email if req.daily_email is not None else True,
        "email_experience_filter": "1_year" if req.experience_level == "fresher" else req.experience_level or "1_year",
        "email_roles": [target_role, "Python Developer", "Backend Developer"] if "software" in target_role.lower() else [target_role],
        "email_languages": ["Python", "JavaScript", "SQL"]
    })
    return {"status": "ok", "user": user}

@app.get("/api/user/profile")
async def get_profile(email: Optional[str] = None):
    if not email or not email.strip():
        return {"user": None}
    user = get_user_by_email(email.strip().lower())
    return {"user": user}

@app.post("/api/auth/reset-password")
async def reset_password_endpoint(req: ResetPasswordRequest):
    email = req.email.strip().lower()
    new_password = (req.new_password or "").strip()

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    if not new_password or len(new_password) < 4:
        raise HTTPException(status_code=400, detail="New password must be at least 4 characters long.")

    user = get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="No account found with this email. Please verify or create an account.")

    updated_user = update_user_profile({"email": email, "password": new_password})
    return {
        "status": "ok", 
        "message": "Password updated successfully!", 
        "user": updated_user
    }

@app.post("/api/auth/profile")
async def update_profile_endpoint(req: ProfileUpdateRequest):
    email = req.email.strip().lower()
    user_data = {"email": email}
    if req.name is not None:
        user_data["name"] = req.name
    if req.password is not None and req.password.strip():
        user_data["password"] = req.password.strip()
    if req.target_role is not None:
        user_data["target_role"] = req.target_role
    if req.experience_level is not None:
        user_data["experience_level"] = req.experience_level
    if req.skills is not None:
        user_data["skills"] = req.skills
    if req.email_time is not None:
        clean_sched_time = normalize_time_str(req.email_time)
        user_data["email_time"] = clean_sched_time
        set_system_setting("global_email_schedule_time", clean_sched_time)
    if req.daily_email is not None:
        user_data["daily_email"] = req.daily_email
    if req.telegram_bot_token is not None:
        user_data["telegram_bot_token"] = req.telegram_bot_token
    if req.telegram_chat_id is not None:
        user_data["telegram_chat_id"] = req.telegram_chat_id
    if req.telegram_alerts is not None:
        user_data["telegram_alerts"] = req.telegram_alerts
    if req.phone is not None:
        user_data["phone"] = req.phone
    if req.github_url is not None:
        user_data["github_url"] = req.github_url
    if req.linkedin_url is not None:
        user_data["linkedin_url"] = req.linkedin_url
    if req.portfolio_url is not None:
        user_data["portfolio_url"] = req.portfolio_url
    if req.years_experience is not None:
        user_data["years_experience"] = req.years_experience
    if req.email_experience_filter is not None:
        user_data["email_experience_filter"] = req.email_experience_filter
    if req.email_roles is not None:
        user_data["email_roles"] = req.email_roles
    if req.email_languages is not None:
        user_data["email_languages"] = req.email_languages
    if req.email_locations is not None:
        user_data["email_locations"] = req.email_locations
    if req.notice_period is not None:
        user_data["notice_period"] = req.notice_period
    if req.expected_ctc is not None:
        user_data["expected_ctc"] = req.expected_ctc
    if req.college_name is not None:
        user_data["college_name"] = req.college_name

    updated_user = update_user_profile(user_data)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"status": "ok", "user": updated_user}

# ------------------------------------------------------------------------------
# Resume Upload & Parsing
# ------------------------------------------------------------------------------
@app.post("/api/user/resume/upload")
async def upload_resume(
    email: str = Form(DEFAULT_EMAIL),
    file: UploadFile = File(...)
):
    try:
        content = await file.read()
        filename = file.filename or "resume.pdf"
        
        extracted_text = ""
        if filename.lower().endswith(".pdf"):
            extracted_text = extract_text_from_pdf(content)
        elif filename.lower().endswith(".docx"):
            extracted_text = extract_text_from_docx(content)
        else:
            extracted_text = content.decode("utf-8", errors="ignore")

        found_skills = extract_skills_from_text(extracted_text)

        # Merge with existing skills in user profile
        user = get_user_by_email(email) or {}
        existing_skills = set(user.get("skills", []))
        merged_skills = sorted(list(existing_skills.union(set(found_skills)))) if found_skills else sorted(list(existing_skills))

        # Perform fresh ATS analysis
        analysis = analyze_resume_ats(
            resume_text=extracted_text, 
            user_exp=user.get("experience_level", "fresher"),
            target_role=user.get("target_role", "Software Engineer")
        )

        # Auto-align email languages to candidate's parsed tech stack
        tech_kw = {"python", "sql", "javascript", "typescript", "java", "c++", "c#", "golang", "go", "react", "node", "nodejs", "vue", "angular", "django", "flask", "fastapi"}
        matched_langs = [s for s in merged_skills if str(s).lower() in tech_kw]
        updated_langs = matched_langs[:6] if matched_langs else user.get("email_languages", ["Python", "SQL"])

        updated_user = upsert_user({
            "email": email,
            "name": user.get("name", email.split("@")[0]),
            "target_role": user.get("target_role", "Software Engineer"),
            "experience_level": user.get("experience_level", "fresher"),
            "skills": merged_skills,
            "resume_text": extracted_text[:12000],
            "resume_filename": filename,
            "email_languages": updated_langs
        })

        return {
            "status": "ok",
            "filename": filename,
            "extracted_skills": found_skills,
            "total_skills": len(merged_skills),
            "analysis": analysis,
            "user": updated_user
        }
    except Exception as e:
        logger.error(f"Error parsing resume: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/user/resume/paste")
async def paste_resume(
    email: str = Form(DEFAULT_EMAIL),
    text: str = Form(...),
    experience_level: str = Form("fresher")
):
    found_skills = extract_skills_from_text(text)
    user = get_user_by_email(email) or {}
    existing_skills = set(user.get("skills", []))
    merged_skills = sorted(list(existing_skills.union(set(found_skills))))

    updated_user = upsert_user({
        "email": email,
        "name": user.get("name", email.split("@")[0]),
        "target_role": user.get("target_role", "Software Engineer"),
        "experience_level": experience_level,
        "skills": merged_skills,
        "resume_text": text[:8000],
        "resume_filename": "Pasted Skills Profile"
    })

    return {"status": "ok", "extracted_skills": found_skills, "user": updated_user}

# ------------------------------------------------------------------------------
# Jobs Feed API with Personalized Resume Scoring
# ------------------------------------------------------------------------------
@app.get("/api/jobs")
async def get_jobs(
    search: str = "",
    site: str = "all",
    experience: str = "all",
    location: str = "all",
    is_remote: Optional[bool] = None,
    status_filter: str = "",
    min_score: int = 0,
    posted_within: str = "",
    skill_tag: str = "",
    email: str = DEFAULT_EMAIL,
    limit: int = 50,
    offset: int = 0
):
    user = get_user_by_email(email) or {}
    user_skills = user.get("skills", [])
    user_exp = experience if experience != "all" else user.get("experience_level", "fresher")
    target_role = user.get("target_role", "Software Engineer")

    jobs, total_count = get_jobs_list(
        search=search,
        site=site,
        experience=experience if experience != "all" else "",
        location=location if location != "all" else "",
        is_remote=is_remote,
        status_filter=status_filter,
        user_email=email,
        posted_within=posted_within,
        skill_tag=skill_tag,
        limit=limit,
        offset=offset
    )

    # Augment with Personalized Match Scoring
    matched_jobs = []
    for j in jobs:
        match_info = calculate_job_match(
            job=j,
            user_skills=user_skills,
            user_experience=user_exp,
            target_role=target_role
        )
        if match_info["score"] >= min_score:
            j["match"] = match_info
            matched_jobs.append(j)

    # Sort primarily by match score if no specific search query
    matched_jobs.sort(key=lambda x: x["match"]["score"], reverse=True)

    return {
        "jobs": matched_jobs,
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "active_user_skills": user_skills,
        "experience_level": user_exp
    }

# ------------------------------------------------------------------------------
# Application Tracking System (Kanban & Pipeline)
# ------------------------------------------------------------------------------
@app.get("/api/tracker")
async def get_tracker_endpoint(email: str = Query(DEFAULT_EMAIL)):
    clean_email = email.strip().lower()
    items = get_tracker_items_for_user(clean_email)
    stats = get_stats(user_email=clean_email)
    return {
        "status": "ok",
        "items": items,
        "stats": stats
    }

@app.post("/api/tracker/update")
async def update_tracker_endpoint(req: TrackerUpdateRequest):
    clean_email = req.user_email.strip().lower()
    res = update_tracker_stage(
        user_email=clean_email,
        job_id=req.job_id,
        status=req.status,
        notes=req.notes,
        applied_date=req.applied_date
    )
    stats = get_stats(user_email=clean_email)
    return {"status": "ok", "result": res, "stats": stats}

@app.post("/api/tracker/delete")
async def delete_tracker_endpoint(req: TrackerDeleteRequest):
    clean_email = req.user_email.strip().lower()
    delete_tracker_item(clean_email, req.job_id)
    stats = get_stats(user_email=clean_email)
    return {"status": "ok", "stats": stats}

# Job Actions: Toggle Save / Applied (from main feed)
@app.post("/api/jobs/toggle-save")
async def toggle_save(req: StatusRequest):
    new_status = toggle_user_job_status(req.user_email, req.job_id, "saved")
    return {"status": "ok", "user_status": new_status}

@app.post("/api/jobs/set-status")
async def set_status(req: StatusRequest):
    new_status = toggle_user_job_status(req.user_email, req.job_id, req.status)
    return {"status": "ok", "user_status": new_status}

# Stats
@app.get("/api/stats")
async def get_dashboard_stats(email: str = DEFAULT_EMAIL):
    stats = get_stats(user_email=email)
    return {"stats": stats}

# ------------------------------------------------------------------------------
# 1-Click AI Cover Letter, Cold Outreach & Interview Prep Generator
# ------------------------------------------------------------------------------
class PitchRequest(BaseModel):
    job_id: str
    user_email: Optional[str] = DEFAULT_EMAIL
    tone: Optional[str] = "professional"

@app.post("/api/ai/generate-pitch")
async def generate_pitch_endpoint(req: PitchRequest):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (req.job_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Job not found")

    job = dict(row)
    user = get_user_by_email(req.user_email) or {}
    pitch = generate_outreach_pitch(job, user, req.tone or "professional")

    return {
        "status": "ok",
        "pitch": pitch,
        "job": {
            "id": job["id"],
            "title": job["title"],
            "company": job["company"],
            "location": job["location"],
            "site": job["site"],
            "job_url": job["job_url"]
        }
    }

# ------------------------------------------------------------------------------
# Free Local Career AI Assistant Chatbot
# ------------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    email: Optional[str] = DEFAULT_EMAIL
    user_email: Optional[str] = DEFAULT_EMAIL

@app.post("/api/chat")
async def chat_with_career_assistant(req: ChatRequest):
    user_email = req.email or req.user_email or DEFAULT_EMAIL
    user = get_user_by_email(user_email)
    response_data = get_career_assistant_response(req.message, user)
    return {
        "status": "ok", 
        "data": response_data,
        "reply": response_data.get("reply", "")
    }

# ------------------------------------------------------------------------------
# 100% Free Telegram Instant Job Alerts
# ------------------------------------------------------------------------------
@app.post("/api/telegram/test")
async def test_telegram_endpoint(req: TelegramTestRequest):
    success, message = test_telegram_connection(req.bot_token, req.chat_id)
    if success:
        return {"status": "ok", "message": message}
    raise HTTPException(status_code=400, detail=message)

@app.post("/api/telegram/send-job-alert")
async def send_telegram_job_alert_endpoint(req: TelegramJobAlertRequest):
    user = get_user_by_email(req.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    token = user.get("telegram_bot_token")
    cid = user.get("telegram_chat_id")
    if not token or not cid:
        raise HTTPException(status_code=400, detail="Telegram bot token and chat ID not configured.")

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM jobs WHERE id = ?", (req.job_id,))
    job_row = c.fetchone()
    conn.close()
    if not job_row:
        raise HTTPException(status_code=404, detail="Job not found.")

    job_dict = dict(job_row)
    match_info = calculate_job_match(
        job=job_dict,
        user_skills=user.get("skills", []),
        user_experience=user.get("experience_level", "fresher"),
        target_role=user.get("target_role", "Software Engineer")
    )
    sent = send_telegram_job_alert(
        token, cid, job_dict,
        match_score=match_info.get("score", 0),
        skills=user.get("skills", [])
    )
    if sent:
        return {"status": "ok", "message": "Alert sent to your Telegram!"}
    raise HTTPException(status_code=500, detail="Failed to send Telegram message. Please check Bot Token and Chat ID.")

# ------------------------------------------------------------------------------
# 1-Click Application Quick-Copy & Universal Portal Auto-Fill Engine
# ------------------------------------------------------------------------------
@app.get("/api/autofill/profile")
async def get_autofill_profile(email: str = DEFAULT_EMAIL):
    user = get_user_by_email(email) or {}
    name = (user.get("name") or "Candidate").strip()
    skills = user.get("skills") or ["Python", "SQL", "JavaScript", "React"]
    skills_str = ", ".join(skills[:4])

    parts = name.split()
    first_name = parts[0] if parts else ""
    last_name = " ".join(parts[1:]) if len(parts) > 1 else first_name

    profile_data = {
        "name": name,
        "first_name": first_name,
        "last_name": last_name,
        "email": user.get("email") or email,
        "phone": user.get("phone") or "",
        "current_city": user.get("current_city") or "Bengaluru, Karnataka, India",
        "linkedin_url": user.get("linkedin_url") or "",
        "github_url": user.get("github_url") or "",
        "portfolio_url": user.get("portfolio_url") or "",
        "years_experience": user.get("years_experience") or "1",
        "experience_level": user.get("experience_level") or "fresher",
        "target_role": user.get("target_role") or "Software Engineer",
        "notice_period": user.get("notice_period") or "Immediate",
        "expected_ctc": user.get("expected_ctc") or "Competitive / Market Standard",
        "work_authorization": user.get("work_authorization") or "Authorized to work in India (Citizen/Permanent Resident)",
        "visa_sponsorship": user.get("visa_sponsorship") or "No",
        "skills": skills,
        "why_hire_me": (
            f"I bring strong practical engineering foundations in {skills_str} and hands-on experience building clean, production-ready software. "
            f"My rapid adaptability and structured problem-solving approach enable me to deliver high impact on engineering roadmaps from day one."
        ),
        "why_this_company": (
            f"I have been tracking your engineering team's innovations and product momentum with great interest. "
            f"The opportunity to solve real-world scalability challenges aligns directly with my technical focus in {skills_str}."
        ),
        "experience_summary": (
            f"Software Engineer experienced in {skills_str}. Built and delivered modern full-stack workflows, reliable APIs, "
            f"and robust automated test suites with a focus on code readability and performance."
        )
    }

    bookmarklet_code = "javascript:(function(){var s=document.createElement('script');s.src='http://127.0.0.1:8765/static/autofill-bookmarklet.js?t='+Date.now();document.body.appendChild(s);})();"

    return {
        "status": "ok",
        "profile": profile_data,
        "bookmarklet_code": bookmarklet_code
    }

@app.post("/api/autofill/profile")
async def save_autofill_profile(req: ProfileUpdateRequest):
    data = req.dict(exclude_unset=True)
    updated = update_user_profile(data)
    if not updated:
        raise HTTPException(status_code=400, detail="Failed to update autofill profile.")
    return {"status": "ok", "message": "Autofill profile updated successfully!", "profile": updated}

@app.post("/api/autofill/generate-custom")
async def generate_custom_autofill_answers(req: AutofillCustomRequest):
    user = get_user_by_email(req.user_email) or {}
    user_skills = user.get("skills") or ["Python", "FastAPI", "React", "SQL"]
    matched = [s for s in user_skills if s.lower() in ((req.job_snippet or "") + " " + req.role).lower()]
    if not matched:
        matched = user_skills[:4]
    skills_str = ", ".join(matched[:4])
    company = req.company or "your company"
    role = req.role or "Software Engineer"

    why_hire = (
        f"For the {role} position at {company}, I bring hands-on experience with {skills_str} and a track record of building reliable, maintainable code. "
        f"I focus on clean architecture, comprehensive test coverage, and clear documentation. I am eager to apply my problem-solving skills to {company}'s technical priorities."
    )

    why_company = (
        f"I admire {company}'s focus on engineering excellence and customer impact. The challenges you are solving in {role} represent exactly the kind of high-impact problem domain where I want to build and grow. "
        f"My background in {skills_str} makes this a natural and mutually beneficial fit."
    )

    projects_summary = (
        f"1. Production API & Backend Services: Designed and implemented RESTful microservices using {skills_str}, optimizing queries to reduce latency.\n"
        f"2. Scalable Architecture: Built responsive frontends integrated with secure authentication, automated CI/CD pipelines, and relational database migrations."
    )

    biggest_challenge = (
        f"In a previous project, we faced performance bottlenecks during concurrent data ingestion. "
        f"By profiling bottlenecks, introducing asynchronous worker queues, and tuning SQL indexing, I helped reduce query execution times by over 40%."
    )

    salary_notes = (
        f"Expected Compensation: {user.get('expected_ctc') or 'Competitive / Market standard for ' + role}. "
        f"Notice Period: {user.get('notice_period') or 'Immediate'}. Ready to onboard quickly."
    )

    return {
        "status": "ok",
        "company": company,
        "role": role,
        "answers": {
            "why_hire_me": why_hire,
            "why_this_company": why_company,
            "projects_summary": projects_summary,
            "biggest_challenge": biggest_challenge,
            "salary_notes": salary_notes
        }
    }

@app.get("/api/autofill/{job_id}")
async def get_application_autofill(job_id: str, email: str = DEFAULT_EMAIL):
    user = get_user_by_email(email) or {}
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found.")
    job = dict(row)

    name = (user.get("name") or "Candidate").strip()
    skills = user.get("skills") or ["Python", "SQL"]
    matched_skills = [s for s in skills if s.lower() in (job.get("snippet", "") + " " + job.get("title", "")).lower()]
    if not matched_skills:
        matched_skills = skills[:3]
    skills_str = ", ".join(matched_skills[:4])
    company = job.get("company", "the company")
    title = job.get("title", "Software Engineer")

    why_hire = (
        f"I bring strong practical engineering foundations in {skills_str} and hands-on experience building reliable, production-ready software. "
        f"My proactive problem-solving mindset and rapid adaptability make me ready to hit the ground running on {company}'s engineering objectives."
    )
    why_company = (
        f"I have been closely following {company}'s growth and product impact. The {title} role is a direct match with my background in {skills_str}, "
        f"and I am enthusiastic about contributing clean, maintainable code to your team."
    )
    experience_summary = (
        f"Software Developer with focused experience in {skills_str}. Built and deployed full-stack solutions with modern development workflows, "
        f"clean architecture, and robust automated testing."
    )

    return {
        "status": "ok",
        "snippets": {
            "name": name,
            "email": user.get("email", ""),
            "phone": user.get("phone", ""),
            "linkedin_url": user.get("linkedin_url", ""),
            "github_url": user.get("github_url", ""),
            "portfolio_url": user.get("portfolio_url", ""),
            "years_experience": user.get("years_experience", "0-1"),
            "notice_period": user.get("notice_period", "Immediate"),
            "expected_ctc": user.get("expected_ctc", "As per company standards"),
            "why_hire_me": why_hire,
            "why_this_company": why_company,
            "experience_summary": experience_summary
        }
    }

# ------------------------------------------------------------------------------
# Multi-Source Scraper Background Worker
# ------------------------------------------------------------------------------
def run_scrape_background():
    global SCAN_STATE
    SCAN_STATE["is_running"] = True
    SCAN_STATE["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cfg = load_config()
        new_jobs = scrape_all_sources(cfg)
        SCAN_STATE["last_result"] = f"Found {new_jobs} new positions across LinkedIn, Indeed, Internshala, Naukri & Google!"
    except Exception as e:
        logger.error(f"Scraper agent error: {e}", exc_info=True)
        SCAN_STATE["last_result"] = f"Error: {str(e)}"
    finally:
        SCAN_STATE["is_running"] = False

@app.post("/api/automation/scan-now")
async def trigger_scan(bg_tasks: BackgroundTasks):
    global SCAN_STATE
    if SCAN_STATE["is_running"]:
        return {"status": "already_running", "message": "Scraper is already active in the background"}
    
    bg_tasks.add_task(run_scrape_background)
    return {
        "status": "started", 
        "message": "Scraper started across LinkedIn, Indeed, Internshala, Naukri & Google Jobs!"
    }

@app.get("/api/automation/scan-status")
async def get_scan_status():
    return SCAN_STATE

class AutoScrapeSettingsRequest(BaseModel):
    enabled: bool = True
    lead_minutes: int = 30

@app.post("/api/automation/auto-scrape-settings")
async def update_auto_scrape_settings(req: AutoScrapeSettingsRequest):
    global SCAN_STATE
    SCAN_STATE["auto_scrape_enabled"] = req.enabled
    SCAN_STATE["lead_minutes"] = max(5, min(120, req.lead_minutes))
    return {
        "status": "ok",
        "auto_scrape_enabled": SCAN_STATE["auto_scrape_enabled"],
        "lead_minutes": SCAN_STATE["lead_minutes"],
        "message": f"Pre-digest auto-scrape set to {SCAN_STATE['lead_minutes']} mins before email dispatch."
    }

@app.get("/api/automation/pipeline-status")
async def get_pipeline_status(email: Optional[str] = None):
    global SCAN_STATE
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = cursor.fetchone()[0]

    email_time = get_system_setting("global_email_schedule_time", "20:00") or "20:00"
    clean_email = (email or "").strip().lower()
    if clean_email:
        cursor.execute("SELECT email_time FROM users WHERE LOWER(email) = ? LIMIT 1", (clean_email,))
        row = cursor.fetchone()
        if row and row["email_time"]:
            email_time = row["email_time"]
    conn.close()

    lead_min = int(SCAN_STATE.get("lead_minutes", 30))
    next_scrape = get_time_minus_minutes(email_time, lead_min)

    return {
        "status": "ok",
        "is_running": SCAN_STATE["is_running"],
        "last_run": SCAN_STATE["last_run"],
        "last_result": SCAN_STATE["last_result"],
        "auto_scrape_enabled": SCAN_STATE.get("auto_scrape_enabled", True),
        "lead_minutes": lead_min,
        "next_scheduled_scrape": next_scrape,
        "next_scheduled_digest": email_time,
        "total_jobs_in_db": total_jobs,
        "platforms": ["LinkedIn", "Indeed", "Glassdoor", "Internshala", "Naukri", "Google Jobs"],
        "country": "India"
    }

# ------------------------------------------------------------------------------
# Daily Email Digest Trigger & Schedule Endpoints
# ------------------------------------------------------------------------------
@app.post("/api/automation/send-digest")
async def send_digest_api(req: SendDigestRequest):
    user = get_user_by_email(req.user_email)
    if not user:
        user = {
            "email": req.user_email,
            "name": req.user_email.split("@")[0].capitalize(),
            "target_role": "Software Engineer",
            "experience_level": "fresher",
            "email_experience_filter": "1_year",
            "skills": ["Python", "JavaScript", "SQL"]
        }

    if req.experience_filter:
        user["email_experience_filter"] = req.experience_filter
    if req.roles is not None:
        user["email_roles"] = req.roles
    if req.languages is not None:
        user["email_languages"] = req.languages

    success, message, count = send_personalized_digest_to_user(user, force_send=True)
    if success:
        return {"status": "ok", "message": message, "job_count": count}
    else:
        return {"status": "failed", "message": message, "job_count": count}

class ScheduleRequest(BaseModel):
    email: str
    email_time: str
    daily_email: bool = True

@app.post("/api/automation/schedule")
async def update_schedule_endpoint(req: ScheduleRequest):
    clean_time = normalize_time_str(req.email_time)
    updated = update_user_schedule(req.email, clean_time, req.daily_email)
    clean_email = (req.email or "").strip().lower()
    set_system_setting("global_email_schedule_time", clean_time)
    
    # Update config.yaml for default scheduler fallback
    try:
        import yaml
        config_path = BASE_DIR / "config.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            if "schedule" not in cfg:
                cfg["schedule"] = {}
            cfg["schedule"]["time"] = clean_time
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(cfg, f, sort_keys=False)
    except Exception as e:
        logger.warning(f"Could not update config.yaml: {e}")

    # Clear memory cache and reset last_digest_date so that if candidate changed
    # to current time or past time today, catch-up dispatches immediately
    global SCHEDULED_LAST_SENT
    SCHEDULED_LAST_SENT = {k for k in SCHEDULED_LAST_SENT if not k.startswith(clean_email)}
    reset_user_digest_tracking(clean_email)
    triggered = check_and_send_scheduled_digests()

    return {
        "status": "ok", 
        "user": updated, 
        "message": f"Daily email digest scheduled for {clean_time} every day!",
        "triggered_now": clean_email in triggered
    }

# ------------------------------------------------------------------------------
# Email Delivery Settings (Render Free Tier HTTPS & SMTP Support)
# ------------------------------------------------------------------------------
class EmailSettingsUpdateRequest(BaseModel):
    resend_api_key: Optional[str] = None
    brevo_api_key: Optional[str] = None
    webhook_url: Optional[str] = None
    sender_email: Optional[str] = None
    sender_app_password: Optional[str] = None

@app.get("/api/ping")
async def ping_endpoint():
    """Keep-alive endpoint for cloud hosting services (Render, Railway, Fly). Also triggers any pending digests."""
    now_ist = datetime.now(IST)
    triggered = check_and_send_scheduled_digests()
    return {
        "status": "alive",
        "service": "JobRadar AI 2.0",
        "current_time_ist": now_ist.strftime("%H:%M:%S"),
        "date_ist": now_ist.strftime("%Y-%m-%d"),
        "timezone": "Asia/Kolkata (IST)",
        "pending_digests_triggered": triggered
    }

@app.get("/api/automation/email-settings")
async def get_email_settings_endpoint():
    resend_key = (os.getenv("RESEND_API_KEY") or get_system_setting("resend_api_key") or "").strip()
    brevo_key = (os.getenv("BREVO_API_KEY") or get_system_setting("brevo_api_key") or "").strip()
    webhook_url = (os.getenv("EMAIL_WEBHOOK_URL") or get_system_setting("email_webhook_url") or "").strip()
    sender_email = (os.getenv("SENDER_EMAIL") or get_system_setting("sender_email") or "sharanujm@gmail.com").strip()
    has_smtp = bool(os.getenv("SENDER_APP_PASSWORD") or get_system_setting("sender_password") or get_system_setting("sender_app_password"))

    # Fallback to email_credentials.json on disk if present
    try:
        cred_file = BASE_DIR / "email_credentials.json"
        if cred_file.exists():
            with open(cred_file, "r", encoding="utf-8") as f:
                fcreds = json.load(f) or {}
            if not resend_key:
                resend_key = (fcreds.get("resend_api_key") or "").strip()
            if not brevo_key:
                brevo_key = (fcreds.get("brevo_api_key") or "").strip()
            if not webhook_url:
                webhook_url = (fcreds.get("email_webhook_url") or "").strip()
            if not has_smtp:
                has_smtp = bool(fcreds.get("sender_password") or fcreds.get("sender_app_password"))
            if not sender_email or sender_email == "sharanujm@gmail.com":
                sender_email = (fcreds.get("sender_email") or sender_email).strip()
    except Exception:
        pass

    is_render = bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID"))

    active_method = "none"
    if resend_key:
        active_method = "resend"
    elif brevo_key:
        active_method = "brevo"
    elif webhook_url:
        active_method = "webhook"
    elif has_smtp:
        active_method = "smtp"

    masked_resend = (resend_key[:6] + "..." + resend_key[-4:]) if len(resend_key) > 10 else resend_key
    masked_brevo = (brevo_key[:6] + "..." + brevo_key[-4:]) if len(brevo_key) > 10 else brevo_key

    return {
        "status": "ok",
        "resend_api_key": masked_resend,
        "has_resend": bool(resend_key),
        "brevo_api_key": masked_brevo,
        "has_brevo": bool(brevo_key),
        "webhook_url": webhook_url,
        "has_webhook": bool(webhook_url),
        "sender_email": sender_email,
        "has_app_password": has_smtp,
        "is_render": is_render,
        "active_method": active_method
    }

@app.post("/api/automation/email-settings")
async def update_email_settings_endpoint(req: EmailSettingsUpdateRequest):
    if req.resend_api_key is not None:
        val = req.resend_api_key.strip()
        if val and not val.endswith("..."):
            set_system_setting("resend_api_key", val)
    if req.brevo_api_key is not None:
        val = req.brevo_api_key.strip()
        if val and not val.endswith("..."):
            set_system_setting("brevo_api_key", val)
    if req.webhook_url is not None:
        set_system_setting("email_webhook_url", req.webhook_url.strip())
    if req.sender_email is not None and req.sender_email.strip():
        set_system_setting("sender_email", req.sender_email.strip())
    if req.sender_app_password is not None and req.sender_app_password.strip():
        clean_pass = req.sender_app_password.replace(" ", "").strip()
        if clean_pass and not clean_pass.endswith("..."):
            set_system_setting("sender_password", clean_pass)
            set_system_setting("sender_app_password", clean_pass)

    return {"status": "ok", "message": "Email delivery settings saved successfully!"}

class TestEmailRequest(BaseModel):
    recipient: str

@app.post("/api/automation/test-email")
async def test_email_endpoint(req: TestEmailRequest):
    user = get_user_by_email(req.recipient) or {
        "email": req.recipient,
        "name": req.recipient.split("@")[0].capitalize(),
        "target_role": "Software Engineer",
        "experience_level": "fresher",
        "email_experience_filter": "1_year",
        "skills": ["Python", "JavaScript", "SQL"]
    }
    success, message, count = send_personalized_digest_to_user(user, force_send=True)
    return {
        "status": "ok" if success else "failed",
        "message": message,
        "job_count": count
    }

# ------------------------------------------------------------------------------
# Resume ATS Analysis & Bullet Enhancer
# ------------------------------------------------------------------------------
class ResumeAnalyzeRequest(BaseModel):
    email: Optional[str] = DEFAULT_EMAIL
    resume_text: Optional[str] = ""

@app.post("/api/resume/analyze")
async def analyze_resume_endpoint(req: ResumeAnalyzeRequest):
    user = get_user_by_email(req.email) or {}
    text = req.resume_text or user.get("resume_text", "")
    exp = user.get("experience_level", "fresher")
    role = user.get("target_role", "Software Engineer")
    analysis = analyze_resume_ats(text, user_exp=exp, target_role=role)
    return {
        "status": "ok", 
        "analysis": analysis, 
        "filename": user.get("resume_filename", ""),
        "skills": user.get("skills", [])
    }

class BulletRequest(BaseModel):
    bullet: str

@app.post("/api/resume/enhance-bullet")
async def enhance_bullet_endpoint(req: BulletRequest):
    res = enhance_resume_bullet(req.bullet)
    return {"status": "ok", "result": res}

# ------------------------------------------------------------------------------
# Study Vault & Interview Prep Resources Endpoints
# ------------------------------------------------------------------------------
class ResourceLinkRequest(BaseModel):
    user_email: str
    title: str
    category: Optional[str] = "General"
    url: Optional[str] = ""
    description: Optional[str] = ""
    content_text: Optional[str] = ""
    tags: Optional[List[str]] = []

class ResourceToggleRequest(BaseModel):
    resource_id: int
    user_email: str

class ResourceNotesRequest(BaseModel):
    resource_id: int
    notes: str
    user_email: Optional[str] = ""

class ResourceAIAssistRequest(BaseModel):
    resource_id: int
    action: str = "takeaways"  # "takeaways" or "quiz"

@app.get("/api/resources")
async def get_resources_endpoint(email: str = DEFAULT_EMAIL):
    resources = get_resources_for_user(email)
    return {"status": "ok", "resources": resources}

@app.post("/api/resources/upload")
async def upload_resource_file(
    email: str = Form(DEFAULT_EMAIL),
    title: str = Form(...),
    category: str = Form("General"),
    description: str = Form(""),
    file: UploadFile = File(...)
):
    try:
        clean_filename = f"{int(datetime.now().timestamp())}_{file.filename}"
        dest_path = RESOURCES_DIR / clean_filename
        content = await file.read()
        dest_path.write_bytes(content)

        res_type = "pdf" if file.filename.lower().endswith(".pdf") else "document"
        new_res = add_resource({
            "user_email": email,
            "title": title or file.filename,
            "category": category or "General",
            "resource_type": res_type,
            "file_path": str(dest_path),
            "url": f"/api/resources/file/{clean_filename}",
            "description": description,
            "tags": [category, res_type.upper()]
        })
        return {"status": "ok", "resource": new_res}
    except Exception as e:
        logger.error(f"Error uploading study resource file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/resources/add-link")
async def add_resource_link_endpoint(req: ResourceLinkRequest):
    new_res = add_resource({
        "user_email": req.user_email,
        "title": req.title,
        "category": req.category or "General",
        "resource_type": "link" if req.url else "note",
        "url": req.url or "",
        "content_text": req.content_text or "",
        "description": req.description or "",
        "tags": req.tags or [req.category]
    })
    return {"status": "ok", "resource": new_res}

@app.post("/api/resources/toggle-status")
async def toggle_resource_status_endpoint(req: ResourceToggleRequest):
    new_status = toggle_resource_completion(req.resource_id, req.user_email)
    return {"status": "ok", "is_completed": new_status}

@app.post("/api/resources/save-notes")
async def save_resource_notes_endpoint(req: ResourceNotesRequest):
    ok = update_resource_notes(req.resource_id, req.notes, req.user_email or "")
    return {"status": "ok", "saved": ok}

@app.post("/api/resources/ai-assist")
async def ai_study_assist_endpoint(req: ResourceAIAssistRequest):
    result = generate_ai_study_assist(req.resource_id, req.action)
    return result

@app.delete("/api/resources/{resource_id}")
async def delete_resource_endpoint(resource_id: int, email: str = DEFAULT_EMAIL):
    deleted = delete_resource(resource_id, email)
    return {"status": "ok", "deleted": deleted}

@app.get("/api/resources/file/{filename}")
async def get_resource_file(filename: str, download: bool = False):
    target = RESOURCES_DIR / filename
    if target.exists() and target.is_file():
        media_type = "application/pdf" if filename.lower().endswith(".pdf") else "application/octet-stream"
        disposition_type = "attachment" if download else "inline"
        return FileResponse(
            target, 
            media_type=media_type, 
            filename=filename, 
            content_disposition_type=disposition_type
        )
    raise HTTPException(status_code=404, detail="Resource file not found.")

# ------------------------------------------------------------------------------
# Indian Tech Salary Studio & Counter-Offer Negotiation Endpoints
# ------------------------------------------------------------------------------
class SalaryEstimateRequest(BaseModel):
    role: str = "software_engineer"
    experience: str = "fresher"
    location: str = "bangalore"
    company_tier: str = "product_unicorn"
    skills: Optional[List[str]] = []
    current_offered_lpa: Optional[float] = None

class CounterOfferRequest(BaseModel):
    candidate_name: str
    company_name: str
    role_title: str
    current_offered_lpa: float
    target_lpa: float
    competing_offer_lpa: Optional[float] = None
    competing_company: Optional[str] = None
    key_skills: Optional[List[str]] = []
    negotiation_focus: str = "polite_counter"

@app.post("/api/salary/estimate")
async def estimate_salary_endpoint(req: SalaryEstimateRequest):
    try:
        data = estimate_compensation(
            role=req.role,
            experience=req.experience,
            location=req.location,
            company_tier=req.company_tier,
            skills=req.skills,
            current_offered_lpa=req.current_offered_lpa
        )
        return {"status": "ok", "data": data}
    except Exception as e:
        logger.error(f"Error estimating compensation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/salary/negotiation-scripts")
async def generate_negotiation_scripts_endpoint(req: CounterOfferRequest):
    try:
        data = generate_counter_offer_scripts(
            candidate_name=req.candidate_name,
            company_name=req.company_name,
            role_title=req.role_title,
            current_offered_lpa=req.current_offered_lpa,
            target_lpa=req.target_lpa,
            competing_offer_lpa=req.competing_offer_lpa,
            competing_company=req.competing_company,
            key_skills=req.key_skills,
            negotiation_focus=req.negotiation_focus
        )
        return {"status": "ok", "data": data}
    except Exception as e:
        logger.error(f"Error generating counter offer scripts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ------------------------------------------------------------------------------
# LinkedIn Senior Referral & Alumni Outreach Hub
# ------------------------------------------------------------------------------
@app.get("/api/referral/hub/{job_id}")
async def get_referral_hub_endpoint(
    job_id: str,
    email: str = Query(DEFAULT_EMAIL),
    senior_name: str = Query(""),
    college_name: str = Query(""),
    company_keyword: str = Query("")
):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    job = dict(row)
    if company_keyword and company_keyword.strip():
        job["company"] = company_keyword.strip()
    user = get_user_by_email(email) or {}
    college = college_name or user.get("college_name") or ""
    data = generate_referral_pitch_suite(job, user, senior_name=senior_name, college_name=college)
    return {"status": "ok", "data": data}

@app.post("/api/referral/generate")
async def generate_referral_endpoint(req: ReferralHubRequest):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM jobs WHERE id = ?", (req.job_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")
    job = dict(row)
    if req.company_keyword and req.company_keyword.strip():
        job["company"] = req.company_keyword.strip()
    if req.job_ref and req.job_ref.strip():
        job["id"] = req.job_ref.strip()
    user = get_user_by_email(req.user_email) or {}
    college = req.college_name or user.get("college_name") or ""
    data = generate_referral_pitch_suite(
        job, 
        user, 
        senior_name=req.senior_name or "", 
        college_name=college, 
        senior_role=req.senior_role or ""
    )
    return {"status": "ok", "data": data}

@app.post("/api/referral/track")
async def track_referral_endpoint(req: ReferralTrackRequest):
    clean_email = req.user_email.strip().lower()
    senior_info = f"Senior: {req.senior_name.strip()}" if req.senior_name else "Senior Referral"
    if req.senior_profile_url:
        senior_info += f" ({req.senior_profile_url.strip()})"
    if req.senior_role:
        senior_info += f" [{req.senior_role.strip()}]"
    
    combined_notes = senior_info
    if req.notes:
        combined_notes += f" | {req.notes.strip()}"
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    update_tracker_stage(
        user_email=clean_email,
        job_id=req.job_id,
        status="referral_requested",
        notes=combined_notes,
        applied_date=today_str
    )
    stats = get_stats(user_email=clean_email)
    return {
        "status": "ok",
        "message": f"Tracked referral request for {req.senior_name or 'Company Senior'}!",
        "stats": stats
    }

# ------------------------------------------------------------------------------
# AI Technical & HR Mock Interview Simulator Endpoints
# ------------------------------------------------------------------------------
class InterviewStartRequest(BaseModel):
    job_id: Optional[str] = None
    user_email: Optional[str] = DEFAULT_EMAIL
    focus_area: Optional[str] = "comprehensive"
    company: Optional[str] = None
    title: Optional[str] = None

class InterviewEvaluateRequest(BaseModel):
    question_data: Dict[str, Any]
    candidate_answer: str
    experience_level: Optional[str] = "fresher"

@app.post("/api/interview/start")
async def start_interview_endpoint(req: InterviewStartRequest):
    job = {}
    if req.job_id:
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM jobs WHERE id = ?", (req.job_id,))
        row = c.fetchone()
        conn.close()
        if row:
            job = dict(row)
    
    if not job:
        job = {
            "id": req.job_id or "custom_target",
            "company": req.company or "Leading Tech Firm",
            "title": req.title or "Software Engineer",
            "snippet": "Python, SQL, JavaScript, React, System Design, REST APIs, Microservices"
        }
    
    user = get_user_by_email(req.user_email) or {}
    session_data = generate_mock_interview(job, user, req.focus_area or "comprehensive")
    return {"status": "ok", "session": session_data}

@app.post("/api/interview/evaluate")
async def evaluate_interview_endpoint(req: InterviewEvaluateRequest):
    result = evaluate_interview_answer(
        question_data=req.question_data,
        candidate_answer=req.candidate_answer,
        experience_level=req.experience_level or "fresher"
    )
    return {"status": "ok", "evaluation": result}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8765))
    host = os.environ.get("HOST", "0.0.0.0")
    uvicorn.run("server:app", host=host, port=port, reload=False)
