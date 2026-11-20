import re
from typing import Dict, List, Optional, Any

KNOWLEDGE_BASE = [
    {
        "keywords": ["fresher", "entry", "strategy", "begin", "start", "college", "graduate", "first job"],
        "title": "🎓 High-Impact Fresher Job Hunting Strategy (0-1 Yrs)",
        "response": (
            "### 🎯 The 4-Pillar Fresher Job Strategy for Maximum Callbacks\n\n"
            "1. **The 70-20-10 Application Rule**:\n"
            "   - **70% Direct Job Boards & Portals**: Apply within the first 24 hours of posting on LinkedIn, Internshala, and Naukri.\n"
            "   - **20% Employee Referrals**: Find alumni from your college working at target companies and ask for referrals via polite LinkedIn DMs.\n"
            "   - **10% Cold Outreach to Founders/HR**: Message tech leads and startup founders directly with a custom cover note.\n\n"
            "2. **Proof of Work over GPA**:\n"
            "   - Build 2 full-stack deployed projects (live URL on Vercel/Render + clean GitHub repo with README and architecture diagram).\n"
            "   - Avoid basic clone projects (Todo apps, basic calculators); instead build apps with auth, databases, caching, or API integrations.\n\n"
            "3. **Daily Cadence**:\n"
            "   - 15-20 targeted applications per day.\n"
            "   - 3 LeetCode problems (1 Easy, 2 Medium in blind 75).\n"
            "   - 2 customized connection requests on LinkedIn.\n\n"
            "💡 *Pro-tip*: Freshers who tailor the top 3 bullet points of their resume to match the job description receive 3.4x more interview invites."
        )
    },
    {
        "keywords": ["ats", "resume", "score", "format", "keyword", "template", "cv"],
        "title": "📄 ATS Resume Optimization & Callback Secrets",
        "response": (
            "### 📄 How to Guarantee 85%+ ATS Compatibility\n\n"
            "1. **Format Standards**:\n"
            "   - Use single-column format (multi-column tables often break legacy ATS parsers).\n"
            "   - Standard font: Inter, Arial, Calibri (10-11pt).\n"
            "   - Export as clean text-selectable PDF (never scanned image).\n\n"
            "2. **The Winning Bullet Point Formula (Google X-Y-Z Method)**:\n"
            "   - *Formula*: **[Action Verb]** + **[Task/Feature Built]** + using **[Tech Stack]**, resulting in **[Quantifiable Metric]**.\n"
            "   - *Weak*: *'Worked on backend APIs using Node.js.'*\n"
            "   - *Strong*: *'Architected 12 RESTful endpoints using Node.js & Redis, reducing median response latency by 38% for 5,000+ daily requests.'*\n\n"
            "3. **Essential Keyword Sections**:\n"
            "   - Group skills into: **Languages** (Python, JavaScript), **Frameworks** (FastAPI, React), **Databases** (PostgreSQL, MongoDB), and **DevOps/Tools** (Docker, Git, Linux).\n"
            "   - Include your GitHub and Live Demo links right in the header next to your email."
        )
    },
    {
        "keywords": ["salary", "ctc", "package", "sde-1", "sde 1", "fresher salary", "bangalore", "hyderabad", "gurgaon", "pay"],
        "title": "💰 2026 Tech Salary Benchmarks in India & Remote",
        "response": (
            "### 💰 2026 Industry Salary Guide (Software Engineer / SDE-1)\n\n"
            "| Tier / Company Type | Typical Fresher CTC | 1-2 Yrs Experience |\n"
            "| :--- | :--- | :--- |\n"
            "| **Product Unicorns & MNCs** (Amazon, Microsoft, Swiggy) | ₹14L - ₹28L LPA | ₹22L - ₹38L LPA |\n"
            "| **High-Growth Startups (Series A-C)** | ₹8L - ₹16L LPA | ₹14L - ₹24L LPA |\n"
            "| **Mid-Market & Bootstrapped Tech** | ₹5L - ₹9L LPA | ₹8L - ₹14L LPA |\n"
            "| **IT Services / Mass Recruiters** | ₹3.5L - ₹6.5L LPA | ₹5.5L - ₹8.5L LPA |\n"
            "| **Global Remote (US/EU startups)** | $35k - $65k USD | $55k - $95k USD |\n\n"
            "💡 *Negotiation Rule for Freshers*: Never reveal your current or minimum expectation first. Ask: *'Could you share the budgeted range for this position so we can ensure alignment?'*"
        )
    },
    {
        "keywords": ["remote", "work from home", "wfh", "international", "global", "usd"],
        "title": "🌐 Finding High-Paying Remote Tech Jobs",
        "response": (
            "### 🌐 Winning Remote Developer Roles\n\n"
            "1. **Where to Apply (100% Free Portals)**:\n"
            "   - **Wellfound (formerly AngelList)**: Best for remote venture-backed startups.\n"
            "   - **JobRadar AI 'Remote Only' Filter**: Aggregates verified remote roles across LinkedIn, Google Jobs & Indeed.\n"
            "   - **Hacker News 'Who is Hiring?'**: Monthly thread on the 1st of every month.\n"
            "   - **We Work Remotely & RemoteOK**: Direct international listings.\n\n"
            "2. **Key Skills for Remote Engineers**:\n"
            "   - Asynchronous written communication (clear PR descriptions & documentation).\n"
            "   - Git proficiency (branching, rebasing, code reviews).\n"
            "   - Self-driven autonomous project management."
        )
    },
    {
        "keywords": ["dsa", "leetcode", "coding", "algorithm", "data structures", "pattern", "neetcode"],
        "title": "⚡ Top 10 DSA Patterns for Coding Rounds",
        "response": (
            "### ⚡ The 10 Core DSA Patterns (Solve 80% of Interview Problems)\n\n"
            "1. **Two Pointers**: Trapping Rain Water, 3Sum, Valid Palindrome.\n"
            "2. **Sliding Window**: Longest Substring Without Repeating Characters, Min Size Subarray Sum.\n"
            "3. **Fast & Slow Pointers**: Linked List Cycle, Middle of the Linked List.\n"
            "4. **Binary Search on Answer**: Koko Eating Bananas, Search in Rotated Sorted Array.\n"
            "5. **BFS (Breadth First Search)**: Level Order Traversal, Rotten Oranges, Shortest Path in Maze.\n"
            "6. **DFS & Backtracking**: Subsets, Permutations, Word Search.\n"
            "7. **Monotonic Stack**: Next Greater Element, Daily Temperatures, Largest Rectangle in Histogram.\n"
            "8. **Top K Elements (Heaps)**: Kth Largest Element, Top K Frequent Elements.\n"
            "9. **Dynamic Programming (1D & 2D)**: Coin Change, Longest Increasing Subsequence, 0/1 Knapsack.\n"
            "10. **Trie (Prefix Tree)**: Autocomplete, Word Search II.\n\n"
            "💡 Master these patterns rather than memorizing 500 isolated problems!"
        )
    },
    {
        "keywords": ["behavioral", "hr", "star", "interview", "questions", "tell me about yourself", "why should we hire you"],
        "title": "💬 HR & Behavioral Mastery (STAR Method)",
        "response": (
            "### 💬 Cracking Behavioral Rounds with the STAR Method\n\n"
            "Structure every behavioral answer in 4 parts:\n"
            "- **Situation**: Set the scene in 2 sentences (context, project, team).\n"
            "- **Task**: Explain the exact challenge or objective you were responsible for.\n"
            "- **Action**: Specify the concrete steps **YOU** took (technologies chosen, communication, debugging).\n"
            "- **Result**: The quantifiable outcome (*'Reduced query load by 40% and shipped 2 days ahead of schedule'*).\n\n"
            "**The Top 4 Questions to Prepare**:\n"
            "1. *'Tell me about a time you handled a difficult technical bug.'*\n"
            "2. *'How do you handle disagreement with a teammate over architectural choices?'*\n"
            "3. *'Why do you want to join our company specifically?'*\n"
            "4. *'What is a project you are most proud of, and what would you do differently today?'*"
        )
    },
    {
        "keywords": ["cold email", "dm", "outreach", "linkedin message", "connect", "recruiter"],
        "title": "✉️ High-Conversion Recruiter Outreach Blueprint",
        "response": (
            "### ✉️ The 3-Sentence Recruiter Outreach Template\n\n"
            "**Subject**: *Application: [Job Title] | [Your Name] (Specializing in [Key Tech])*\n\n"
            "*Hi [Recruiter / Engineering Manager Name],*\n\n"
            "*I noticed [Company] is scaling the [Team/Product] and recently opened the [Job Title] role. As a software developer with hands-on experience building scalable applications using [Skill 1] and [Skill 2], I have already deployed projects solving [Problem].*\n\n"
            "*Here is my live portfolio: [Link] and GitHub: [Link]. Would you be open to a 10-minute intro chat this week?*\n\n"
            "*Best regards,*\n"
            "*[Your Name]*"
        )
    },
    {
        "keywords": ["system design", "architecture", "scalability", "caching", "database"],
        "title": "🌐 Junior System Design Fundamentals",
        "response": (
            "### 🌐 Key System Design Concepts for Junior to Mid Engineers\n\n"
            "1. **Horizontal vs Vertical Scaling**: Adding more nodes (scale out) vs upgrading CPU/RAM (scale up).\n"
            "2. **Load Balancing**: Distributing incoming traffic (Round Robin, Least Connections, Consistent Hashing).\n"
            "3. **Caching**: Redis / Memcached in front of DB; Cache-Aside, Write-Through strategies.\n"
            "4. **Database Selection**: Relational (PostgreSQL/MySQL for ACID & structured data) vs NoSQL (MongoDB/DynamoDB for flexible schema & fast horizontal scale).\n"
            "5. **Message Queues**: RabbitMQ/Kafka for asynchronous task processing and decoupling services."
        )
    }
]

def get_career_assistant_response(
    query: str,
    user_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Intelligent free local assistant that matches user queries with expert career advice,
    customized to the candidate's active role and technical skills.
    """
    clean_query = query.lower().strip()
    user_name = "Candidate"
    target_role = "Software Engineer"
    skills = []

    if user_context:
        user_name = user_context.get("name") or "Candidate"
        target_role = user_context.get("target_role") or "Software Engineer"
        skills = user_context.get("skills") or []

    # Search knowledge base by keyword density
    best_match = None
    best_score = 0

    for item in KNOWLEDGE_BASE:
        score = sum(1 for kw in item["keywords"] if kw in clean_query)
        if score > best_score:
            best_score = score
            best_match = item

    if best_match and best_score > 0:
        reply = best_match["response"]
        title = best_match["title"]
    else:
        # Contextual dynamic response based on skills and query
        skills_str = ", ".join(skills[:3]) if skills else "Python, JavaScript, and SQL"
        reply = (
            f"### 🤖 JobRadar Career Guidance for {user_name}\n\n"
            f"Here are actionable suggestions tailored to your **{target_role}** goals:\n\n"
            f"1. **Targeting Roles**: Focus on positions requesting your core competencies in **{skills_str}**. Use JobRadar's **Super Match (>80%)** filter to prioritize applications with the highest callback probability.\n"
            f"2. **Application Speed**: Apply within 24 hours of job postings. Check the Live Opportunities tab daily at your scheduled digest time.\n"
            f"3. **Interview Preparation**: For each role you save, click **'🎯 Interview Prep'** in the job card to get tailored technical questions and behavioral STAR points generated on-the-fly.\n"
            f"4. **Direct Outreach**: Connect with recruiters and team leads using our 1-click **LinkedIn DM** generator in the AI Suite.\n\n"
            f"💬 *Try asking me:* 'How can I optimize my resume for ATS?', 'What are top fresher salaries?', or 'Top DSA patterns for interviews'!"
        )
        title = f"💡 Career Insights for {target_role}"

    return {
        "title": title,
        "reply": reply,
        "suggested_topics": [
            "🎓 Fresher Strategy",
            "📄 ATS Resume Tips",
            "💰 SDE-1 Salary",
            "⚡ Top DSA Patterns",
            "💬 Behavioral STAR Questions"
        ]
    }
