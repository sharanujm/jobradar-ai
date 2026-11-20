import re
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple

def clean_text(text: Any) -> str:
    """Strip whitespace and collapse multiple spaces, handling None, NaN, and floats safely."""
    if text is None:
        return ""
    try:
        if pd.isna(text):
            return ""
    except Exception:
        pass
    text_str = str(text).strip()
    if text_str.lower() in ("nan", "none", "<na>"):
        return ""
    return re.sub(r"\s+", " ", text_str).strip()

def format_salary(row: dict) -> str:
    """Format salary information into a clean readable string."""
    min_amt = row.get("min_amount")
    max_amt = row.get("max_amount")
    curr = clean_text(row.get("currency"))
    interval = clean_text(row.get("interval"))

    try:
        if min_amt is not None and not pd.isna(min_amt) and max_amt is not None and not pd.isna(max_amt):
            return f"{curr} {int(float(min_amt)):,} - {int(float(max_amt)):,} / {interval}".strip()
        elif min_amt is not None and not pd.isna(min_amt):
            return f"{curr} {int(float(min_amt)):,}+ / {interval}".strip()
        elif max_amt is not None and not pd.isna(max_amt):
            return f"Up to {curr} {int(float(max_amt)):,} / {interval}".strip()
    except Exception:
        pass
    return ""

import unicodedata

# Comprehensive geographic dictionaries for India filtering
INDIAN_CITIES_AND_STATES = {
    # Metropolitan & Tech Hub Cities
    "bengaluru", "bangalore", "hyderabad", "chennai", "pune", "mumbai", "delhi", "new delhi", 
    "noida", "gurgaon", "gurugram", "kolkata", "calcutta", "ahmedabad", "kochi", "cochin", 
    "trivandrum", "thiruvananthapuram", "indore", "jaipur", "coimbatore", "chandigarh", 
    "mohali", "mysore", "mysuru", "nagpur", "bhubaneswar", "visakhapatnam", "vizag", 
    "surat", "vadodara", "bhopal", "patna", "lucknow", "kanpur", "thane", "navi mumbai", 
    "vellore", "guwahati", "trichy", "thanjavur", "madurai", "kozhikode", "mangalore", 
    "mangaluru", "salem", "tirupati", "vijayawada", "warangal", "guntur", "dehradun",
    "faridabad", "ghaziabad", "ncr", "greater noida", "hubli", "dharwad", "belgaum",
    # States & Union Territories
    "karnataka", "telangana", "maharashtra", "tamil nadu", "tamilnadu", "andhra pradesh", 
    "uttar pradesh", "haryana", "gujarat", "kerala", "west bengal", "rajasthan", 
    "madhya pradesh", "punjab", "odisha", "orissa", "bihar", "assam", "goa", "jharkhand", 
    "uttarakhand", "himachal pradesh"
}

INDIAN_STATE_CODES = {
    "ka", "ts", "mh", "tn", "dl", "up", "hr", "kl", "gj", "wb", "ap", "rj", "mp", "pb", "or", "ch", "ga"
}

FOREIGN_INDICATORS = {
    "united states", "usa", "u.s.", "u.s.a", "canada", "united kingdom", "scotland", "england",
    "australia", "germany", "deutschland", "france", "singapore", "united arab emirates", "uae",
    "dubai", "netherlands", "ireland", "switzerland", "sweden", "spain", "italy", "brazil",
    "brasil", "poland", "japan", "mexico", "philippines", "indonesia", "malaysia", "vietnam",
    "south africa", "egypt", "nigeria", "portugal", "new zealand", "russia", "china", "argentina",
    "colombia", "chile", "peru", "ecuador", "bolivia", "tunisia", "turkey", "turkiye",
    "recife", "salvador", "sao paulo", "rio de janeiro", "toronto", "vancouver", "montreal",
    "london", "dublin", "berlin", "munich", "paris", "amsterdam", "sydney", "melbourne",
    "seattle", "austin", "chicago", "new york", "san francisco", "los angeles", "boston",
    "california", "texas", "florida", "washington", "colorado", "ohio", "jakarta", "bangkok",
    "auvergne-rhone-alpes", "grenoble", "lisbon", "porto", "casablanca", "salt lake city",
    "nashville", "aurora", "columbus", "medellin", "la paz", "guayas", "tunis", "curitiba",
    "cologno monzese", "da nang", "finland", "helsinki", "belgium", "brussels", "norway", "oslo",
    "denmark", "copenhagen", "austria", "vienna", "warsaw", "czech", "prague", "hungary",
    "budapest", "romania", "bucharest", "israel", "tel aviv", "taiwan", "hong kong", "korea"
}

def is_india_location(location: Any, site: Any = "") -> bool:
    """
    Strictly verifies whether a job location is within India or Indian Remote.
    Disqualifies any foreign country, foreign city, or international remote position.
    """
    if not location:
        site_clean = clean_text(site).lower()
        # Default Indian job boards to True if location unstated
        return site_clean in ("internshala", "naukri")

    loc_str = str(location).strip()
    # Normalize unicode diacritics (e.g. Hyderābād -> Hyderabad, Thanjāvūr -> Thanjavur)
    loc_clean = unicodedata.normalize("NFKD", loc_str).encode("ascii", "ignore").decode("utf-8").lower().strip()

    if not loc_clean:
        return False

    # 1. Any foreign indicator is an immediate disqualifier
    for f in FOREIGN_INDICATORS:
        if f in loc_clean:
            return False

    # Check US state codes like ', ca' or ', tx'
    if re.search(r',\s*(?:ca|ny|tx|wa|fl|il|pa|oh|ga|nc|mi|nj|va|ma|az|co|tn|mo|md|wi|mn|or)\b', loc_clean):
        return False

    # 2. Positive India indicators
    if "india" in loc_clean:
        return True

    # Check ', in' or 'remote, in' or '(in)' or 'in /'
    if re.search(r'\b(?:in|ind)\b', loc_clean) and (
        ", in" in loc_clean or "remote, in" in loc_clean or "/ in" in loc_clean or 
        "(in)" in loc_clean or ",in" in loc_clean or loc_clean.endswith(" in") or loc_clean == "in"
    ):
        return True

    # 3. Check Indian cities and states
    for ind in INDIAN_CITIES_AND_STATES:
        if ind in loc_clean:
            return True

    # 4. Check state codes like 'KA, IN' or ', KA'
    for sc in INDIAN_STATE_CODES:
        if re.search(r'\b' + sc + r'\b', loc_clean) and (", in" in loc_clean or "in" in loc_clean or "," in loc_clean):
            return True

    # 5. Platforms like Internshala / Naukri with Work from home / Remote
    site_clean = clean_text(site).lower()
    if site_clean in ("internshala", "naukri") and ("work from home" in loc_clean or "remote" in loc_clean or "india" in loc_clean):
        return True

    return False

def is_matching_job(job: dict, config: dict) -> bool:
    """
    Check if a job matches user keywords, location requirements, and passes blacklist filters.
    """
    filtering_cfg = config.get("filtering", {})
    required_keywords = filtering_cfg.get("required_title_keywords", [])
    blacklist = filtering_cfg.get("blacklist_keywords", [])
    only_india = filtering_cfg.get("only_india", True)

    title = clean_text(job.get("title")).lower()
    snippet = clean_text(job.get("snippet")).lower()
    location = clean_text(job.get("location"))
    site = clean_text(job.get("site"))

    if not title:
        return False

    # 0. Check India-only restriction
    if only_india and not is_india_location(location, site):
        return False

    # 1. Check blacklist
    for bad_word in blacklist:
        bw = bad_word.lower().strip()
        if bw and bw in title:
            return False

    # 2. Check required keywords in title
    if required_keywords:
        has_required = any(req.lower().strip() in title for req in required_keywords if req.strip())
        if not has_required:
            # Check snippet as fallback
            has_in_desc = any(req.lower().strip() in snippet for req in required_keywords if req.strip())
            if not has_in_desc:
                return False

    return True

def clean_and_normalize_job(raw_job: dict) -> dict:
    """Normalizes job fields from JobSpy or custom sources into a standard dict."""
    title = clean_text(raw_job.get("title")) or "Software Engineer"
    company = clean_text(raw_job.get("company")) or "Tech Company"
    location = clean_text(raw_job.get("location")) or "India / Remote"
    
    # Direct apply url or job url
    raw_direct = clean_text(raw_job.get("job_url_direct"))
    raw_url = clean_text(raw_job.get("job_url"))
    job_url = raw_direct if raw_direct else (raw_url if raw_url else "#")
    
    site = clean_text(raw_job.get("site")) or "Web"
    site = site.capitalize()
    
    # Snippet
    raw_desc = raw_job.get("description")
    snippet_str = ""
    if raw_desc is not None:
        try:
            if not pd.isna(raw_desc):
                s = str(raw_desc).strip()
                snippet_str = s[:597].rstrip() + "..." if len(s) > 600 else s
        except Exception:
            pass
    snippet = clean_text(snippet_str)

    # Date posted
    date_val = raw_job.get("date_posted")
    date_posted = clean_text(date_val) if date_val is not None and not (isinstance(date_val, float) and pd.isna(date_val)) else "Recently"

    # Salary
    salary = format_salary(raw_job) or clean_text(raw_job.get("salary"))

    # Remote indicator
    is_remote = bool(raw_job.get("is_remote")) or "remote" in location.lower() or "remote" in title.lower()

    # Pre-calculate experience bounds
    min_exp, max_exp, exp_category = parse_job_experience(title, snippet)

    return {
        "id": clean_text(raw_job.get("id")),
        "site": site,
        "title": title,
        "company": company,
        "location": location,
        "job_url": job_url,
        "date_posted": date_posted,
        "job_type": clean_text(raw_job.get("job_type")) or "Full-time",
        "salary": salary,
        "is_remote": int(is_remote),
        "snippet": snippet,
        "min_exp": min_exp,
        "max_exp": max_exp,
        "exp_category": exp_category
    }

# Disqualifying patterns for irrelevant / non-software positions
IRRELEVANT_PATTERNS = [
    # Faculty & Education
    r"\b(?:faculty|professor|asst\.?\s*professor|assistant\s+professor|associate\s+professor|lecturer|teacher|trainer|mentor|tutor|dean|instructor|curriculum)\b",
    # Hardware & IT Support / Networking / Telecom
    r"\b(?:network\s+engineer|telecom\s+engineer|rf\s+engineer|hardware\s+engineer|desktop\s+support|laptop\s+technician|technician|service\s+engineer|field\s+engineer|helpdesk|sysadmin|system\s+administrator|rf/network|telecom\s+services|network\s+operations)\b",
    # Non-tech / Corporate / Operations / Finance / Legal / HR / Sales
    r"\b(?:corporate\s+finance|financial\s+analyst|accountant|accounts\s+executive|auditor|legal|counsel|advocate|attorney|human\s+resources|recruiter|talent\s+acquisition|bpo|telecaller|customer\s+support\s+executive|sales\s+executive|marketing\s+executive|business\s+development|regulatory\s+affairs|content\s+writer|copywriter)\b",
    # Non-software engineering branches & Healthcare
    r"\b(?:civil\s+engineer|mechanical\s+engineer|chemical\s+engineer|petroleum|pharmacist|pharmacy|nurse|nursing|doctor)\b",
]

# Senior / High experience titles and keywords
SENIOR_PATTERNS = [
    r"\bsenior\b",
    r"\bsr\.?\s+",
    r"\bsr\b",
    r"\blead\b",
    r"\b(?:principal|principle)\b",
    r"\bstaff\b",
    r"\b(?:architect|architech)\b",
    r"\bmanager\b",
    r"\bdirector\b",
    r"\bhead\s+of\b",
    r"\bvp\b",
    r"\bvice\s+president\b",
    r"\bchief\b",
    r"\bdistinguished\b",
    r"\bfellow\b",
    r"\bexpert\b",
    r"\bsupervisor\b",
    r"\badvanced\b",
    r"\btech\s+lead\b",
    r"\bteam\s+lead\b",
    r"\bconsultant\b",
    # Executive & Corporate Senior Leadership titles
    r"\b(?:avp|agm|dgm|gm|evp|svp|md|cto|cio|coo|ceo)\b",
    # Engineering Level 2+ / Roman numerals II, III, IV, V
    r"\b(?:ii|iii|iv|v)\b",
    r"\b(?:sde|engineer|developer|member|specialist|consultant|analyst|associate|grade|band|level|lvl)\s*[-_]?\s*(?:[2-9][a-z]?)\b",
    r"\b(?:sde|engineer|developer|member|specialist|consultant|analyst|associate)\s*[-_]?\s*(?:ii|iii|iv|v)\b",
    r"\bsoftware\s+development\s+engineer\s*[-_]?\s*(?:[2-9]|ii|iii|iv|v)\b",
    r"\bapplication\s+engineer\s*[-_]?\s*(?:[2-9]|ii|iii|iv|v)\b",
    r"\bassociate\s*(?:iii|iv|v|[3-9])\b",
    r"\b(?:grade\s*)?4[a-b]\b",
    r"\bb[2-4]\b",
    # Numeric candidate experience in title >= 2 years
    r"\b([2-9]|\d{2})\s*(?:to|-|\+)\s*\d*\s*(?:years?|yrs?)\b",
    r"\b([2-9]|\d{2})\+\s*(?:years?|yrs?)\b"
]

# Specialized / proprietary stacks that must only match if requested
PROPRIETARY_OR_DISTINCT_STACKS = {
    "sap": r"\bsap\b",
    "salesforce": r"\bsalesforce\b",
    "dotnet": r"(?:\b\.net\b|\bdotnet\b|\bc#(?!\w))",
    "c#": r"(?:\bc#(?!\w)|\bcsharp\b)",
    "flutter": r"\bflutter\b",
    "ios": r"\b(?:ios|swift|objective-c)\b",
    "android": r"\b(?:android|kotlin)\b",
    "power platform": r"\bpower\s+platform\b",
    "mainframe": r"\b(?:mainframe|cobol)\b",
    "pega": r"\bpega\b",
    "workday": r"\bworkday\b",
    "guidewire": r"\bguidewire\b",
    "servicenow": r"\bservicenow\b",
    "ab initio": r"\bab\s*initio\b"
}

# Recognized tech stack pattern definitions for word-boundary matching
TECH_PATTERNS = {
    "python": r"\bpython\b",
    "sql": r"\b(?:sql|mysql|postgresql|postgres|sqlite|mssql|oracle|plsql)\b",
    "javascript": r"\b(?:javascript|js)\b",
    "typescript": r"\b(?:typescript|ts)\b",
    "java": r"\bjava\b(?!script)",
    "c++": r"(?:\bc\+\+(?!\w)|\bcpp\b)",
    "c#": r"(?:\bc#(?!\w)|\bcsharp\b)",
    "dotnet": r"(?:\b\.net\b|\bdotnet\b|\bc#(?!\w))",
    "golang": r"(?:\bgolang\b|\bgo\b)",
    "go": r"(?:\bgolang\b|\bgo\s+(?:developer|engineer|backend|dev)\b)",
    "react": r"(?:\breact(?:\.js|js)?\b)",
    "node": r"(?:\bnode(?:\.js|js)?\b)",
    "nodejs": r"(?:\bnode(?:\.js|js)?\b)",
    "vue": r"(?:\bvue(?:\.js|js)?\b)",
    "angular": r"(?:\bangular(?:\.js|js)?\b)",
    "django": r"\bdjango\b",
    "flask": r"\bflask\b",
    "fastapi": r"(?:\bfastapi\b|\bfast\s+api\b)",
    "spring": r"\bspring(?:\s+boot)?\b",
    "docker": r"\bdocker\b",
    "aws": r"\baws\b",
    "azure": r"\bazure\b",
    "kubernetes": r"(?:\bkubernetes\b|\bk8s\b)",
    "html": r"\bhtml(?:5)?\b",
    "css": r"\bcss(?:3)?\b",
    "git": r"\bgit\b",
    "rest api": r"\b(?:rest\s*api|restful)\b",
    "microservices": r"\bmicroservices\b"
}

SOFTWARE_ENGINEERING_TITLES = [
    "software engineer", "software developer", "sde", "software development",
    "full stack engineer", "full stack developer", "fullstack developer", "fullstack engineer",
    "backend engineer", "backend developer", "frontend engineer", "frontend developer",
    "web developer", "application engineer", "systems software", "programmer"
]

def is_irrelevant_title(title: str) -> bool:
    """Disqualifies non-software titles (faculty, technicians, corporate finance, legal, sales, etc.)."""
    t = (title or "").lower()
    for pat in IRRELEVANT_PATTERNS:
        if re.search(pat, t):
            return True
    return False

def parse_job_experience(title: str, snippet: str = "") -> Tuple[float, float, str]:
    """
    Extracts minimum and maximum required experience in years and assigns
    the accurate category ('fresher', '1_year', 'mid', 'senior').
    Guarantees that 3+ years or 3-6 years roles are NEVER misclassified as 1-year or fresher.
    """
    title_str = (title or "").strip()
    snippet_str = (snippet or "").strip()
    text = f"{title_str} {snippet_str}".lower()

    # Guard against company age / market presence (e.g. 'company with 15 years in market')
    clean_text = re.sub(r"\b(?:company|organization|firm|agency|founded|presence|in business)\s+[^.!?\n]{0,40}\b\d+\s*(?:years?|yrs?)\b", "", text)
    clean_text = re.sub(r"\b\d+\s*(?:years?|yrs?)\s+of\s+(?:company|industry|business|market)\s+presence\b", "", clean_text)

    min_exp = None
    max_exp = None

    # 1. Range: X-Y years, X to Y years, X–Y years, X—Y years
    m_range = re.search(r"(?:(?:exp|experience|relevant\s+experience|hands-on\s+experience)\s*[:\-]?\s*)?(\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*(\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)", clean_text)
    if m_range:
        min_exp = float(m_range.group(1))
        max_exp = float(m_range.group(2))

    # 2. X+ years
    if min_exp is None:
        m_plus = re.search(r"(?:(?:exp|experience|relevant\s+experience|hands-on\s+experience)\s*[:\-]?\s*)?(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)", clean_text)
        if m_plus:
            min_exp = float(m_plus.group(1))
            max_exp = min_exp + 3.0

    # 3. Minimum / at least X years
    if min_exp is None:
        m_min = re.search(r"(?:min(?:imum)?|at\s+least)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)", clean_text)
        if m_min:
            min_exp = float(m_min.group(1))
            max_exp = min_exp + 3.0

    # 4. Explicit Exp: X years
    if min_exp is None:
        m_exp = re.search(r"(?:exp|experience|relevant\s+experience)\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)", clean_text)
        if m_exp:
            min_exp = float(m_exp.group(1))
            max_exp = min_exp + 2.0

    # 5. X years of experience
    if min_exp is None:
        m_of = re.search(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)(?:\s+of)?\s*(?:relevant\s+)?(?:experience|exp)\b", clean_text)
        if m_of:
            min_exp = float(m_of.group(1))
            max_exp = min_exp + 2.0

    tl = title_str.lower()
    is_senior = any(re.search(p, tl) for p in [
        r"\bsenior\b", r"\bsr\.?\b", r"\blead\b", r"\bprincipal\b", r"\bstaff\b", r"\barchitect\b",
        r"\bmanager\b", r"\bdirector\b", r"\bhead\s+of\b", r"\bvp\b", r"\bvice\s+president\b",
        r"\bchief\b", r"\btech\s+lead\b", r"\bteam\s+lead\b", r"\bengineering\s+manager\b",
        r"\bsde\s*3\b", r"\bsde-3\b", r"\bsde\s*iii\b", r"\bengineer\s*3\b", r"\bdeveloper\s*3\b",
        r"\bl3\b", r"\bl4\b", r"\bl5\b"
    ])
    is_mid = any(re.search(p, tl) for p in [
        r"\bsde\s*2\b", r"\bsde-2\b", r"\bsde\s*ii\b", r"\bengineer\s*2\b", r"\bdeveloper\s*2\b",
        r"\bl2\b", r"\bmid\b", r"\bmid-level\b"
    ])
    is_fresher = any(re.search(p, tl) for p in [
        r"\bintern\b", r"\binternship\b", r"\bfresher\b", r"\btrainee\b", r"\bgraduate\s+trainee\b", r"\bcampus\b"
    ])
    is_junior = any(re.search(p, tl) for p in [
        r"\bjunior\b", r"\bjr\.?\b", r"\bassociate\b", r"\bentry\s*level\b", r"\bentry-level\b",
        r"\bsde\s*1\b", r"\bsde-1\b", r"\bsde\s*i\b", r"\bengineer\s*1\b", r"\bdeveloper\s*1\b", r"\bl1\b"
    ])

    if is_senior:
        min_exp = max(min_exp if min_exp is not None else 5.0, 5.0)
        max_exp = max(max_exp if max_exp is not None else 10.0, 8.0)
        category = "senior"
    elif is_mid:
        min_exp = max(min_exp if min_exp is not None else 3.0, 3.0)
        max_exp = max(max_exp if max_exp is not None else 6.0, 5.0)
        category = "mid"
    elif is_fresher:
        if min_exp is None or min_exp <= 1.0:
            min_exp = 0.0
            max_exp = 1.0
            category = "fresher"
        else:
            category = "mid" if min_exp < 5.0 else "senior"
    elif is_junior:
        if min_exp is None or min_exp <= 2.0:
            min_exp = min_exp if min_exp is not None else 0.0
            max_exp = max_exp if max_exp is not None else 2.0
            category = "1_year"
        else:
            category = "mid" if min_exp < 5.0 else "senior"
    else:
        # Based on explicit numbers parsed
        if min_exp is not None:
            if min_exp >= 5.0:
                category = "senior"
            elif min_exp >= 2.5:
                category = "mid"
            elif min_exp >= 0.5 or (max_exp and max_exp <= 2.5):
                category = "1_year"
            else:
                category = "fresher"
        else:
            # Default for generic developer titles without high-experience signals
            min_exp = 0.0
            max_exp = 2.0
            category = "1_year"

    return min_exp, max_exp, category

def is_high_experience_job(title: str, snippet: str = "", exp_filter: str = "1_year") -> bool:
    """
    Identifies if a job requires high experience (3+ years, Mid, Senior, Lead, etc.)
    and should be strictly excluded from 1-year experience or fresher filtering.
    """
    min_exp, max_exp, category = parse_job_experience(title, snippet)
    if exp_filter in ("fresher", "intern", "0-1"):
        return category in ("mid", "senior") or (min_exp is not None and min_exp >= 1.5)
    elif exp_filter in ("1_year", "1 year", "1-2", "junior"):
        return category in ("mid", "senior") or (min_exp is not None and min_exp >= 3.0)
    elif exp_filter in ("mid", "2-5"):
        return category == "senior" or (min_exp is not None and min_exp >= 5.0)
    elif exp_filter in ("senior", "5+"):
        return category != "senior"
    return False

def matches_experience_filter(job: dict, exp_filter: str = "1_year", years_exp: str = "") -> bool:
    """
    Strictly filters jobs according to user's targeted experience requirement.
    Specifically guarantees that a user wanting 1-year experience roles will ONLY
    receive 1-year / 0-2 yrs / junior / entry roles and NEVER senior/lead/3+ yr / 3-6 yr roles.
    """
    norm_filter = (exp_filter or "1_year").lower().strip()
    if norm_filter in ("all", "any", "all levels", ""):
        return True

    title = job.get("title", "")
    snippet = job.get("snippet", "")
    min_exp, max_exp, category = parse_job_experience(title, snippet)

    # 1. Target: 1 Year Experience (0-2 Yrs / Junior / Entry / SDE 1)
    if norm_filter in ("1_year", "1 year", "1yr", "1", "0-1", "0-2", "1-2", "junior"):
        if category in ("mid", "senior"):
            return False
        if min_exp is not None and min_exp >= 3.0:
            return False
        return True

    # 2. Target: Fresher Only (0-1 Yrs / Intern / Graduate)
    elif norm_filter in ("fresher", "intern", "0_1"):
        if category in ("mid", "senior"):
            return False
        if min_exp is not None and min_exp >= 1.5:
            return False
        return category == "fresher" or (min_exp is not None and min_exp <= 1.0)

    # 3. Target: Mid-Level (2-5 Yrs / 3-6 Yrs)
    elif norm_filter in ("mid", "mid-level", "2-5", "2-4", "3-5", "3-6"):
        return category == "mid" or (min_exp is not None and 2.5 <= min_exp < 5.0)

    # 4. Target: Senior & Leads (5+ Yrs)
    elif norm_filter in ("senior", "sr", "5+", "lead"):
        return category == "senior" or (min_exp is not None and min_exp >= 5.0)

    return True

def get_job_experience_badge(job: dict) -> dict:
    """
    Calculates an experience badge and label for display in UI and email digests.
    Accurately tags roles as 1-2 Yrs, Fresher, 3-6 Yrs Exp, or Senior & Lead.
    """
    title = (job.get("title") or "").strip()
    snippet = (job.get("snippet") or "").strip()
    min_exp, max_exp, category = parse_job_experience(title, snippet)

    if category == "senior":
        lbl = f"⭐ {int(min_exp)}+ Yrs & Lead" if min_exp and min_exp >= 5 else "⭐ Senior & Lead"
        return {"category": "senior", "label": lbl, "badge_class": "badge-purple", "min_exp": min_exp, "max_exp": max_exp}
    elif category == "mid":
        if min_exp and max_exp and max_exp > min_exp:
            lbl = f"🚀 {int(min_exp)}-{int(max_exp)} Yrs Exp"
        elif min_exp:
            lbl = f"🚀 {int(min_exp)}+ Yrs Exp"
        else:
            lbl = "🚀 3-5 Yrs Exp"
        return {"category": "mid", "label": lbl, "badge_class": "badge-indigo", "min_exp": min_exp, "max_exp": max_exp}
    elif category == "fresher":
        return {"category": "fresher", "label": "🎓 Fresher / Intern", "badge_class": "badge-emerald", "min_exp": min_exp, "max_exp": max_exp}
    else:
        lbl = f"🎯 {int(min_exp)}-{int(max_exp)} Yrs Exp" if (min_exp is not None and max_exp is not None and max_exp <= 2) else "🎯 1-2 Yrs Exp"
        return {"category": "1_year", "label": lbl, "badge_class": "badge-sky", "min_exp": min_exp, "max_exp": max_exp}

def matches_location_filter(job: dict, target_locations: Optional[List[str]] = None) -> bool:
    """Verifies that a job strictly matches user's preferred locations (including Remote)."""
    if not target_locations:
        return True

    clean_locs = []
    if isinstance(target_locations, str):
        clean_locs = [l.strip().lower() for l in target_locations.split(",") if l.strip()]
    else:
        clean_locs = [str(l).strip().lower() for l in target_locations if str(l).strip()]
    clean_locs = [l for l in clean_locs if l not in ("all", "any", "all locations", "all cities", "")]

    if not clean_locs:
        return True

    job_loc = (job.get("location") or "").lower()
    job_title = (job.get("title") or "").lower()
    is_remote = bool(job.get("is_remote")) or "remote" in job_loc or "remote" in job_title or "work from home" in job_loc

    for req_loc in clean_locs:
        if req_loc in ("remote", "work from home", "wfh"):
            if is_remote:
                return True
        elif req_loc in ("bangalore", "bengaluru", "bengaluru east", "karnataka"):
            if any(w in job_loc for w in ["bangalore", "bengaluru", "ka, in", "karnataka"]):
                return True
        elif req_loc in ("hyderabad", "telangana"):
            if any(w in job_loc for w in ["hyderabad", "hyderābād", "ts, in", "telangana"]):
                return True
        elif req_loc in ("pune", "maharashtra"):
            if any(w in job_loc for w in ["pune", "mh, in", "maharashtra"]):
                return True
        elif req_loc in ("chennai", "tamil nadu"):
            if any(w in job_loc for w in ["chennai", "tn, in", "tamil nadu"]):
                return True
        elif req_loc in ("delhi", "ncr", "gurgaon", "gurugram", "noida", "haryana"):
            if any(w in job_loc for w in ["delhi", "ncr", "gurgaon", "gurugram", "noida", "dl, in", "haryana"]):
                return True
        elif req_loc in ("mumbai", "navi mumbai"):
            if any(w in job_loc for w in ["mumbai", "navi mumbai", "bombay", "thane"]):
                return True
        elif req_loc in ("kolkata", "calcutta", "west bengal"):
            if any(w in job_loc for w in ["kolkata", "calcutta", "wb, in", "west bengal"]):
                return True
        elif req_loc in ("ahmedabad", "gujarat"):
            if any(w in job_loc for w in ["ahmedabad", "gj, in", "gujarat", "gandhinagar"]):
                return True
        elif req_loc in ("kochi", "cochin", "kerala", "trivandrum", "thiruvananthapuram"):
            if any(w in job_loc for w in ["kochi", "cochin", "trivandrum", "thiruvananthapuram", "kl, in", "kerala"]):
                return True
        elif req_loc in ("indore", "bhopal", "madhya pradesh"):
            if any(w in job_loc for w in ["indore", "bhopal", "mp, in", "madhya pradesh"]):
                return True
        elif req_loc in ("jaipur", "rajasthan"):
            if any(w in job_loc for w in ["jaipur", "rj, in", "rajasthan"]):
                return True
        elif req_loc in ("coimbatore",):
            if any(w in job_loc for w in ["coimbatore", "tn, in"]):
                return True
        elif req_loc in ("chandigarh", "mohali", "punjab"):
            if any(w in job_loc for w in ["chandigarh", "mohali", "pb, in", "punjab"]):
                return True
        elif req_loc in ("bhubaneswar", "odisha"):
            if any(w in job_loc for w in ["bhubaneswar", "or, in", "odisha"]):
                return True
        else:
            if req_loc in job_loc:
                return True

    return False

def matches_email_filter(
    job: dict, 
    exp_filter: str = "1_year", 
    target_roles: Optional[List[str]] = None, 
    target_languages: Optional[List[str]] = None,
    target_locations: Optional[List[str]] = None,
    years_exp: str = ""
) -> bool:
    """
    Combined strict filter for daily email digest delivery.
    Verifies that a job strictly matches:
      1. Non-software disqualification (no faculty, technician, corporate finance, legal, sales)
      2. Experience filter (e.g. 1-year experience / 0-2 yrs, no senior roles, no SDE-2/Level-2+)
      3. Contradictory proprietary tech stack disqualification (e.g. no SAP, Dotnet, Salesforce unless requested)
      4. Preferred target job roles (e.g. Software Engineer, Python Developer, Backend Developer)
      5. Preferred programming languages & tech stack (e.g. Python, SQL, JavaScript, React)
    """
    title = (job.get("title") or "").strip()
    snippet = (job.get("snippet") or "").strip()
    tl = title.lower()
    sl = snippet.lower()
    full = f"{tl} {sl}"

    # 1. Non-software title disqualification
    if is_irrelevant_title(title):
        return False

    # 2. Experience check
    if not matches_experience_filter(job, exp_filter=exp_filter, years_exp=years_exp):
        return False

    # Normalize roles list
    clean_roles: List[str] = []
    if target_roles:
        if isinstance(target_roles, str):
            clean_roles = [r.strip().lower() for r in target_roles.split(",") if r.strip()]
        else:
            clean_roles = [str(r).strip().lower() for r in target_roles if str(r).strip()]
        clean_roles = [r for r in clean_roles if r not in ("all", "any", "all roles")]

    # Normalize languages list
    clean_langs: List[str] = []
    if target_languages:
        if isinstance(target_languages, str):
            clean_langs = [l.strip().lower() for l in target_languages.split(",") if l.strip()]
        else:
            clean_langs = [str(l).strip().lower() for l in target_languages if str(l).strip()]
        clean_langs = [l for l in clean_langs if l not in ("all", "any", "all languages")]

    # 3. Disqualify contradictory proprietary / specialized tech stack in title unless requested
    for stack_key, stack_pat in PROPRIETARY_OR_DISTINCT_STACKS.items():
        if re.search(stack_pat, tl):
            has_requested = any(stack_key in r for r in clean_roles) or any(stack_key in l for l in clean_langs)
            if not has_requested:
                return False

    # 4. Target Roles check
    if clean_roles:
        matched_role = False
        for r in clean_roles:
            if r in tl:
                matched_role = True
                break

            # Python Developer
            if "python" in r:
                if "python" in tl:
                    matched_role = True
                    break
                if any(w in tl for w in ["software engineer", "software developer", "sde", "backend developer", "backend engineer"]) and ("python" in sl or "python" in clean_langs):
                    matched_role = True
                    break

            # Backend Developer
            if "backend" in r or "back-end" in r:
                if "backend" in tl or "back-end" in tl:
                    matched_role = True
                    break
                if any(w in tl for w in ["software engineer", "software developer", "sde", "python developer", "java developer", "node developer"]):
                    matched_role = True
                    break

            # Frontend Developer
            if "frontend" in r or "front-end" in r:
                if any(w in tl for w in ["frontend", "front-end", "ui developer", "ui engineer", "web developer", "react", "angular", "vue"]):
                    matched_role = True
                    break

            # Full Stack Developer
            if "full stack" in r or "fullstack" in r or "full-stack" in r:
                if any(w in tl for w in ["full stack", "fullstack", "full-stack"]):
                    matched_role = True
                    break
                if ("frontend" in tl or "ui" in tl) and "backend" in tl:
                    matched_role = True
                    break

            # Data Engineer
            if "data engineer" in r:
                if any(w in tl for w in ["data engineer", "data engineering", "big data", "etl"]):
                    matched_role = True
                    break

            # DevOps / Cloud
            if "devops" in r or "cloud" in r:
                if any(w in tl for w in ["devops", "cloud engineer", "cloud developer", "sre", "platform engineer", "infrastructure"]):
                    matched_role = True
                    break

            # General Software Engineer / Developer / SDE
            if any(w in r for w in ["software engineer", "software developer", "sde"]):
                if any(w in tl for w in SOFTWARE_ENGINEERING_TITLES):
                    matched_role = True
                    break
                if any(w in tl for w in ["developer", "engineer"]) and any(w in tl for w in ["python", "java", "backend", "web", "associate", "junior"]):
                    matched_role = True
                    break

        if not matched_role:
            return False

    # 5. Target Languages / Tech Stack check
    if clean_langs:
        matched_lang = False
        for l in clean_langs:
            pat = TECH_PATTERNS.get(l, r"\b" + re.escape(l) + r"\b")
            if re.search(pat, full, re.IGNORECASE):
                matched_lang = True
                break
        if not matched_lang:
            return False

    # 6. Target Locations check (Bangalore, Hyderabad, Pune, Chennai, Delhi NCR, Remote, etc.)
    if target_locations and not matches_location_filter(job, target_locations):
        return False

    return True

