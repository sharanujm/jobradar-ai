# 📋 JobRadar AI — Comprehensive Project Technical Documentation

> **Project Name:** JobRadar AI (Automated Job Hunter & Career Acceleration Platform)  
> **Platform Version:** 2.0.0  
> **Repository Directory:** `d:\Job automation`  
> **Generated Date:** October 2026  
> **License:** Private / Educational & Professional Use  

---

## 📑 Table of Contents
1. [Executive Summary](#1-executive-summary)
2. [High-Level Architecture](#2-high-level-architecture)
3. [APIs & Communication Protocols Used](#3-apis--communication-protocols-used)
   - [3.1 External Aggregation & Scraping APIs](#31-external-aggregation--scraping-apis)
   - [3.2 Email & Delivery Protocols](#32-email--delivery-protocols)
   - [3.3 Internal REST API Endpoints](#33-internal-rest-api-endpoints)
4. [Complete Technology Stack](#4-complete-technology-stack)
   - [4.1 Backend Engine & Runtime](#41-backend-engine--runtime)
   - [4.2 Data Storage & Persistence](#42-data-storage--persistence)
   - [4.3 Web Scraping & Anti-Bot Technologies](#43-web-scraping--anti-bot-technologies)
   - [4.4 Resume Parsing & NLP Heuristics](#44-resume-parsing--nlp-heuristics)
   - [4.5 Frontend User Interface](#45-frontend-user-interface)
5. [Core Modules & Directory Structure](#5-core-modules--directory-structure)
6. [Database Schema & Data Models](#6-database-schema--data-models)
7. [Core Platform Features](#7-core-platform-features)
8. [Configuration & Environment Reference](#8-configuration--environment-reference)
9. [How to Run and Operate](#9-how-to-run-and-operate)

---

## 1. Executive Summary

**JobRadar AI** is an all-in-one automated job search, candidate matching, and career preparation platform. It solves the fatigue of manual job hunting by automatically aggregating freshly posted Software Engineering and Tech roles across top job boards, filtering out spam or irrelevant titles, scoring jobs against the candidate's actual resume skills, delivering a beautifully curated daily email digest, and offering an integrated suite of career acceleration tools:

- **Automated Multi-Board Scraper**: Crawls LinkedIn, Indeed, Glassdoor, Google Jobs, Naukri, and Internshala strictly for India-based and remote tech roles.
- **Pre-Digest Auto-Scraping Pipeline**: Automatically triggers fresh multi-platform scraping 30 minutes before your scheduled daily email dispatch.
- **100-Job Daily Email Digest**: Delivers 100 curated India jobs scored against your resume skills directly to your inbox.
- **Interactive Salary Studio & Offer Negotiator**: Benchmark Indian compensation across Bangalore, Hyderabad, Pune, and Remote; calculates monthly in-hand take-home under India's New Tax Regime (FY 2025-26); generates 3 high-conversion counter-offer email scripts.
- **Smart ATS Resume Matcher**: Parses PDF resumes, extracts 60+ technical skills, calculates match percentages, and computes ATS resume scores with actionable feedback.
- **Tailored Outreach Pitch Generator**: Formulates personalized Cover Letters, LinkedIn InMail messages, and Cold Outreach pitches for any role with 1 click.
- **Job Application Kanban Tracker**: Tracks applications from *Wishlist* ➡️ *Applied* ➡️ *Interviewing* ➡️ *Offer* / *Rejected*.
- **Tech Study Vault**: Curated interview prep guides (CS Fundamentals, System Design, DSA) and personal resource management.

---

## 2. High-Level Architecture

```
+---------------------------------------------------------------------------------------+
|                                     JOB PLATFORMS                                     |
|  [LinkedIn]   [Indeed]   [Glassdoor]   [Google Jobs]   [Naukri]   [Internshala]       |
+---------------------------------------------------------------------------------------+
                                           |
                                  (JobSpy & Requests)
                                           v
+---------------------------------------------------------------------------------------+
|                                SCRAPING & FILTER ENGINE                               |
|  - Title Keyword Whitelist & Blacklist Filtering (src/filter.py)                     |
|  - Deduplication via URL & Title/Company Hash                                         |
|  - Normalization (Location, Experience Tier, Source)                                  |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                               SQLite DATABASE (jobs.db)                               |
|  - jobs: Normalized job repository                                                    |
|  - users: User profiles, target roles, experience tier, skills                        |
|  - user_jobs: Delivery tracking & saved status                                        |
|  - application_tracker: Application pipeline status                                   |
|  - study_vault_resources: Prep notes, links, and study materials                      |
+---------------------------------------------------------------------------------------+
           ^                                                               ^
           |                                                               |
(REST API Endpoints)                                             (Background Scheduler)
           |                                                               |
+------------------------+                                      +------------------------+
|   FASTAPI WEB SERVER   |                                      |  SCHEDULED DISPATCHER  |
|  Port 8765             |                                      |  Async 20s poller /    |
|  (server.py)           |                                      |  Cron daily trigger    |
+------------------------+                                      +------------------------+
           |                                                               |
           v                                                               v
+------------------------+                                      +------------------------+
|  SINGLE-PAGE APP (UI)  |                                      |   GMAIL SMTP ENGINE    |
|  - Dashboard           |                                      |   Port 465 SSL         |
|  - ATS Resume Checker  |                                      |   Curated HTML Digest  |
|  - Pitch Generator     |                                      +------------------------+
|  - Application Kanban  |                                                 |
|  - Study Vault         |                                                 v
+------------------------+                                      +------------------------+
                                                                |      USER'S INBOX      |
                                                                +------------------------+
```

---

## 3. APIs & Communication Protocols Used

### 3.1 External Aggregation & Scraping APIs
The platform aggregates listings without requiring expensive commercial API keys by leveraging modern headless and reverse-engineered API scraping protocols:

| Service / Interface | Protocol / Tool | Purpose |
| :--- | :--- | :--- |
| **LinkedIn Jobs** | `python-jobspy` (HTTP / TLS Client) | Scrapes active Software Engineer openings and direct apply links. |
| **Indeed Jobs** | `python-jobspy` with `curl_cffi` | Bypasses Cloudflare & bot protection to extract active job cards. |
| **Glassdoor** | `python-jobspy` | Extracts company reviews, salaries, and job openings. |
| **Google Jobs** | `python-jobspy` (Google Search SERP parser) | Aggregates company career site postings indexed across Google. |
| **Naukri.com** | `python-jobspy` | India-centric IT job listings. |
| **Internshala** | Custom `requests` + `BeautifulSoup4` scraper | Crawls fresh software engineering graduate roles and internships in India and remote. |

### 3.2 Email & Delivery Protocols
| Service / Protocol | Library / Standard | Details |
| :--- | :--- | :--- |
| **Gmail SMTP** | `smtplib.SMTP_SSL` | Secure SSL connection over port 465 to `smtp.gmail.com`. |
| **Google App Passwords** | OAuth-alternative App Password | Zero-cost 16-character authentication bypasses 2FA securely. |
| **MIME Multipart Protocol** | `email.mime.multipart`, `email.mime.text` | Constructs dual-payload emails: rich HTML design + plain text fallback. |

### 3.3 Internal REST API Endpoints (`server.py`)
The system provides a full-featured async REST API:

| Endpoint | Method | Description |
| :--- | :---: | :--- |
| `/` | `GET` | Serves the single-page application dashboard (`static/index.html`). |
| `/api/auth/login` | `POST` | Authenticates existing users or auto-onboards new users. |
| `/api/auth/signup` | `POST` | Registers a new profile with roles, skills, and alert preferences. |
| `/api/profile` | `GET` | Fetches user profile settings, saved skills, and schedules. |
| `/api/profile/update` | `POST` | Updates target role, experience level, skills list, and alert time. |
| `/api/jobs` | `GET` | Retrieves paginated jobs with filters (search, platform, experience, status). |
| `/api/stats` | `GET` | Aggregates live system metrics (total jobs, fresh matches, platform distribution). |
| `/api/scan` | `POST` | Triggers immediate multi-source scraping job across all platforms. |
| `/api/scan/status` | `GET` | Returns current background scraping status (`running`, `idle`, timestamp). |
| `/api/send-digest` | `POST` | Force-triggers an immediate personalized email digest to the user's inbox. |
| `/api/resume/upload` | `POST` | Parses candidate PDF resume, extracts skills, and calculates match rankings. |
| `/api/resume/ats-analyze` | `POST` | Computes comprehensive ATS score, action-verb usage, and bullet enhancements. |
| `/api/pitch/generate` | `POST` | Generates tailored Cover Letter, LinkedIn InMail, and Cold Email. |
| `/api/tracker` | `GET` | Retrieves all tracked job applications grouped by recruitment stage. |
| `/api/tracker/update` | `POST` | Moves jobs between stages (*Wishlist*, *Applied*, *Interviewing*, *Offer*, *Rejected*). |
| `/api/tracker/delete` | `POST` | Removes an item from the application tracker. |
| `/api/resources` | `GET` | Fetches curated interview guides and user-uploaded study notes. |
| `/api/resources/upload` | `POST` | Uploads PDF study guides or revision cheat-sheets. |
| `/api/resources/add-link` | `POST` | Adds external learning links or custom Markdown notes. |
| `/api/resources/toggle-status`| `POST` | Toggles revision completion checklist for study resources. |
| `/api/resources/{id}` | `DELETE` | Deletes a study resource from the database. |
| `/api/resources/file/{name}` | `GET` | Streams stored PDF study guides directly to the browser. |

---

## 4. Complete Technology Stack

### 4.1 Backend Engine & Runtime
- **Python 3.12**: Core programming language.
- **FastAPI (0.110+)**: High-performance asynchronous REST API framework.
- **Uvicorn (0.28+)**: Production-grade ASGI web server running on port `8765`.
- **Pydantic (2.6+)**: Data validation, schema definition, and request serialization.
- **Starlette**: Underpins FastAPI with static file hosting, CORS middleware, and streaming responses.
- **Asyncio**: Non-blocking asynchronous task orchestration and background scheduler worker.

### 4.2 Data Storage & Persistence
- **SQLite 3**: Embedded relational database (`jobs.db`) storing jobs, user accounts, application kanban cards, and study resources.
- **JSON Serialization**: Flexible storage for skills taxonomy, tags, and dynamic user configurations.
- **YAML (`pyyaml`)**: Declarative configuration management (`config.yaml`).
- **Python-Dotenv**: Safe isolation of SMTP credentials in local `.env`.

### 4.3 Web Scraping & Anti-Bot Technologies
- **Python-JobSpy (1.2+)**: Multi-board aggregator for LinkedIn, Indeed, Glassdoor, and Google Jobs.
- **BeautifulSoup4 (4.12+)**: HTML DOM parser used in custom scrapers (Internshala).
- **Requests (2.31+)**: HTTP client with custom User-Agent rotations.
- **curl_cffi (0.7+)**: High-performance HTTP client simulating browser TLS client fingerprints.
- **Pandas (2.1+)**: Tabular job data cleaning, deduplication, and transformation.

### 4.4 Resume Parsing & NLP Heuristics
- **pypdf (4.2+)**: High-fidelity text extraction from candidate PDF resumes.
- **Regex NLP Taxonomy**: Custom pattern matcher categorizing 60+ technical skills across 7 engineering domains:
  - *Languages*: Python, Java, JavaScript, TypeScript, C++, Go, Rust, SQL, etc.
  - *Frontend*: React, Next.js, Vue, Angular, Tailwind, HTML5, CSS3, etc.
  - *Backend*: FastAPI, Django, Flask, Node.js, Express, Spring Boot, etc.
  - *Databases*: PostgreSQL, MySQL, MongoDB, Redis, SQLite, etc.
  - *Cloud / DevOps*: AWS, Azure, GCP, Docker, Kubernetes, CI/CD, Git, Linux.
  - *AI / ML*: Machine Learning, PyTorch, TensorFlow, NLP, LLMs, RAG, Pandas.
  - *CS Fundamentals*: OOP, DSA, System Design, Operating Systems, DBMS, Networks.
- **ATS Scoring Engine**: Algorithmic scoring evaluating section structure, action-verb density, quantifiable metrics, and skill keyword density.

### 4.5 Frontend User Interface
- **HTML5**: Semantic single-page layout.
- **Vanilla CSS3**:
  - Custom Dark Mode Theme (`#0b0f19` and `#111827`) with glassmorphic cards (`rgba(17, 24, 39, 0.7)`).
  - CSS Grid & Flexbox responsive layouts.
  - Smooth micro-interactions, gradient badges, and modal overlays.
- **Vanilla JavaScript (ES6+)**:
  - Native `fetch()` API asynchronous communication.
  - Tab routing and dynamic reactive state management.
  - Drag-and-drop file upload handling.
  - Real-time search, multi-filter dropdowns, and toast alerts.
- **Typography & Icons**:
  - Google Fonts: *Inter* and *Plus Jakarta Sans*.
  - Font Awesome 6: Crisp vector iconography.

---

## 5. Core Modules & Directory Structure

```
d:\Job automation\
├── .env                          # SMTP credentials & sender configuration
├── .env.example                  # Template for environment variables
├── config.yaml                   # Scraping roles, locations, blacklist keywords
├── requirements.txt              # Python package dependencies
├── server.py                     # Main FastAPI server & REST API endpoints
├── run_now.py                    # Standalone CLI script to trigger on-demand scrape
├── send_digest_now.py            # Standalone CLI script to force email dispatch
├── test_email.py                 # Quick SMTP validation script
├── jobs.db                       # SQLite database file
├── latest_digest.html            # Rendered HTML preview of last generated email
│
├── src/                          # Backend business logic modules
│   ├── config_loader.py          # Loads YAML and .env configurations
│   ├── database.py               # SQLite schema initialization & database queries
│   ├── scraper.py                # JobSpy orchestrator across platforms
│   ├── internshala_scraper.py    # Custom Internshala scraper module
│   ├── filter.py                 # Keyword matching, title blacklist & deduplication
│   ├── resume_matcher.py         # PDF parser, skill extractor & ATS scorer
│   ├── pitch_generator.py        # Cover letter & cold outreach generator
│   ├── email_builder.py          # HTML email template renderer
│   ├── email_sender.py           # Gmail SSL SMTP dispatcher
│   └── study_vault.py            # Interview prep guides & resource repository
│
├── static/                       # Frontend assets
│   ├── index.html                # Single-page application UI
│   ├── styles.css                # Glassmorphic dark-mode design system
│   ├── app.js                    # SPA application state and client API logic
│   └── project_documentation.html # Interactive web documentation page
│
└── data/resources/               # Uploaded candidate PDF guides & study materials
```

---

## 6. Database Schema & Data Models

### 1. `jobs` Table
Stores unique normalized job opportunities aggregated across the internet:
- `id` (TEXT PRIMARY KEY): MD5 hash of `url` or `company + title`.
- `title` (TEXT): Job title.
- `company` (TEXT): Company name.
- `location` (TEXT): Job location (e.g. Bangalore, Remote, India).
- `site` (TEXT): Platform source (`linkedin`, `indeed`, `glassdoor`, `google`, `naukri`, `internshala`).
- `job_url` (TEXT): Direct URL for "Apply Now".
- `date_posted` (TEXT): Date published on the job board.
- `snippet` (TEXT): Job summary / description snippet.
- `experience_level` (TEXT): Categorized tier (`fresher`, `mid`, `senior`).
- `scraped_at` (TEXT): Timestamp when discovered.
- `emailed` (INTEGER): Global emailed flag (0 or 1).

### 2. `users` Table
Multi-user accounts supporting individualized preferences:
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `email` (TEXT UNIQUE): Primary email address for alerts.
- `name` (TEXT): User's display name.
- `password_hash` (TEXT): Secure credential string.
- `target_role` (TEXT): Preferred job title (e.g., Software Engineer).
- `experience_level` (TEXT): Experience tier (`fresher`, `mid`, `senior`).
- `skills` (TEXT): JSON array of candidate's technical skills.
- `daily_email` (BOOLEAN): Master toggle for automated email delivery.
- `email_time` (TEXT): Scheduled trigger time (e.g. `20:00`).

### 3. `user_jobs` Table
Tracks user-specific interactions per job:
- `user_email` (TEXT)
- `job_id` (TEXT)
- `status` (TEXT): `saved`, `applied`, `hidden`, or `emailed`.
- `notes` (TEXT): Candidate's personal interview notes.
- `updated_at` (TEXT): Timestamp of state update.

### 4. `application_tracker` Table
Powers the recruitment Kanban pipeline:
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `user_email` (TEXT)
- `job_id` (TEXT)
- `stage` (TEXT): `wishlist` | `applied` | `interviewing` | `offer` | `rejected`
- `applied_date` (TEXT): Date submitted.
- `notes` (TEXT): Interview notes, salary discussions, recruiter contacts.

### 5. `study_vault_resources` Table
Houses interview prep guides and study checklists:
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `user_email` (TEXT)
- `title` (TEXT): Guide title (e.g., *Top 100 SDE Technical Questions*).
- `category` (TEXT): *CS Fundamentals*, *System Design*, *DSA*, *Web Dev*.
- `resource_type` (TEXT): `guide` | `link` | `file` | `note`
- `content_text` (TEXT): Full markdown guide text.
- `is_completed` (BOOLEAN): Checklist tracking status.

---

## 7. Core Platform Features

### 1. Multi-Board Job Aggregation & Filtering
- Scrapes listings for configurable target roles and locations.
- Automatically excludes irrelevant listings (Sales, HR, Senior Directors, Civil, etc.) using regex keyword blacklists.
- Normalizes job attributes into a clean, searchable database.

### 2. Tailored Email Digest Engine
- Builds responsive, modern HTML email alerts with direct "Apply Now" buttons.
- Deduplicates so users never receive the same job twice.
- Background worker checks the system every 20 seconds and dispatches digests at each user's designated local time.

### 3. Smart ATS Resume Matcher & Feedback
- Instant PDF drag-and-drop text extraction.
- Scans candidate skills against active job descriptions.
- Calculates an ATS Score (0–100%) and highlights:
  - Identified skills vs Missing job-critical skills.
  - Action-verb strength.
  - Bullet point enhancement suggestions.

### 4. 1-Click Outreach Pitch Generator
- Creates tailored application materials for any selected job:
  - **Full Cover Letter**: Personalized with candidate's top matching skills.
  - **LinkedIn InMail Message**: High-conversion 100-word networking note.
  - **Cold Outreach Email**: Direct message for hiring managers with a compelling call-to-action.

### 5. Job Application Kanban Tracker
- Interactive pipeline board to track application progress:
  - **Wishlist** ➡️ **Applied** ➡️ **Interviewing** ➡️ **Offer** ➡️ **Rejected**.
- Enables candidates to maintain accountability and log notes throughout the interview lifecycle.

### 6. Tech Study Vault
- Preloaded revision guides:
  - **CS Fundamentals**: OOP, DBMS, OS, Computer Networks.
  - **System Design Principles**: Scalability, Caching, Load Balancing, Microservices.
  - **DSA Cheatsheet**: Complexity cheat-sheets and core pattern guides.
- Ability to upload custom PDF revision notes or bookmark important technical articles.

---

## 8. Configuration & Environment Reference

### 8.1 Environment Variables (`.env`)
```env
# Google Account credentials for sending emails
SENDER_EMAIL=your_email@gmail.com
SENDER_APP_PASSWORD=abcdefghijklmnop   # 16-character Google App Password

# Default recipient for automated notifications
RECIPIENT_EMAIL=your_email@gmail.com
```

### 8.2 YAML Configuration (`config.yaml`)
```yaml
search:
  roles:
    - Software Engineer
    - Software Developer
    - Full Stack Developer
    - Backend Developer
    - Frontend Developer
    - Python Developer
  locations:
    - India
    - Bangalore, Karnataka, India
    - Hyderabad, Telangana, India
    - Remote
  platforms:
    - linkedin
    - indeed
    - glassdoor
    - google
    - naukri
    - internshala
  country_indeed: india
  results_per_platform: 15
  hours_old: 48

filtering:
  required_title_keywords:
    - Software
    - Developer
    - Engineer
    - Full Stack
    - Backend
    - Frontend
    - Python
    - SDE
  blacklist_keywords:
    - Senior Director
    - Vice President
    - Sales Executive
    - Human Resources
    - Civil Engineer
    - Mechanical Engineer

schedule:
  time: "20:00"
  timezone: "Asia/Kolkata"

digest:
  max_jobs_in_email: 50
  email_subject: "🚀 Daily Job Alert: {count} New Matching Opportunities ({date})"
  generate_html_preview: true
  preview_file: "latest_digest.html"
```

---

## 9. How to Run and Operate

### 1. Launch the Web Application
```powershell
# In project root: d:\Job automation
.\venv\Scripts\python.exe server.py
```
- Open browser at: **`http://127.0.0.1:8765`**

### 2. Run Scraping On-Demand (CLI)
```powershell
.\venv\Scripts\python.exe run_now.py
```

### 3. Send Daily Digest Right Now (CLI)
```powershell
.\venv\Scripts\python.exe send_digest_now.py
```

### 4. Test Email SMTP Connection (CLI)
```powershell
.\venv\Scripts\python.exe test_email.py
```

---

*Documentation compiled for JobRadar AI Platform.*
