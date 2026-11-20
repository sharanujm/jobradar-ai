import re
import io
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Dict, Tuple, Set
from pypdf import PdfReader

# Comprehensive Software Engineering & IT Skills taxonomy with regex patterns and display names
SKILL_PATTERNS = [
    # Languages & Core Runtimes
    (r"(?:\bc\+\+|\bcpp\b)", "C++"),
    (r"(?:\bc\#|\bcsharp\b)", "C#"),
    (r"(?:\b\.net\b|\bdotnet\b)", ".NET"),
    (r"\bpython\b|\bpy\b", "Python"),
    (r"\bjavascript\b|\bjs\b", "JavaScript"),
    (r"\btypescript\b|\bts\b", "TypeScript"),
    (r"\bjava\b(?!\s*script)", "Java"),
    (r"\bgolang\b", "Go"),
    (r"\brust\b", "Rust"),
    (r"\bkotlin\b", "Kotlin"),
    (r"\bswift\b", "Swift"),
    (r"\bphp\b", "PHP"),
    (r"\bruby\b(?!\s*on\s*rails)", "Ruby"),
    (r"\bruby\s+on\s+rails\b|\brails\b", "Ruby on Rails"),
    (r"\bdart\b", "Dart"),
    (r"\bscala\b", "Scala"),
    (r"\br\b(?=\s+programming|\s+scripting)", "R"),

    # Frontend Technologies
    (r"\breact\s+native\b", "React Native"),
    (r"\breact(?:\.js|js)?\b", "React"),
    (r"\bnext(?:\.js|js)?\b", "Next.js"),
    (r"\bvue(?:\.js|js)?\b", "Vue.js"),
    (r"\bangular(?:\.js|js)?\b", "Angular"),
    (r"\bredux\b", "Redux"),
    (r"\bsvelte\b", "Svelte"),
    (r"\btailwind(?:\s*css)?\b", "Tailwind CSS"),
    (r"\bbootstrap\b", "Bootstrap"),
    (r"\bhtml5?\b", "HTML"),
    (r"\bcss3?\b", "CSS"),
    (r"\bsass\b|\bscss\b", "Sass"),
    (r"\bwebpack\b", "Webpack"),
    (r"\bvite\b", "Vite"),
    (r"\bflutter\b", "Flutter"),

    # Backend Frameworks & Architectures
    (r"\bnode(?:\.js|js)?\b", "Node.js"),
    (r"\bexpress(?:\.js|js)?\b", "Express.js"),
    (r"\bnest(?:\.js|js)?\b", "NestJS"),
    (r"\b(?:fast\s*api|fastapi)\b", "FastAPI"),
    (r"\bdjango\b", "Django"),
    (r"\bflask\b", "Flask"),
    (r"\bspring\s*boot\b", "Spring Boot"),
    (r"\bspring\b(?!\s*boot)", "Spring"),
    (r"\blaravel\b", "Laravel"),
    (r"\basp\.net\b", "ASP.NET"),
    (r"\b(?:rest\s*apis?|restful\s*apis?)\b", "REST API"),
    (r"\bgraphql\b", "GraphQL"),
    (r"\bmicroservices?\b", "Microservices"),
    (r"\bgrpc\b", "gRPC"),
    (r"\bwebsockets?\b", "WebSockets"),

    # Databases & Caching
    (r"\b(?:postgre\s*sql|postgres)\b", "PostgreSQL"),
    (r"\bmysql\b", "MySQL"),
    (r"\b(?:mongo\s*db|mongo)\b", "MongoDB"),
    (r"\bredis\b", "Redis"),
    (r"\bsqlite\b", "SQLite"),
    (r"\bsql\b(?!\s*server)", "SQL"),
    (r"\bms\s*sql\b|\bsql\s*server\b", "SQL Server"),
    (r"\boracle(?:\s*db)?\b", "Oracle"),
    (r"\belasticsearch\b", "Elasticsearch"),
    (r"\bcassandra\b", "Cassandra"),
    (r"\bdynamodb\b", "DynamoDB"),
    (r"\bfirebase\b", "Firebase"),

    # Cloud, DevOps & Infrastructure
    (r"\baws\b|\bamazon\s+web\s+services\b", "AWS"),
    (r"\bazure\b", "Azure"),
    (r"\bgcp\b|\bgoogle\s+cloud\b", "GCP"),
    (r"\bdocker\b", "Docker"),
    (r"\bkubernetes\b|\bk8s\b", "Kubernetes"),
    (r"(?:\bci\/cd\b|\bcicd\b)", "CI/CD"),
    (r"\bjenkins\b", "Jenkins"),
    (r"\bgit\b", "Git"),
    (r"\bgithub\b", "GitHub"),
    (r"\bgitlab\b", "GitLab"),
    (r"\blinux\b|\bunix\b", "Linux"),
    (r"\bbash\b|\bshell\s+scripting\b", "Bash"),
    (r"\bterraform\b", "Terraform"),
    (r"\bkafka\b", "Kafka"),
    (r"\brabbitmq\b", "RabbitMQ"),
    (r"\bnginx\b", "Nginx"),

    # AI, ML & Data Science
    (r"\bmachine\s+learning\b|\bml\b", "Machine Learning"),
    (r"\bdeep\s+learning\b|\bdl\b", "Deep Learning"),
    (r"\b(?:nlp|natural\s+language\s+processing)\b", "NLP"),
    (r"\bllm\b|\blarge\s+language\s+models?\b", "LLM"),
    (r"\bgenerative\s+ai\b|\bgenai\b", "Generative AI"),
    (r"\brag\b|\bretrieval\s+augmented\b", "RAG"),
    (r"\blangchain\b", "LangChain"),
    (r"\bpytorch\b", "PyTorch"),
    (r"\btensorflow\b", "TensorFlow"),
    (r"\bpandas\b", "Pandas"),
    (r"\bnumpy\b", "NumPy"),
    (r"\bscikit[- ]?learn\b", "Scikit-Learn"),
    (r"\bopencv\b", "OpenCV"),
    (r"\bpower\s*bi\b", "Power BI"),
    (r"\btableau\b", "Tableau"),

    # Core Engineering, Testing & QA
    (r"\bdata\s+structures?\b|\bdsa\b", "Data Structures"),
    (r"\balgorithms?\b", "Algorithms"),
    (r"\bsystem\s+design\b", "System Design"),
    (r"\boop\b|\bobject[- ]oriented\b", "OOP"),
    (r"\bunit\s+testing\b", "Unit Testing"),
    (r"\bpytest\b", "PyTest"),
    (r"\bjunit\b", "JUnit"),
    (r"\bjest\b", "Jest"),
    (r"\bselenium\b", "Selenium"),
    (r"\bplaywright\b", "Playwright"),
    (r"\bpostman\b", "Postman"),
    (r"\bagile\b|\bscrum\b", "Agile"),
    (r"\bjira\b", "Jira")
]

ACTION_VERBS = [
    "developed", "designed", "engineered", "built", "architected", "optimized",
    "implemented", "deployed", "spearheaded", "accelerated", "reduced", "scaled",
    "integrated", "refactored", "automated", "created", "resolved", "maintained",
    "established", "orchestrated", "modernized", "delivered", "executed", "collaborated"
]

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract readable text from PDF bytes."""
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
        return text.strip()
    except Exception as e:
        return f"Error extracting PDF: {str(e)}"

def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract readable text from DOCX bytes using pure Python zipfile & XML."""
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            xml_content = z.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            texts = []
            for elem in tree.iter():
                if elem.tag.endswith("}t") and elem.text:
                    texts.append(elem.text)
            return " ".join(texts).strip()
    except Exception as e:
        return f"Error extracting DOCX: {str(e)}"

def extract_skills_from_text(text: str) -> List[str]:
    """Extract recognized technical skills from resume or job text."""
    if not text:
        return []
    
    found_skills = set()
    for pattern, name in SKILL_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            found_skills.add(name)

    return sorted(list(found_skills))

def calculate_job_match(
    job: dict, 
    user_skills: List[str], 
    user_experience: str = "fresher",
    target_role: str = ""
) -> Dict:
    """
    Computes match score, matched skills, missing skills, and fit badge.
    """
    job_title = (job.get("title") or "").lower()
    job_snippet = (job.get("snippet") or "").lower()
    job_text = f"{job_title} {job_snippet} {job.get('company', '')}"

    job_skills = set(extract_skills_from_text(job_text))
    user_skills_set = set(user_skills)
    matched = list(user_skills_set.intersection(job_skills))
    missing = list(job_skills.difference(user_skills_set))

    score = 52

    if job_skills:
        skill_ratio = len(matched) / max(len(job_skills), 1)
        score += int(skill_ratio * 36)
    else:
        if any(s.lower() in job_text for s in user_skills):
            score += 24

    if target_role:
        tr_words = [w.lower() for w in target_role.split() if len(w) > 3]
        if any(w in job_title for w in tr_words):
            score += 14

    is_senior_role = any(w in job_title for w in ["senior", "lead", "staff", "principal", "manager", "director"])
    is_fresher_role = any(w in job_title for w in ["junior", "fresher", "intern", "associate", "graduate", "sde 1", "entry"])

    if user_experience == "fresher":
        if is_fresher_role:
            score += 18
        elif is_senior_role:
            score -= 28
        else:
            score += 6
    elif user_experience == "senior":
        if is_senior_role:
            score += 16
        elif is_fresher_role:
            score -= 12

    final_score = max(38, min(98, score))

    if final_score >= 82:
        badge_class = "badge-emerald"
        label = "Super Match"
    elif final_score >= 70:
        badge_class = "badge-indigo"
        label = "Strong Match"
    elif final_score >= 55:
        badge_class = "badge-sky"
        label = "Good Match"
    else:
        badge_class = "badge-slate"
        label = "Related Role"

    return {
        "score": final_score,
        "label": label,
        "badge_class": badge_class,
        "matched_skills": matched[:6],
        "missing_skills": missing[:4],
        "job_skills": list(job_skills)
    }

def analyze_resume_ats(resume_text: str, user_exp: str = "fresher", target_role: str = "Software Engineer") -> Dict:
    """
    Performs full ATS (Applicant Tracking System) check and generates tailored optimizations.
    """
    if not resume_text or len(resume_text.strip()) < 20:
        # Fallback template analysis if empty
        resume_text = "Software Engineer candidate with Python, JavaScript, React, SQL, and Git experience."

    text_lower = resume_text.lower()
    skills = extract_skills_from_text(resume_text)
    
    # Check action verbs
    found_verbs = [v for v in ACTION_VERBS if v in text_lower]
    
    # Check metrics (% or numbers or metrics)
    has_metrics = bool(re.search(r"\b(?:\d+[%xX]|\d+\+?k|\d+\+)\b", text_lower))

    # Check key sections
    has_experience = any(k in text_lower for k in ["experience", "projects", "work history"])
    has_education = any(k in text_lower for k in ["education", "degree", "b.tech", "b.e", "bachelor", "mca", "university"])
    has_links = any(k in text_lower for k in ["github.com", "linkedin.com", "http", "www."])

    # ATS Score calculation
    score = 45
    score += min(len(skills) * 3, 25)
    score += min(len(found_verbs) * 2, 12)
    if has_metrics: score += 8
    if has_experience: score += 5
    if has_education: score += 5
    if has_links: score += 5

    ats_score = min(96, max(45, score))

    # Targeted suggestions
    suggestions = []
    if len(skills) < 6:
        suggestions.append({
            "type": "skills",
            "title": "Expand Core Technical Skills",
            "desc": "Add in-demand industry tools to your skills section, such as Docker, REST API, Postman, or AWS."
        })
    if not has_metrics:
        suggestions.append({
            "type": "metrics",
            "title": "Add Quantifiable Impact Metrics",
            "desc": "Recruiters love numbers! E.g. 'Improved database query speed by 35%' or 'Handled 5,000+ API requests daily'."
        })
    if len(found_verbs) < 4:
        suggestions.append({
            "type": "verbs",
            "title": "Use Stronger Action Verbs",
            "desc": "Begin bullet points with words like 'Architected', 'Spearheaded', 'Optimized', or 'Automated' instead of passive phrases."
        })
    if user_exp == "fresher":
        suggestions.append({
            "type": "projects",
            "title": "Highlight 2-3 Production-Grade Projects",
            "desc": "For freshers, include full-stack projects with live deployment URLs and clean GitHub code repositories."
        })
    else:
        suggestions.append({
            "type": "system_design",
            "title": "Emphasize Architecture & Scalability",
            "desc": "Mention system design choices, caching strategies (Redis), and cloud deployment pipelines (CI/CD)."
        })

    return {
        "ats_score": ats_score,
        "skills_detected": skills,
        "action_verbs_count": len(found_verbs),
        "has_metrics": has_metrics,
        "has_links": has_links,
        "suggestions": suggestions
    }

def enhance_resume_bullet(raw_bullet: str) -> Dict[str, str]:
    """Transforms a weak or plain bullet point into a high-impact, ATS-optimized version."""
    clean = raw_bullet.strip()
    if not clean:
        return {"original": "", "enhanced": ""}

    text_l = clean.lower()
    
    if "python" in text_l or "backend" in text_l or "api" in text_l:
        enhanced = f"Designed and deployed scalable RESTful APIs utilizing Python and modern frameworks, enhancing endpoint response times by 32% and ensuring robust database integration."
    elif "react" in text_l or "frontend" in text_l or "ui" in text_l:
        enhanced = f"Architected responsive, mobile-first user interfaces using React & modern state management, improving user engagement and cutting client-side load times by 28%."
    elif "sql" in text_l or "database" in text_l:
        enhanced = f"Engineered optimized SQL queries and indexing schemas across relational databases, reducing complex reporting latency by 45% across large datasets."
    elif "test" in text_l or "bug" in text_l or "qa" in text_l:
        enhanced = f"Authored comprehensive unit and integration test suites, elevating code test coverage to over 85% and significantly curtailing production regression defects."
    else:
        enhanced = f"Spearheaded the end-to-end development of core modules, applying modern software design principles and delivering milestones 2 weeks ahead of scheduled release."

    return {
        "original": clean,
        "enhanced": enhanced
    }
