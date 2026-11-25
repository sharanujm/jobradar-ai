import sqlite3
import hashlib
import json
import logging
import time
import random
import functools
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any

logger = logging.getLogger("Database")

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "jobs.db"

def get_connection(db_path: Path = DB_PATH, timeout: float = 60.0) -> sqlite3.Connection:
    """Returns a new SQLite connection with WAL mode, normal synchronous, and busy timeout configured."""
    conn = sqlite3.connect(str(db_path), timeout=timeout, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute(f"PRAGMA busy_timeout = {int(timeout * 1000)};")
        conn.execute("PRAGMA cache_size = -64000;")
    except Exception:
        pass
    return conn

def with_db_retry(max_retries: int = 8, base_delay: float = 0.2):
    """
    Decorator that catches sqlite3.OperationalError: database is locked / busy
    and transparently retries with exponential backoff and jitter.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_err = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    last_err = e
                    err_msg = str(e).lower()
                    if "locked" in err_msg or "busy" in err_msg:
                        if attempt == max_retries - 1:
                            logger.error(f"[DB LOCKED] {func.__name__} exhausted {max_retries} retries: {e}")
                            raise
                        sleep_time = (base_delay * (1.6 ** attempt)) + random.uniform(0.04, 0.12)
                        logger.warning(f"[DB BUSY] {func.__name__} locked, retrying in {sleep_time:.2f}s (attempt {attempt+1}/{max_retries})...")
                        time.sleep(sleep_time)
                    else:
                        raise
            if last_err:
                raise last_err
        return wrapper
    return decorator

def _get_table_columns(cursor, table_name: str) -> set:
    """Helper to retrieve existing column names of a table to avoid duplicate ALTER TABLE locks."""
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        return {row[1] for row in cursor.fetchall()}
    except Exception:
        return set()

@with_db_retry(max_retries=6, base_delay=0.2)
def init_db(db_path: Path = DB_PATH) -> None:
    """Initialize SQLite database schema and migrate missing columns idempotently."""
    conn = get_connection(db_path, timeout=60.0)
    try:
        cursor = conn.cursor()
        # Set WAL mode and normal synchronous once
        cursor.execute("PRAGMA journal_mode = WAL;")
        cursor.execute("PRAGMA synchronous = NORMAL;")

        # Jobs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                site TEXT,
                title TEXT,
                company TEXT,
                location TEXT,
                job_url TEXT,
                date_posted TEXT,
                job_type TEXT,
                salary TEXT,
                is_remote INTEGER,
                snippet TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                emailed_at TIMESTAMP NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_emailed ON jobs(emailed_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at)")

        # Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                name TEXT,
                password TEXT DEFAULT 'password123',
                target_role TEXT DEFAULT 'Software Engineer',
                experience_level TEXT DEFAULT 'fresher',
                skills TEXT DEFAULT '[]',
                resume_text TEXT DEFAULT '',
                resume_filename TEXT DEFAULT '',
                daily_email INTEGER DEFAULT 1,
                email_time TEXT DEFAULT '20:00',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # User Job Interactions Table (Saved / Applied / Interviewing / Offered / Rejected)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_job_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT,
                job_id TEXT,
                status TEXT,
                notes TEXT DEFAULT '',
                applied_date TEXT DEFAULT '',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_email, job_id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_interactions_user ON user_job_interactions(user_email)")

        # Multi-User Email Deliveries Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_job_deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT,
                job_id TEXT,
                delivered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_email, job_id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_deliveries_user ON user_job_deliveries(user_email)")

        # System Settings Table (SMTP credentials, schedule fallbacks, etc.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Seed default SMTP settings from environment or defaults if not present
        try:
            import os
            from dotenv import load_dotenv
            load_dotenv(BASE_DIR / ".env")
            s_email = os.getenv("SENDER_EMAIL", "").strip() or "sharanujm@gmail.com"
            s_pass = os.getenv("SENDER_APP_PASSWORD", "").strip()
            cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('sender_email', ?)", (s_email,))
            if s_pass:
                cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES ('sender_password', ?)", (s_pass,))
            cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('smtp_host', 'smtp.gmail.com')")
            cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('smtp_port', '465')")
            cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('use_ssl', 'true')")

            cred_file = BASE_DIR / "email_credentials.json"
            if cred_file.exists():
                try:
                    with open(cred_file, "r", encoding="utf-8") as f:
                        creds = json.load(f) or {}
                    for k, v in creds.items():
                        if v:
                            cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)", (k, str(v)))
                except Exception:
                    pass
        except Exception:
            pass

        # Idempotent Column Migrations: ONLY run ALTER TABLE if column does NOT already exist!
        user_cols = _get_table_columns(cursor, "users")
        interaction_cols = _get_table_columns(cursor, "user_job_interactions")
        job_cols = _get_table_columns(cursor, "jobs")

        interactions_to_add = [
            ("notes", "ALTER TABLE user_job_interactions ADD COLUMN notes TEXT DEFAULT ''"),
            ("applied_date", "ALTER TABLE user_job_interactions ADD COLUMN applied_date TEXT DEFAULT ''"),
        ]
        for col_name, sql in interactions_to_add:
            if col_name not in interaction_cols:
                try:
                    cursor.execute(sql)
                except Exception:
                    pass

        users_to_add = [
            ("password", "ALTER TABLE users ADD COLUMN password TEXT DEFAULT 'password123'"),
            ("email_time", "ALTER TABLE users ADD COLUMN email_time TEXT DEFAULT '20:00'"),
            ("daily_email", "ALTER TABLE users ADD COLUMN daily_email INTEGER DEFAULT 1"),
            ("telegram_bot_token", "ALTER TABLE users ADD COLUMN telegram_bot_token TEXT DEFAULT ''"),
            ("telegram_chat_id", "ALTER TABLE users ADD COLUMN telegram_chat_id TEXT DEFAULT ''"),
            ("telegram_alerts", "ALTER TABLE users ADD COLUMN telegram_alerts INTEGER DEFAULT 0"),
            ("phone", "ALTER TABLE users ADD COLUMN phone TEXT DEFAULT ''"),
            ("github_url", "ALTER TABLE users ADD COLUMN github_url TEXT DEFAULT ''"),
            ("linkedin_url", "ALTER TABLE users ADD COLUMN linkedin_url TEXT DEFAULT ''"),
            ("portfolio_url", "ALTER TABLE users ADD COLUMN portfolio_url TEXT DEFAULT ''"),
            ("years_experience", "ALTER TABLE users ADD COLUMN years_experience TEXT DEFAULT '0-1'"),
            ("email_experience_filter", "ALTER TABLE users ADD COLUMN email_experience_filter TEXT DEFAULT '1_year'"),
            ("email_roles", "ALTER TABLE users ADD COLUMN email_roles TEXT DEFAULT '[\"Software Engineer\"]'"),
            ("email_languages", "ALTER TABLE users ADD COLUMN email_languages TEXT DEFAULT '[\"Python\"]'"),
            ("notice_period", "ALTER TABLE users ADD COLUMN notice_period TEXT DEFAULT 'Immediate'"),
            ("expected_ctc", "ALTER TABLE users ADD COLUMN expected_ctc TEXT DEFAULT ''"),
            ("college_name", "ALTER TABLE users ADD COLUMN college_name TEXT DEFAULT ''"),
            ("email_locations", "ALTER TABLE users ADD COLUMN email_locations TEXT DEFAULT '[]'"),
            ("current_city", "ALTER TABLE users ADD COLUMN current_city TEXT DEFAULT 'Bengaluru, India'"),
            ("work_authorization", "ALTER TABLE users ADD COLUMN work_authorization TEXT DEFAULT 'Authorized to work (Citizen/PR)'"),
            ("visa_sponsorship", "ALTER TABLE users ADD COLUMN visa_sponsorship TEXT DEFAULT 'No'"),
            ("summary_bio", "ALTER TABLE users ADD COLUMN summary_bio TEXT DEFAULT ''"),
            ("last_digest_date", "ALTER TABLE users ADD COLUMN last_digest_date TEXT DEFAULT ''"),
            ("last_digest_at", "ALTER TABLE users ADD COLUMN last_digest_at TEXT DEFAULT ''")
        ]
        for col_name, sql in users_to_add:
            if col_name not in user_cols:
                try:
                    cursor.execute(sql)
                except Exception:
                    pass

        jobs_to_add = [
            ("min_exp", "ALTER TABLE jobs ADD COLUMN min_exp REAL DEFAULT NULL"),
            ("max_exp", "ALTER TABLE jobs ADD COLUMN max_exp REAL DEFAULT NULL"),
            ("exp_category", "ALTER TABLE jobs ADD COLUMN exp_category TEXT DEFAULT '1_year'")
        ]
        for col_name, sql in jobs_to_add:
            if col_name not in job_cols:
                try:
                    cursor.execute(sql)
                except Exception:
                    pass

        for idx_sql in [
            "CREATE INDEX IF NOT EXISTS idx_jobs_exp ON jobs(exp_category)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_minexp ON jobs(min_exp)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_location ON jobs(location)",
            "CREATE INDEX IF NOT EXISTS idx_jobs_site ON jobs(site)"
        ]:
            try:
                cursor.execute(idx_sql)
            except Exception:
                pass

        conn.commit()
    finally:
        conn.close()

@with_db_retry()
def backfill_jobs_experience(db_path: Path = DB_PATH, force: bool = False) -> int:
    """Calculates and stores min_exp, max_exp, and exp_category for existing jobs."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        if not force:
            cursor.execute("SELECT COUNT(*) FROM jobs WHERE min_exp IS NULL OR exp_category IS NULL")
            missing = cursor.fetchone()[0]
            if missing == 0:
                return 0

        if force:
            cursor.execute("SELECT id, title, snippet, job_url FROM jobs")
        else:
            cursor.execute("SELECT id, title, snippet, job_url FROM jobs WHERE min_exp IS NULL OR exp_category IS NULL")
        rows = cursor.fetchall()
        if not rows:
            return 0

        from .filter import parse_job_experience
        updated = 0
        batch = []
        for r in rows:
            min_e, max_e, cat = parse_job_experience(r["title"], r["snippet"], r["job_url"])
            batch.append((min_e, max_e, cat, r["id"]))
            if len(batch) >= 100:
                cursor.executemany("UPDATE jobs SET min_exp = ?, max_exp = ?, exp_category = ? WHERE id = ?", batch)
                conn.commit()
                updated += len(batch)
                batch = []
                time.sleep(0.03)
        if batch:
            cursor.executemany("UPDATE jobs SET min_exp = ?, max_exp = ?, exp_category = ? WHERE id = ?", batch)
            conn.commit()
            updated += len(batch)

        return updated
    finally:
        conn.close()

def generate_job_id(site: str, title: str, company: str, job_url: str) -> str:
    """Generate a consistent unique identifier for deduplication."""
    clean_url = (job_url or "").split("?")[0].strip().lower()
    raw = f"{site.lower()}|{title.lower().strip()}|{company.lower().strip()}|{clean_url}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

@with_db_retry()
def get_job_by_id(job_id: str, db_path: Path = DB_PATH) -> Optional[Dict]:
    """Retrieve a single job by its unique ID."""
    if not job_id:
        return None
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM jobs WHERE id = ?", (str(job_id),))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

@with_db_retry()
def get_scheduled_users(db_path: Path = DB_PATH) -> List[Dict]:
    """Retrieve all users who have daily digest emails enabled."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE daily_email = 1")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@with_db_retry()
def save_jobs_batch(jobs: List[dict], db_path: Path = DB_PATH) -> int:
    """Saves a batch of jobs in a single transaction, deduplicating existing entries."""
    if not jobs:
        return 0
    from .filter import parse_job_experience
    conn = get_connection(db_path)
    inserted = 0
    try:
        cursor = conn.cursor()
        for job in jobs:
            job_id = job.get("id") or generate_job_id(
                job.get("site", "unknown"),
                job.get("title", ""),
                job.get("company", ""),
                job.get("job_url", "")
            )
            min_exp = job.get("min_exp")
            max_exp = job.get("max_exp")
            exp_category = job.get("exp_category")
            if exp_category is None:
                min_exp, max_exp, exp_category = parse_job_experience(job.get("title", ""), job.get("snippet", ""), job.get("job_url", ""))
            try:
                cursor.execute("""
                    INSERT INTO jobs (
                        id, site, title, company, location, job_url, 
                        date_posted, job_type, salary, is_remote, snippet, emailed_at,
                        min_exp, max_exp, exp_category
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
                """, (
                    job_id,
                    job.get("site", "web"),
                    job.get("title", "Untitled Role"),
                    job.get("company", "Company"),
                    job.get("location", "Location Not Specified"),
                    job.get("job_url", "#"),
                    str(job.get("date_posted", "")),
                    str(job.get("job_type", "")),
                    str(job.get("salary", "")),
                    1 if job.get("is_remote") else 0,
                    job.get("snippet", "")[:600] if job.get("snippet") else "",
                    min_exp,
                    max_exp,
                    exp_category
                ))
                inserted += 1
            except sqlite3.IntegrityError:
                continue
        conn.commit()
        return inserted
    finally:
        conn.close()

@with_db_retry()
def save_job(job: dict, db_path: Path = DB_PATH) -> bool:
    """Saves a job if it does not already exist."""
    job_id = job.get("id") or generate_job_id(
        job.get("site", "unknown"),
        job.get("title", ""),
        job.get("company", ""),
        job.get("job_url", "")
    )

    min_exp = job.get("min_exp")
    max_exp = job.get("max_exp")
    exp_category = job.get("exp_category")
    if exp_category is None:
        from .filter import parse_job_experience
        min_exp, max_exp, exp_category = parse_job_experience(job.get("title", ""), job.get("snippet", ""), job.get("job_url", ""))

    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO jobs (
                id, site, title, company, location, job_url, 
                date_posted, job_type, salary, is_remote, snippet, emailed_at,
                min_exp, max_exp, exp_category
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
        """, (
            job_id,
            job.get("site", "web"),
            job.get("title", "Untitled Role"),
            job.get("company", "Company"),
            job.get("location", "Location Not Specified"),
            job.get("job_url", "#"),
            str(job.get("date_posted", "")),
            str(job.get("job_type", "")),
            str(job.get("salary", "")),
            1 if job.get("is_remote") else 0,
            job.get("snippet", "")[:600] if job.get("snippet") else "",
            min_exp,
            max_exp,
            exp_category
        ))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

@with_db_retry()
def get_unemailed_jobs(limit: int = 100, db_path: Path = DB_PATH) -> List[Dict]:
    """Legacy global unemailed jobs fetcher (filtered to India)."""
    from .filter import is_india_location
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM jobs 
            WHERE emailed_at IS NULL 
            ORDER BY created_at DESC, date_posted DESC
            LIMIT ?
        """, (limit * 2,))
        rows = cursor.fetchall()
        jobs = [dict(row) for row in rows if is_india_location(dict(row).get("location"), dict(row).get("site"))]
        return jobs[:limit]
    finally:
        conn.close()

@with_db_retry()
def get_unemailed_jobs_for_user(
    user_email: str, 
    limit: int = 100, 
    experience_filter: str = "",
    target_roles: Optional[List[str]] = None,
    target_languages: Optional[List[str]] = None,
    target_locations: Optional[List[str]] = None,
    years_exp: str = "",
    db_path: Path = DB_PATH
) -> List[Dict]:
    """
    Multi-user email delivery: fetches jobs that have NOT yet been delivered
    to this specific user's email address, strictly filtered to India, requested
    experience level, target roles, programming languages/tech stack, and preferred locations.
    """
    from .filter import is_india_location, matches_email_filter, get_job_experience_badge
    clean_email = (user_email or "").strip().lower()
    fetch_pool_size = max(limit * 25, 4500)

    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM jobs 
            WHERE id NOT IN (
                SELECT job_id FROM user_job_deliveries WHERE LOWER(user_email) = ?
            )
            ORDER BY created_at DESC, date_posted DESC
            LIMIT ?
        """, (clean_email, fetch_pool_size))
        rows = cursor.fetchall()
    finally:
        conn.close()

    matched = []
    for row in rows:
        job_dict = dict(row)
        if not is_india_location(job_dict.get("location"), job_dict.get("site")):
            continue
        if (experience_filter or target_roles or target_languages or target_locations) and not matches_email_filter(
            job_dict,
            exp_filter=experience_filter,
            target_roles=target_roles,
            target_languages=target_languages,
            target_locations=target_locations,
            years_exp=years_exp
        ):
            continue
        job_dict["exp_badge"] = get_job_experience_badge(job_dict)
        matched.append(job_dict)
        if len(matched) >= limit:
            break

    return matched

@with_db_retry()
def mark_jobs_as_emailed(job_ids: List[str], db_path: Path = DB_PATH) -> None:
    """Marks jobs as emailed globally (legacy support)."""
    if not job_ids:
        return
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        placeholders = ",".join("?" for _ in job_ids)
        cursor.execute(f"""
            UPDATE jobs 
            SET emailed_at = CURRENT_TIMESTAMP 
            WHERE id IN ({placeholders})
        """, job_ids)
        conn.commit()
    finally:
        conn.close()

@with_db_retry()
def mark_jobs_delivered_for_user(user_email: str, job_ids: List[str], db_path: Path = DB_PATH) -> None:
    """Records that specific job IDs were delivered to a given user email."""
    if not job_ids or not user_email:
        return
    clean_email = user_email.strip().lower()
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        for jid in job_ids:
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO user_job_deliveries (user_email, job_id, delivered_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (clean_email, str(jid)))
            except Exception:
                pass
        conn.commit()
    finally:
        conn.close()

@with_db_retry()
def get_stats(db_path: Path = DB_PATH, user_email: str = None) -> Dict[str, int]:
    """Returns database counts and user-specific tracking numbers."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM jobs")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM jobs WHERE emailed_at IS NOT NULL")
        emailed = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM jobs WHERE emailed_at IS NULL")
        pending = cursor.fetchone()[0]

        saved = 0
        applied = 0
        interviewing = 0
        offered = 0
        referrals = 0

        if user_email:
            clean_email = user_email.strip().lower()
            cursor.execute("SELECT COUNT(*) FROM user_job_interactions WHERE LOWER(user_email) = ? AND status = 'saved'", (clean_email,))
            saved = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM user_job_interactions WHERE LOWER(user_email) = ? AND status = 'applied'", (clean_email,))
            applied = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM user_job_interactions WHERE LOWER(user_email) = ? AND status = 'interviewing'", (clean_email,))
            interviewing = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM user_job_interactions WHERE LOWER(user_email) = ? AND (status = 'offered' OR status = 'offer')", (clean_email,))
            offered = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM user_job_interactions WHERE LOWER(user_email) = ? AND (status = 'referral' OR status = 'referral_requested')", (clean_email,))
            referrals = cursor.fetchone()[0]

        return {
            "total": total, 
            "emailed": emailed, 
            "pending": pending, 
            "saved": saved, 
            "applied": applied,
            "referrals": referrals,
            "interviewing": interviewing,
            "offered": offered
        }
    finally:
        conn.close()

@with_db_retry()
def get_jobs_list(
    search: str = "",
    site: str = "",
    experience: str = "",
    location: str = "",
    is_remote: Optional[bool] = None,
    status_filter: str = "",
    user_email: str = "",
    posted_within: str = "",
    skill_tag: str = "",
    limit: int = 60,
    offset: int = 0,
    db_path: Path = DB_PATH
) -> Tuple[List[Dict], int]:
    """
    Retrieve jobs with full-text search, strict experience boundaries,
    location filtering (Bangalore, Hyderabad, Pune, Remote, etc.), and status tracking.
    """
    try:
        limit = max(1, min(int(limit), 100))
    except (ValueError, TypeError):
        limit = 60
    try:
        offset = max(0, int(offset))
    except (ValueError, TypeError):
        offset = 0

    conditions = ["1=1"]
    params = []

    # 1. Search Query (Title, Company, Snippet)
    if search:
        s = f"%{search.strip().lower()}%"
        conditions.append("(LOWER(j.title) LIKE ? OR LOWER(j.company) LIKE ? OR LOWER(j.snippet) LIKE ? OR LOWER(j.location) LIKE ?)")
        params.extend([s, s, s, s])

    # 2. Location Filtering
    if location and location.strip().lower() not in ("all", "any", "all locations", "all cities"):
        loc_items = [l.strip().lower() for l in location.split(",") if l.strip() and l.strip().lower() not in ("all", "any", "all locations", "all cities")]
        if loc_items:
            loc_clauses = []
            for loc_clean in loc_items:
                if loc_clean in ("remote", "work from home", "wfh"):
                    loc_clauses.append("(j.is_remote = 1 OR LOWER(j.location) LIKE '%remote%' OR LOWER(j.title) LIKE '%remote%' OR LOWER(j.location) LIKE '%work from home%' OR LOWER(j.location) LIKE '%worldwide%' OR LOWER(j.location) LIKE '%anywhere%')")
                elif loc_clean in ("bangalore", "bengaluru", "karnataka"):
                    loc_clauses.append("(LOWER(j.location) LIKE '%bangalore%' OR LOWER(j.location) LIKE '%bengaluru%' OR LOWER(j.location) LIKE '%ka, in%' OR LOWER(j.location) LIKE '%karnataka%')")
                elif loc_clean in ("hyderabad", "telangana"):
                    loc_clauses.append("(LOWER(j.location) LIKE '%hyderabad%' OR LOWER(j.location) LIKE '%hyderābād%' OR LOWER(j.location) LIKE '%ts, in%' OR LOWER(j.location) LIKE '%telangana%')")
                elif loc_clean in ("pune", "maharashtra"):
                    loc_clauses.append("(LOWER(j.location) LIKE '%pune%' OR LOWER(j.location) LIKE '%pune division%')")
                elif loc_clean in ("chennai", "tamil nadu"):
                    loc_clauses.append("(LOWER(j.location) LIKE '%chennai%' OR LOWER(j.location) LIKE '%tn, in%' OR LOWER(j.location) LIKE '%tamil nadu%')")
                elif loc_clean in ("delhi", "ncr", "gurgaon", "gurugram", "noida", "haryana"):
                    loc_clauses.append("(LOWER(j.location) LIKE '%delhi%' OR LOWER(j.location) LIKE '%ncr%' OR LOWER(j.location) LIKE '%gurgaon%' OR LOWER(j.location) LIKE '%gurugram%' OR LOWER(j.location) LIKE '%noida%' OR LOWER(j.location) LIKE '%dl, in%' OR LOWER(j.location) LIKE '%haryana%')")
                elif loc_clean in ("mumbai", "navi mumbai"):
                    loc_clauses.append("(LOWER(j.location) LIKE '%mumbai%' OR LOWER(j.location) LIKE '%navi mumbai%' OR LOWER(j.location) LIKE '%bombay%' OR LOWER(j.location) LIKE '%thane%')")
                elif loc_clean in ("kolkata", "calcutta", "west bengal"):
                    loc_clauses.append("(LOWER(j.location) LIKE '%kolkata%' OR LOWER(j.location) LIKE '%calcutta%' OR LOWER(j.location) LIKE '%wb, in%' OR LOWER(j.location) LIKE '%west bengal%')")
                elif loc_clean in ("ahmedabad", "gujarat"):
                    loc_clauses.append("(LOWER(j.location) LIKE '%ahmedabad%' OR LOWER(j.location) LIKE '%gj, in%' OR LOWER(j.location) LIKE '%gujarat%' OR LOWER(j.location) LIKE '%gandhinagar%')")
                elif loc_clean in ("kochi", "cochin", "kerala", "trivandrum", "thiruvananthapuram"):
                    loc_clauses.append("(LOWER(j.location) LIKE '%kochi%' OR LOWER(j.location) LIKE '%cochin%' OR LOWER(j.location) LIKE '%trivandrum%' OR LOWER(j.location) LIKE '%thiruvananthapuram%' OR LOWER(j.location) LIKE '%kl, in%' OR LOWER(j.location) LIKE '%kerala%')")
                elif loc_clean in ("indore", "bhopal", "madhya pradesh"):
                    loc_clauses.append("(LOWER(j.location) LIKE '%indore%' OR LOWER(j.location) LIKE '%bhopal%' OR LOWER(j.location) LIKE '%mp, in%' OR LOWER(j.location) LIKE '%madhya pradesh%')")
                elif loc_clean in ("jaipur", "rajasthan"):
                    loc_clauses.append("(LOWER(j.location) LIKE '%jaipur%' OR LOWER(j.location) LIKE '%rj, in%' OR LOWER(j.location) LIKE '%rajasthan%')")
                elif loc_clean in ("coimbatore",):
                    loc_clauses.append("(LOWER(j.location) LIKE '%coimbatore%' OR LOWER(j.location) LIKE '%tn, in%')")
                elif loc_clean in ("chandigarh", "mohali", "punjab"):
                    loc_clauses.append("(LOWER(j.location) LIKE '%chandigarh%' OR LOWER(j.location) LIKE '%mohali%' OR LOWER(j.location) LIKE '%pb, in%' OR LOWER(j.location) LIKE '%punjab%')")
                elif loc_clean in ("bhubaneswar", "odisha"):
                    loc_clauses.append("(LOWER(j.location) LIKE '%bhubaneswar%' OR LOWER(j.location) LIKE '%or, in%' OR LOWER(j.location) LIKE '%odisha%')")
                else:
                    loc_clauses.append("LOWER(j.location) LIKE ?")
                    params.append(f"%{loc_clean}%")
            if loc_clauses:
                conditions.append(f"({' OR '.join(loc_clauses)})")

    if skill_tag:
        tag_items = [t.strip().lower() for t in skill_tag.split(",") if t.strip()]
        if tag_items:
            tag_clauses = []
            for st in tag_items:
                tag_clauses.append("(LOWER(j.title) LIKE ? OR LOWER(j.snippet) LIKE ?)")
                params.extend([f"%{st}%", f"%{st}%"])
            conditions.append(f"({' OR '.join(tag_clauses)})")

    if posted_within == "24h":
        conditions.append("datetime(j.created_at) >= datetime('now', '-1 day')")
    elif posted_within == "3d":
        conditions.append("datetime(j.created_at) >= datetime('now', '-3 days')")
    elif posted_within == "7d":
        conditions.append("datetime(j.created_at) >= datetime('now', '-7 days')")

    if site and site.strip().lower() != "all":
        site_items = [s.strip().lower() for s in site.split(",") if s.strip() and s.strip().lower() != "all"]
        if site_items:
            site_clauses = []
            for s_lower in site_items:
                if s_lower == "google":
                    site_clauses.append("(LOWER(j.site) LIKE '%google%' OR LOWER(j.job_url) LIKE '%greenhouse%' OR LOWER(j.job_url) LIKE '%lever%' OR LOWER(j.job_url) LIKE '%workday%' OR LOWER(j.job_url) LIKE '%careers%' OR LOWER(j.site) LIKE '%company%' OR LOWER(j.site) LIKE '%web%')")
                elif s_lower in ("instahyre", "remoteok", "remotive", "weworkremotely", "wwr", "arbeitnow"):
                    site_clauses.append("(LOWER(j.site) LIKE ? OR LOWER(j.job_url) LIKE ?)")
                    params.extend([f"%{s_lower}%", f"%{s_lower}%"])
                else:
                    site_clauses.append("LOWER(j.site) = ?")
                    params.append(s_lower)
            if site_clauses:
                conditions.append(f"({' OR '.join(site_clauses)})")

    if is_remote is True:
        conditions.append("j.is_remote = 1")

    # 3. Strict Experience Boundaries
    if experience and experience.strip().lower() != "all":
        exp_items = [e.strip().lower() for e in experience.split(",") if e.strip() and e.strip().lower() != "all"]
        if exp_items:
            exp_clauses = []
            for exp_val in exp_items:
                if exp_val in ("1_year", "junior"):
                    exp_clauses.append("""(
                        (j.exp_category = '1_year' OR (j.min_exp IS NOT NULL AND j.min_exp <= 2.0))
                        AND (j.min_exp IS NULL OR j.min_exp < 2.5)
                        AND (j.exp_category IS NULL OR j.exp_category NOT IN ('mid', 'senior'))
                        AND LOWER(j.snippet) NOT LIKE '%3-6%' AND LOWER(j.snippet) NOT LIKE '%3 - 6%' AND LOWER(j.snippet) NOT LIKE '%3 to 6%'
                        AND LOWER(j.snippet) NOT LIKE '%3+ years%' AND LOWER(j.snippet) NOT LIKE '%4+ years%' AND LOWER(j.snippet) NOT LIKE '%5+ years%'
                        AND LOWER(j.snippet) NOT LIKE '%8+ years%' AND LOWER(j.snippet) NOT LIKE '%5–15%'
                        AND LOWER(j.title) NOT LIKE '%senior%' AND LOWER(j.title) NOT LIKE '%lead%' AND LOWER(j.title) NOT LIKE '%staff%' AND LOWER(j.title) NOT LIKE '%principal%'
                        AND LOWER(j.title) NOT LIKE '% sde 2%' AND LOWER(j.title) NOT LIKE '% sde-2%' AND LOWER(j.title) NOT LIKE '% sde ii%'
                        AND LOWER(j.title) NOT LIKE '% sde 3%' AND LOWER(j.title) NOT LIKE '% sde-3%'
                        AND LOWER(j.job_url) NOT LIKE '%-3-to-%' AND LOWER(j.job_url) NOT LIKE '%-4-to-%' AND LOWER(j.job_url) NOT LIKE '%-5-to-%'
                        AND LOWER(j.job_url) NOT LIKE '%-6-to-%' AND LOWER(j.job_url) NOT LIKE '%-7-to-%' AND LOWER(j.job_url) NOT LIKE '%-8-to-%'
                        AND LOWER(j.job_url) NOT LIKE '%-9-to-%' AND LOWER(j.job_url) NOT LIKE '%-10-to-%'
                    )""")
                elif exp_val == "fresher":
                    exp_clauses.append("""(
                        (j.exp_category = 'fresher' OR j.min_exp = 0.0)
                        AND (j.min_exp IS NULL OR j.min_exp <= 1.0)
                        AND (j.exp_category IS NULL OR j.exp_category NOT IN ('mid', 'senior'))
                        AND LOWER(j.title) NOT LIKE '%senior%' AND LOWER(j.title) NOT LIKE '%lead%'
                        AND LOWER(j.snippet) NOT LIKE '%3-6%' AND LOWER(j.snippet) NOT LIKE '%2+%' AND LOWER(j.snippet) NOT LIKE '%3+%'
                        AND LOWER(j.job_url) NOT LIKE '%-2-to-%' AND LOWER(j.job_url) NOT LIKE '%-3-to-%' AND LOWER(j.job_url) NOT LIKE '%-4-to-%'
                        AND LOWER(j.job_url) NOT LIKE '%-5-to-%' AND LOWER(j.job_url) NOT LIKE '%-6-to-%' AND LOWER(j.job_url) NOT LIKE '%-7-to-%'
                    )""")
                elif exp_val == "mid":
                    exp_clauses.append("""(
                        j.exp_category = 'mid'
                        OR (j.min_exp >= 2.5 AND j.min_exp < 5.0)
                        OR LOWER(j.title) LIKE '%sde 2%' OR LOWER(j.title) LIKE '%sde-2%' OR LOWER(j.title) LIKE '%sde ii%'
                    )""")
                elif exp_val == "senior":
                    exp_clauses.append("""(
                        j.exp_category = 'senior'
                        OR j.min_exp >= 5.0
                        OR LOWER(j.title) LIKE '%senior%' OR LOWER(j.title) LIKE '%lead%' OR LOWER(j.title) LIKE '%staff%' OR LOWER(j.title) LIKE '%principal%' OR LOWER(j.title) LIKE '%architect%'
                    )""")
            if exp_clauses:
                conditions.append(f"({' OR '.join(exp_clauses)})")

    # Status filter (saved, applied, interviewing, offered)
    if status_filter and user_email:
        conditions.append("u.status = ?")
        params.append(status_filter)

    where_clause = " AND ".join(conditions)

    # Count total
    clean_email = (user_email or "").strip().lower()
    count_sql = f"""
        SELECT COUNT(*) FROM jobs j
        LEFT JOIN user_job_interactions u ON j.id = u.job_id AND LOWER(u.user_email) = ?
        WHERE {where_clause}
    """
    count_params = [clean_email] + params

    # Fetch rows
    fetch_sql = f"""
        SELECT j.*, u.status as user_status, u.notes as user_notes, u.applied_date as user_applied_date
        FROM jobs j
        LEFT JOIN user_job_interactions u ON j.id = u.job_id AND LOWER(u.user_email) = ?
        WHERE {where_clause}
        ORDER BY j.created_at DESC
        LIMIT ? OFFSET ?
    """
    fetch_params = [clean_email] + params + [limit, offset]

    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(count_sql, count_params)
        total_count = cursor.fetchone()[0]

        cursor.execute(fetch_sql, fetch_params)
        rows = cursor.fetchall()
    finally:
        conn.close()

    from .filter import get_job_experience_badge, matches_experience_filter
    jobs = []
    for row in rows:
        jd = dict(row)
        if experience and experience != "all" and not matches_experience_filter(jd, exp_filter=experience):
            continue
        jd["exp_badge"] = get_job_experience_badge(jd)
        jobs.append(jd)

    return jobs, total_count

@with_db_retry()
def toggle_user_job_status(user_email: str, job_id: str, new_status: str, db_path: Path = DB_PATH) -> str:
    """Toggles or sets job status ('saved', 'applied', etc.)."""
    clean_email = (user_email or "").strip().lower()
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM user_job_interactions WHERE LOWER(user_email) = ? AND job_id = ?", (clean_email, job_id))
        row = cursor.fetchone()

        current_status = row["status"] if row else None
        result_status = new_status

        if current_status == new_status:
            cursor.execute("DELETE FROM user_job_interactions WHERE LOWER(user_email) = ? AND job_id = ?", (clean_email, job_id))
            result_status = ""
        elif current_status:
            applied_date = datetime.now().strftime("%Y-%m-%d") if new_status == "applied" else ""
            cursor.execute("""
                UPDATE user_job_interactions 
                SET status = ?, applied_date = CASE WHEN ? != '' THEN ? ELSE applied_date END, updated_at = CURRENT_TIMESTAMP 
                WHERE LOWER(user_email) = ? AND job_id = ?
            """, (new_status, applied_date, applied_date, clean_email, job_id))
        else:
            applied_date = datetime.now().strftime("%Y-%m-%d") if new_status == "applied" else ""
            cursor.execute("""
                INSERT INTO user_job_interactions (user_email, job_id, status, applied_date) 
                VALUES (?, ?, ?, ?)
            """, (clean_email, job_id, new_status, applied_date))

        conn.commit()
        return result_status
    finally:
        conn.close()

@with_db_retry()
def get_tracker_items_for_user(user_email: str, db_path: Path = DB_PATH) -> List[Dict]:
    """Returns all tracked jobs with full job metadata and notes."""
    clean_email = (user_email or "").strip().lower()
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                u.id as interaction_id,
                u.user_email,
                u.job_id,
                u.status,
                COALESCE(u.notes, '') as notes,
                COALESCE(u.applied_date, '') as applied_date,
                u.updated_at,
                j.site,
                j.title,
                j.company,
                j.location,
                j.job_url,
                j.date_posted,
                j.job_type,
                j.salary,
                j.is_remote,
                j.snippet
            FROM user_job_interactions u
            JOIN jobs j ON u.job_id = j.id
            WHERE LOWER(u.user_email) = ?
            ORDER BY u.updated_at DESC
        """, (clean_email,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

@with_db_retry()
def update_tracker_stage(
    user_email: str, 
    job_id: str, 
    status: str, 
    notes: Optional[str] = None, 
    applied_date: Optional[str] = None, 
    db_path: Path = DB_PATH
) -> Dict:
    """Updates the pipeline stage and notes of a tracked job."""
    clean_email = (user_email or "").strip().lower()
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_job_interactions WHERE LOWER(user_email) = ? AND job_id = ?", (clean_email, job_id))
        existing = cursor.fetchone()

        cur_notes = existing["notes"] if existing and "notes" in existing.keys() and existing["notes"] else ""
        cur_date = existing["applied_date"] if existing and "applied_date" in existing.keys() and existing["applied_date"] else ""

        final_notes = notes if notes is not None else cur_notes
        final_date = applied_date if applied_date is not None else cur_date
        if status == "applied" and not final_date:
            final_date = datetime.now().strftime("%Y-%m-%d")

        cursor.execute("""
            INSERT INTO user_job_interactions (user_email, job_id, status, notes, applied_date, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_email, job_id) DO UPDATE SET
                status = excluded.status,
                notes = excluded.notes,
                applied_date = excluded.applied_date,
                updated_at = CURRENT_TIMESTAMP
        """, (clean_email, job_id, status, final_notes, final_date))

        conn.commit()
        return {"status": status, "notes": final_notes, "applied_date": final_date}
    finally:
        conn.close()

@with_db_retry()
def delete_tracker_item(user_email: str, job_id: str, db_path: Path = DB_PATH) -> bool:
    """Removes a job completely from the user's application tracker."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_job_interactions WHERE LOWER(user_email) = ? AND job_id = ?", (user_email.strip().lower(), job_id))
        conn.commit()
        return True
    finally:
        conn.close()

# User Management Functions

@with_db_retry()
def get_user_by_email(email: str, db_path: Path = DB_PATH) -> Optional[Dict]:
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email.strip().lower(),))
        row = cursor.fetchone()
        if row:
            u = dict(row)
            for json_field in ("skills", "email_roles", "email_languages", "email_locations"):
                try:
                    u[json_field] = json.loads(u.get(json_field) or "[]")
                except Exception:
                    u[json_field] = []

            if not u.get("email_locations"):
                u["email_locations"] = []

            if not u.get("email_roles"):
                tr = u.get("target_role") or "Software Engineer"
                u["email_roles"] = [tr, "Python Developer", "Backend Developer"] if "software" in tr.lower() else [tr]
            if not u.get("email_languages"):
                user_skills = u.get("skills") or []
                tech_kw = {"python", "sql", "javascript", "typescript", "java", "c++", "c#", "golang", "go", "react", "node", "nodejs", "vue", "angular", "django", "flask", "fastapi"}
                langs = [s for s in user_skills if str(s).lower() in tech_kw]
                u["email_languages"] = langs if langs else (user_skills[:4] if user_skills else ["Python", "SQL"])
            if not u.get("email_experience_filter"):
                u["email_experience_filter"] = "1_year"
            return u
        return None
    finally:
        conn.close()

def verify_user_credentials(email: str, password: str, db_path: Path = DB_PATH) -> Optional[Dict]:
    """Verifies user login credentials."""
    user = get_user_by_email(email, db_path)
    if not user:
        return None
    stored_pw = user.get("password") or "password123"
    if stored_pw == password or hashlib.sha256(password.encode()).hexdigest() == stored_pw:
        return user
    return None

@with_db_retry()
def upsert_user(user_data: dict, db_path: Path = DB_PATH) -> Dict:
    email = user_data.get("email", "").strip().lower()
    name = user_data.get("name", "").strip() or email.split("@")[0]
    password = user_data.get("password", "password123")
    target_role = user_data.get("target_role", "Software Engineer")
    experience_level = user_data.get("experience_level", "fresher")
    raw_skills = user_data.get("skills", [])
    skills = json.dumps(raw_skills)
    resume_text = user_data.get("resume_text", "")
    resume_filename = user_data.get("resume_filename", "")
    daily_email = 1 if user_data.get("daily_email", True) else 0
    email_time = user_data.get("email_time", "20:00")
    email_experience_filter = user_data.get("email_experience_filter", "1_year")

    email_roles = user_data.get("email_roles")
    if isinstance(email_roles, list) and email_roles:
        email_roles_str = json.dumps(email_roles)
    elif isinstance(email_roles, str) and email_roles.strip():
        email_roles_str = json.dumps([r.strip() for r in email_roles.split(",") if r.strip()])
    else:
        email_roles_str = json.dumps([target_role, "Python Developer", "Backend Developer"] if "software" in target_role.lower() else [target_role])

    email_languages = user_data.get("email_languages")
    if isinstance(email_languages, list) and email_languages:
        email_languages_str = json.dumps(email_languages)
    elif isinstance(email_languages, str) and email_languages.strip():
        email_languages_str = json.dumps([l.strip() for l in email_languages.split(",") if l.strip()])
    else:
        tech_kw = {"python", "sql", "javascript", "typescript", "java", "c++", "c#", "golang", "go", "react", "node", "nodejs", "vue", "angular", "django", "flask", "fastapi"}
        matched_l = [s for s in raw_skills if str(s).lower() in tech_kw]
        email_languages_str = json.dumps(matched_l if matched_l else (raw_skills[:4] if raw_skills else ["Python", "SQL"]))

    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (
                email, name, password, target_role, experience_level, skills, 
                resume_text, resume_filename, daily_email, email_time,
                email_experience_filter, email_roles, email_languages
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                name = excluded.name,
                password = CASE WHEN excluded.password != '' AND excluded.password != 'password123' THEN excluded.password ELSE users.password END,
                target_role = excluded.target_role,
                experience_level = excluded.experience_level,
                skills = excluded.skills,
                resume_text = CASE WHEN excluded.resume_text != '' THEN excluded.resume_text ELSE users.resume_text END,
                resume_filename = CASE WHEN excluded.resume_filename != '' THEN excluded.resume_filename ELSE users.resume_filename END,
                daily_email = excluded.daily_email,
                email_time = CASE WHEN excluded.email_time != '' THEN excluded.email_time ELSE users.email_time END,
                email_experience_filter = CASE WHEN excluded.email_experience_filter != '' THEN excluded.email_experience_filter ELSE users.email_experience_filter END,
                email_roles = CASE WHEN excluded.email_roles != '[]' THEN excluded.email_roles ELSE users.email_roles END,
                email_languages = CASE WHEN excluded.email_languages != '[]' THEN excluded.email_languages ELSE users.email_languages END
        """, (email, name, password, target_role, experience_level, skills, resume_text, resume_filename, daily_email, email_time, email_experience_filter, email_roles_str, email_languages_str))
        conn.commit()
    finally:
        conn.close()

    return get_user_by_email(email, db_path)

@with_db_retry()
def update_user_profile(user_data: dict, db_path: Path = DB_PATH) -> Optional[Dict]:
    """Updates user profile details directly."""
    email = user_data.get("email", "").strip().lower()
    if not email:
        return None

    name = user_data.get("name")
    target_role = user_data.get("target_role")
    experience_level = user_data.get("experience_level")
    skills = json.dumps(user_data.get("skills", [])) if "skills" in user_data else None
    email_time = user_data.get("email_time")
    daily_email = 1 if user_data.get("daily_email", True) else 0
    password = user_data.get("password")

    updates = []
    params = []
    if name is not None:
        updates.append("name = ?")
        params.append(name.strip())
    if target_role is not None:
        updates.append("target_role = ?")
        params.append(target_role.strip())
    if experience_level is not None:
        updates.append("experience_level = ?")
        params.append(experience_level.strip())
    if skills is not None:
        updates.append("skills = ?")
        params.append(skills)
    if email_time is not None:
        updates.append("email_time = ?")
        params.append(email_time.strip())
    if "daily_email" in user_data:
        updates.append("daily_email = ?")
        params.append(daily_email)
    if password and password.strip():
        updates.append("password = ?")
        params.append(password.strip())
    if "telegram_bot_token" in user_data:
        updates.append("telegram_bot_token = ?")
        params.append((user_data.get("telegram_bot_token") or "").strip())
    if "telegram_chat_id" in user_data:
        updates.append("telegram_chat_id = ?")
        params.append((user_data.get("telegram_chat_id") or "").strip())
    if "telegram_alerts" in user_data:
        updates.append("telegram_alerts = ?")
        params.append(1 if user_data.get("telegram_alerts") else 0)
    if "phone" in user_data:
        updates.append("phone = ?")
        params.append((user_data.get("phone") or "").strip())
    if "github_url" in user_data:
        updates.append("github_url = ?")
        params.append((user_data.get("github_url") or "").strip())
    if "linkedin_url" in user_data:
        updates.append("linkedin_url = ?")
        params.append((user_data.get("linkedin_url") or "").strip())
    if "portfolio_url" in user_data:
        updates.append("portfolio_url = ?")
        params.append((user_data.get("portfolio_url") or "").strip())
    if "years_experience" in user_data:
        updates.append("years_experience = ?")
        params.append((user_data.get("years_experience") or "0-1").strip())
    if "email_experience_filter" in user_data:
        updates.append("email_experience_filter = ?")
        params.append((user_data.get("email_experience_filter") or "1_year").strip())
    if "email_roles" in user_data:
        roles_val = user_data.get("email_roles")
        if isinstance(roles_val, list):
            roles_str = json.dumps(roles_val)
        elif isinstance(roles_val, str):
            r_list = [r.strip() for r in roles_val.split(",") if r.strip()] if "," in roles_val else ([roles_val.strip()] if roles_val.strip() else [])
            roles_str = json.dumps(r_list)
        else:
            roles_str = "[]"
        updates.append("email_roles = ?")
        params.append(roles_str)
    if "email_languages" in user_data:
        langs_val = user_data.get("email_languages")
        if isinstance(langs_val, list):
            langs_str = json.dumps(langs_val)
        elif isinstance(langs_val, str):
            l_list = [l.strip() for l in langs_val.split(",") if l.strip()] if "," in langs_val else ([langs_val.strip()] if langs_val.strip() else [])
            langs_str = json.dumps(l_list)
        else:
            langs_str = "[]"
        updates.append("email_languages = ?")
        params.append(langs_str)
    if "notice_period" in user_data:
        updates.append("notice_period = ?")
        params.append((user_data.get("notice_period") or "Immediate").strip())
    if "expected_ctc" in user_data:
        updates.append("expected_ctc = ?")
        params.append((user_data.get("expected_ctc") or "").strip())
    if "college_name" in user_data:
        updates.append("college_name = ?")
        params.append((user_data.get("college_name") or "").strip())
    if "email_locations" in user_data:
        locs_val = user_data.get("email_locations")
        if isinstance(locs_val, list):
            locs_str = json.dumps(locs_val)
        elif isinstance(locs_val, str):
            l_list = [l.strip() for l in locs_val.split(",") if l.strip()] if "," in locs_val else ([locs_val.strip()] if locs_val.strip() else [])
            locs_str = json.dumps(l_list)
        else:
            locs_str = "[]"
        updates.append("email_locations = ?")
        params.append(locs_str)
    if "current_city" in user_data:
        updates.append("current_city = ?")
        params.append((user_data.get("current_city") or "").strip())
    if "work_authorization" in user_data:
        updates.append("work_authorization = ?")
        params.append((user_data.get("work_authorization") or "Authorized to work (Citizen/PR)").strip())
    if "visa_sponsorship" in user_data:
        updates.append("visa_sponsorship = ?")
        params.append((user_data.get("visa_sponsorship") or "No").strip())
    if "summary_bio" in user_data:
        updates.append("summary_bio = ?")
        params.append((user_data.get("summary_bio") or "").strip())

    if updates:
        conn = get_connection(db_path)
        try:
            cursor = conn.cursor()
            sql = f"UPDATE users SET {', '.join(updates)} WHERE LOWER(email) = ?"
            params.append(email)
            cursor.execute(sql, params)
            conn.commit()
        finally:
            conn.close()

    return get_user_by_email(email, db_path)

@with_db_retry()
def get_system_setting(key: str, default: str = "", db_path: Path = DB_PATH) -> str:
    """Retrieves a persisted system setting from the database."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row and row[0] is not None else default
    except Exception:
        return default
    finally:
        conn.close()

def normalize_time_str(time_str: str) -> str:
    """Normalizes any time string (12h with AM/PM or 24h) to a strict HH:MM 24-hour string."""
    if not time_str:
        return "20:00"
    s = str(time_str).strip()
    from datetime import datetime
    for fmt in ("%I:%M %p", "%I:%M%p", "%H:%M", "%I %p"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%H:%M")
        except ValueError:
            pass
    parts = s.split(":")
    if len(parts) == 2:
        try:
            h = int(parts[0])
            m = int(parts[1][:2])
            if "pm" in s.lower() and h < 12:
                h += 12
            elif "am" in s.lower() and h == 12:
                h = 0
            return f"{h:02d}:{m:02d}"
        except Exception:
            pass
    return "20:00"

def format_time_to_12h(time_str: str) -> str:
    """Converts a 24-hour time string like '20:00' to a friendly 12-hour string like '08:00 PM'."""
    if not time_str:
        return "08:00 PM"
    s = str(time_str).strip()
    if "am" in s.lower() or "pm" in s.lower():
        return s
    try:
        from datetime import datetime
        dt = datetime.strptime(s, "%H:%M")
        return dt.strftime("%I:%M %p")
    except Exception:
        return s

@with_db_retry()
def set_system_setting(key: str, value: str, db_path: Path = DB_PATH) -> None:
    """Stores a persisted system setting in the database and syncs to email_credentials.json."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
    except Exception as e:
        logger.error(f"Error saving system setting {key}: {e}")
    finally:
        conn.close()

    try:
        cred_file = BASE_DIR / "email_credentials.json"
        creds = {}
        if cred_file.exists():
            try:
                with open(cred_file, "r", encoding="utf-8") as f:
                    creds = json.load(f) or {}
            except Exception:
                creds = {}
        creds[key] = str(value)
        with open(cred_file, "w", encoding="utf-8") as f:
            json.dump(creds, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not backup to email_credentials.json: {e}")

@with_db_retry()
def update_user_schedule(email: str, email_time: str, daily_email: bool = True, db_path: Path = DB_PATH) -> Optional[Dict]:
    """Updates user preferred daily digest time and toggle status, auto-upserting if new."""
    clean_email = (email or "").strip().lower()
    if not clean_email:
        return None

    clean_time = normalize_time_str(email_time)

    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE LOWER(email) = ?", (clean_email,))
        existing = cursor.fetchone()
        if not existing:
            name = clean_email.split("@")[0].capitalize()
            cursor.execute("""
                INSERT INTO users (email, name, email_time, daily_email, target_role, experience_level)
                VALUES (?, ?, ?, ?, 'Software Engineer', 'fresher')
            """, (clean_email, name, clean_time, 1 if daily_email else 0))
        else:
            cursor.execute("""
                UPDATE users 
                SET email_time = ?, daily_email = ?
                WHERE LOWER(email) = ?
            """, (clean_time, 1 if daily_email else 0, clean_email))
        conn.commit()
    finally:
        conn.close()

    return get_user_by_email(clean_email, db_path)

@with_db_retry()
def mark_user_digest_sent(email: str, date_str: str, time_str: str = "", db_path: Path = DB_PATH) -> None:
    """Records that today's digest was sent to this user, preventing duplicate delivery on subsequent ticks."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET last_digest_date = ?, last_digest_at = ?
            WHERE LOWER(email) = ?
        """, (date_str, time_str, (email or "").strip().lower()))
        conn.commit()
    except Exception as e:
        logger.error(f"Error marking digest sent for {email}: {e}")
    finally:
        conn.close()

@with_db_retry()
def reset_user_digest_tracking(email: str, db_path: Path = DB_PATH) -> None:
    """Clears last digest date so user can immediately receive a digest when changing schedule time to test."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET last_digest_date = '' WHERE LOWER(email) = ?", ((email or "").strip().lower(),))
        conn.commit()
    except Exception as e:
        logger.error(f"Error resetting digest tracking for {email}: {e}")
    finally:
        conn.close()
