import re
import html
from typing import Dict, List, Optional
from datetime import datetime

def generate_outreach_pitch(
    job: dict,
    user: dict,
    tone: str = "professional"
) -> Dict[str, str]:
    """
    Generates tailored Cover Letter, LinkedIn Message, and Cold Email Pitch
    customized specifically for the job and the candidate's skills and experience.
    """
    name = (user.get("name") or "Candidate").strip()
    user_skills = user.get("skills") or ["Python", "JavaScript", "SQL", "Git"]
    if isinstance(user_skills, str):
        try:
            import json
            user_skills = json.loads(user_skills)
        except Exception:
            user_skills = ["Software Development"]

    exp_level = user.get("experience_level") or "fresher"
    target_role = user.get("target_role") or "Software Engineer"

    job_title = (job.get("title") or "Software Engineer").strip()
    company = (job.get("company") or "your company").strip()
    location = (job.get("location") or "India").strip()
    snippet = job.get("snippet") or ""

    # Find common skills
    snippet_lower = snippet.lower()
    matched_skills = [s for s in user_skills if s.lower() in snippet_lower]
    if not matched_skills:
        matched_skills = user_skills[:3]
    skills_str = ", ".join(matched_skills[:4])
    primary_skill = matched_skills[0] if matched_skills else "Software Engineering"

    today_str = datetime.now().strftime("%B %d, %Y")

    # Experience phrasing
    if exp_level == "fresher":
        intro_exp = f"as an aspiring {target_role} with hands-on project experience in {skills_str}"
        value_prop = f"Throughout my academic and project work, I have focused on building scalable, clean software solutions using {skills_str}. I am eager to bring this solid foundation and quick learning ability to the engineering team at {company}."
    else:
        intro_exp = f"as a software developer specializing in {skills_str}"
        value_prop = f"With hands-on experience in building and deploying production-grade applications using {skills_str}, I am well-prepared to contribute immediately to {company}'s engineering objectives."

    # 1. Full Cover Letter
    cover_letter = f"""{today_str}

Hiring Team
{company}
{location}

Subject: Application for {job_title} Position - {name}

Dear Hiring Team at {company},

I am writing to express my strong interest in the {job_title} position at {company}. With a strong foundation in {skills_str} and a passionate focus on writing clean, efficient, and reliable code, I am excited about the opportunity to contribute to your engineering team.

{value_prop}

What particularly excites me about {company} is the opportunity to tackle meaningful engineering challenges. My technical background in {primary_skill} and modern development best practices has equipped me to solve problems systematically and collaborate effectively across modern tech stacks.

I would welcome the opportunity to discuss how my technical skills and enthusiasm align with {company}'s goals for this role. Thank you for your time and consideration.

Sincerely,

{name}
Email: {user.get('email', '')}
Role: {target_role}"""

    # 2. LinkedIn DM (strictly under 300 characters for connection notes)
    linkedin_msg = f"Hi Team! I noticed the {job_title} opening at {company}. As a developer skilled in {primary_skill} & {matched_skills[1] if len(matched_skills) > 1 else 'modern software'}, I'd love to connect and learn more about your engineering team's current work!"
    if len(linkedin_msg) > 295:
        linkedin_msg = f"Hi! I saw the {job_title} role at {company}. With background in {primary_skill}, I'd love to connect and discuss how my skills align with your team's goals!"

    # 3. Recruiter Cold Email
    cold_subject = f"Application: {job_title} | {name} ({primary_skill} & {skills_str.split(',')[0]})"
    cold_email_body = f"""Hi Hiring Team,

I recently came across the {job_title} role at {company} and wanted to reach out directly.

I am a {target_role} specializing in {skills_str}. Here is a quick summary of what I bring to the table:
• Core Proficiency: Strong hands-on experience with {skills_str}
• Fast Execution: Built and deployed end-to-end applications with clean architectures
• High Agility: Proven ability to rapidly adapt to new codebases and development workflows

I would love to share my portfolio and discuss how I can contribute to {company}'s product roadmap. Would you be open to a brief 10-minute introductory conversation this week?

Best regards,

{name}
{user.get('email', '')}
LinkedIn / GitHub Portfolio Attached"""

    # 4. Job-Specific Interview Cheat Sheet & Questions
    interview_cheat_sheet = generate_interview_prep(job_title, company, matched_skills, exp_level)

    return {
        "cover_letter": cover_letter.strip(),
        "linkedin_message": linkedin_msg.strip(),
        "cold_email_subject": cold_subject.strip(),
        "cold_email_body": cold_email_body.strip(),
        "interview_prep": interview_cheat_sheet
    }

def generate_interview_prep(job_title: str, company: str, skills: List[str], exp_level: str) -> Dict:
    """Generates technical questions and behavioral tips for interview preparation."""
    skills_lower = [s.lower() for s in skills]

    questions = []
    
    # Python questions
    if any("python" in s for s in skills_lower):
        questions.append({
            "topic": "Python Core",
            "q": "How does memory management and garbage collection work in Python, and what is the GIL?",
            "tip": "Explain reference counting + cyclic garbage collector. Mention how GIL impacts multithreading vs multiprocessing."
        })
        questions.append({
            "topic": "Python / Backend",
            "q": "What is the difference between synchronous and asynchronous programming in FastAPI/Flask?",
            "tip": "Explain async/await, event loops, and non-blocking I/O for high-concurrency REST endpoints."
        })

    # JavaScript / React questions
    if any("react" in s or "javascript" in s for s in skills_lower):
        questions.append({
            "topic": "React / Frontend",
            "q": "How does React's Virtual DOM and Reconciliation algorithm (Fiber) work?",
            "tip": "Explain diffing heuristics, keys in lists, and batching state updates."
        })
        questions.append({
            "topic": "JavaScript Core",
            "q": "Explain closures, promises, and the Event Loop (microtasks vs macrotasks).",
            "tip": "Draw the call stack, Web APIs, microtask queue (Promises), and macrotask queue (setTimeout)."
        })

    # SQL / Database questions
    if any("sql" in s or "postgres" in s or "mysql" in s for s in skills_lower):
        questions.append({
            "topic": "Databases & SQL",
            "q": "How do B-Tree indexes speed up queries, and when does an index cause a performance penalty?",
            "tip": "Indexes accelerate SELECT lookups from O(N) to O(log N) but introduce overhead on INSERT/UPDATE/DELETE."
        })

    # Default general engineering questions
    if len(questions) < 4:
        questions.append({
            "topic": "System Design / Architecture",
            "q": f"How would you design a scalable REST API for {job_title} requirements?",
            "tip": "Discuss pagination, rate limiting, caching (Redis), authentication (JWT), and proper HTTP status codes."
        })
        questions.append({
            "topic": "Data Structures & Algorithms",
            "q": "What data structure would you choose for fast lookups vs maintaining sorted order?",
            "tip": "HashMaps give O(1) average lookup; Balanced BSTs / B-Trees give O(log N) with ordered traversals."
        })

    behavioral = [
        {
            "q": f"Why do you want to work at {company} specifically?",
            "tip": f"Mention 1 specific product or feature {company} builds, and tie it to your technical passion in {skills[0] if skills else 'engineering'}."
        },
        {
            "q": "Tell me about a challenging bug you encountered in a project and how you solved it.",
            "tip": "Use the STAR format: Situation, Task, Action (systematic debugging steps), Result (performance improvement or resolution)."
        }
    ]

    coding_patterns = [
        "Two Pointers & Sliding Window (Substrings, Arrays)",
        "HashMap / Set Lookup (Frequencies, Pairs)",
        "Fast & Slow Pointers (Linked lists, Cycles)",
        "Binary Search (Search in sorted spaces, bounds)"
    ]

    return {
        "technical_questions": questions,
        "behavioral_questions": behavioral,
        "coding_patterns": coding_patterns
    }
