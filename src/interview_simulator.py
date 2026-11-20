"""
src/interview_simulator.py
==========================
AI Technical & HR Mock Interview Simulator for Indian Tech Roles.
Generates tailored questions based on Company, Role, and Candidate Resume,
and evaluates answers with scoring, feedback, gap analysis, and ideal model answers.
"""

import re
import html
from typing import Dict, Any, List, Optional

INTERVIEW_QUESTION_BANKS = {
    "python": [
        {
            "topic": "Python Internals & Memory",
            "question": "How does Python handle memory management and garbage collection? Can you explain how reference counting and the cyclic garbage collector work together?",
            "hint": "Mention reference counting, sys.getrefcount, generational GC (gen 0, 1, 2), and circular references (gc module).",
            "ideal_answer": "Python primarily uses Reference Counting for memory management. Every Python object has a reference count (`ob_refcnt`). When this count reaches 0, the memory is deallocated immediately. However, reference counting alone cannot clean up cyclic references (e.g., object A referencing object B, and B referencing A). To solve this, Python runs a secondary Generational Cyclic Garbage Collector that operates across three generations (0, 1, 2). New objects start in Generation 0. If they survive a GC pass, they are promoted to older generations which are inspected less frequently, balancing performance and memory reclamation.",
            "key_concepts": ["reference counting", "cyclic garbage collector", "generational", "generations", "deallocation", "circular"]
        },
        {
            "topic": "Async & Concurrency",
            "question": "What is the Python GIL (Global Interpreter Lock), and how does asynchronous programming with `asyncio` differ from multi-threading and multi-processing?",
            "hint": "Explain that GIL restricts execution to one native thread at a time for bytecode, and how asyncio uses single-threaded event loops for I/O bound tasks while multiprocessing bypasses the GIL for CPU-bound tasks.",
            "ideal_answer": "The Global Interpreter Lock (GIL) is a mutex that protects Python objects, preventing multiple native threads from executing Python bytecodes simultaneously. Because of the GIL, standard multi-threading in CPython does not give true CPU parallelism. For I/O-bound operations (network requests, database queries), `asyncio` provides cooperative multitasking using an event loop and non-blocking sockets on a single thread with minimal overhead. For CPU-bound tasks (data crunching, ML inferences), `multiprocessing` spawns distinct OS processes, each with its own Python interpreter and memory space, effectively bypassing the GIL.",
            "key_concepts": ["gil", "global interpreter lock", "event loop", "cooperative", "cpu-bound", "i/o-bound", "multiprocessing", "thread"]
        },
        {
            "topic": "FastAPI & REST Architecture",
            "question": "In a FastAPI or Flask microservice, how do you handle database connection pooling and asynchronous background tasks to prevent request timeouts under high traffic?",
            "hint": "Mention SQLAlchemy connection pool (QueuePool, pool_size, max_overflow), async engines, and FastAPI BackgroundTasks or Celery/Redis for decoupled async workers.",
            "ideal_answer": "Under high traffic, creating a fresh database connection per request exhausts DB connection limits and causes latency spikes. We resolve this by using a persistent Connection Pool (such as SQLAlchemy AsyncEngine with `QueuePool`, tuning `pool_size=20` and `max_overflow=10`). Sessions are injected via dependency injection (`Depends(get_db)`) and closed in a `try...finally` block. For heavy tasks like generating PDFs, sending emails, or calling third-party webhooks, we decouple execution from the HTTP request-response cycle using FastAPI `BackgroundTasks` for lightweight jobs or Celery backed by Redis/RabbitMQ for mission-critical, retryable background tasks.",
            "key_concepts": ["connection pool", "pool", "sqlalchemy", "celery", "redis", "backgroundtasks", "dependency injection", "timeout"]
        }
    ],
    "sql": [
        {
            "topic": "Database Indexing & Performance",
            "question": "How do B-Tree indexes work in relational databases (PostgreSQL/MySQL), and why can having too many indexes degrade database performance?",
            "hint": "Discuss balanced tree traversal (O(log N)), composite index leftmost prefix rule, and write overhead on INSERT/UPDATE/DELETE.",
            "ideal_answer": "Relational databases use B-Tree (Balanced Tree) indexes where data pointers are sorted hierarchically, allowing search, range scans, and equality lookups in O(log N) time instead of sequential table scans (O(N)). While indexes drastically speed up read queries (`SELECT`), each index carries a write overhead: every time a row is inserted, updated, or deleted, all associated B-Trees must be rebalanced and updated on disk. Additionally, excessive indexes consume significant RAM buffer cache and can confuse query planners when selecting execution plans. Best practice is to index high-cardinality foreign keys and columns frequently used in `WHERE`, `JOIN`, and `ORDER BY` clauses.",
            "key_concepts": ["b-tree", "b tree", "balanced tree", "log n", "sequential scan", "write overhead", "insert", "update", "buffer cache"]
        },
        {
            "topic": "ACID & Transaction Isolation",
            "question": "Can you explain the difference between 'Read Committed' and 'Repeatable Read' isolation levels, and what anomaly 'Repeatable Read' prevents?",
            "hint": "Discuss dirty reads, non-repeatable reads, and phantom reads. Mention snapshot isolation.",
            "ideal_answer": "In 'Read Committed' (default in PostgreSQL), a transaction only reads data committed before the query began. However, if the transaction reads row A, and another transaction updates and commits row A, reading row A a second time within the same transaction yields different data (Non-Repeatable Read). 'Repeatable Read' prevents Non-Repeatable Reads by ensuring a transaction sees a consistent snapshot of the database taken at the start of the transaction. Any updates made and committed by concurrent transactions are hidden until the current transaction completes.",
            "key_concepts": ["read committed", "repeatable read", "non-repeatable read", "snapshot", "dirty read", "isolation", "transaction", "acid"]
        }
    ],
    "javascript_react": [
        {
            "topic": "React Rendering & Reconciliation",
            "question": "Explain how React's Virtual DOM and Fiber reconciliation algorithm work. When should you use `useCallback` or `useMemo` to prevent unnecessary re-renders?",
            "hint": "Mention Virtual DOM diffing (heuristics, keys), Fiber tree units of work, referential equality, and function recreations on parent render.",
            "ideal_answer": "React maintains a lightweight in-memory representation of the UI called the Virtual DOM. When state changes, React creates a new VDOM tree and uses the Fiber reconciliation engine to diff it against the previous tree. Fiber breaks rendering into incremental, interruptible units of work. A component re-renders whenever its parent re-renders, causing all inline functions and computed objects to get fresh memory references. `useCallback` caches a function definition between renders to maintain referential equality when passed to memoized children (`React.memo`). `useMemo` caches the calculated result of expensive pure computations unless its dependencies change.",
            "key_concepts": ["virtual dom", "fiber", "reconciliation", "diff", "referential equality", "usecallback", "usememo", "re-render", "memo"]
        },
        {
            "topic": "JavaScript Event Loop",
            "question": "How does the JavaScript single-threaded Event Loop handle asynchronous code? What is the execution priority between Microtasks and Macrotasks?",
            "hint": "Discuss Call Stack, Web APIs, Microtask Queue (Promises, queueMicrotask), and Task/Macrotask Queue (setTimeout, setInterval).",
            "ideal_answer": "JavaScript runs on a single main thread with a Call Stack. Synchronous functions execute immediately on the stack. Asynchronous callbacks are offloaded to runtime Web APIs and placed into queues upon completion. The Event Loop continuously checks if the Call Stack is empty. Once clear, it drains the entire Microtask Queue (Promises `.then/catch/finally`, `async/await`, `queueMicrotask`) before picking the next single Macrotask (e.g. `setTimeout`, `setInterval`, I/O events). This means Microtasks always have strict priority over Macrotasks.",
            "key_concepts": ["call stack", "event loop", "microtask", "macrotask", "promises", "settimeout", "queue", "single-threaded"]
        }
    ],
    "system_design": [
        {
            "topic": "High-Throughput Architecture",
            "question": "How would you design an API rate limiter for a multi-node backend service handling 100,000 requests per second in India?",
            "hint": "Discuss Redis Sliding Window Log or Token Bucket algorithm, atomic Lua scripts, and HTTP 429 Too Many Requests response headers.",
            "ideal_answer": "To enforce rate limits across a distributed multi-node cluster, in-memory local limits are insufficient; we need a centralized, ultra-fast store like Redis. The Token Bucket or Sliding Window Counter algorithm is ideal. In Redis, we execute an atomic Lua script that tracks timestamps in a Redis Sorted Set (`ZSET`) keyed by `user_id` or `IP`. The Lua script removes records older than the sliding window (`ZREMRANGEBYSCORE`), counts active requests (`ZCARD`), and either appends the current timestamp or rejects with HTTP 429 and `Retry-After` headers if the limit is exceeded. Running this via Lua ensures atomic execution with sub-millisecond latency.",
            "key_concepts": ["rate limiter", "redis", "token bucket", "sliding window", "lua script", "atomic", "http 429", "distributed"]
        },
        {
            "topic": "Caching & Consistency",
            "question": "What is the difference between Cache-Aside and Write-Through caching patterns, and how do you prevent Cache Stampede (Thundering Herd) when a key expires?",
            "hint": "Explain Cache-Aside (lazy loading) vs Write-Through (write to cache and DB simultaneously). Prevent stampede via distributed mutex/locking or probabilistic early expiration.",
            "ideal_answer": "In Cache-Aside (Lazy Loading), the application checks the cache first; on a miss, it queries the database, writes the result to cache, and returns. In Write-Through, the application writes directly to the cache, which synchronously updates the DB. Cache Stampede occurs when a high-traffic cache key expires, causing hundreds of concurrent requests to hit the database simultaneously. To prevent this, we can: 1) Use a distributed lock (e.g., Redis `SETNX`) so only one thread re-computes the cache while others wait or return stale data, 2) Implement Probabilistic Early Expiration (XFetch algorithm) where background workers refresh the key before it hits TTL, or 3) Add random jitter to cache expiration times.",
            "key_concepts": ["cache-aside", "write-through", "cache stampede", "thundering herd", "mutex", "distributed lock", "ttl", "jitter"]
        }
    ],
    "behavioral": [
        {
            "topic": "Conflict & Engineering Disagreement",
            "question": "Tell me about a time you had a technical disagreement with a team member or senior engineer. How did you handle it and what was the outcome?",
            "hint": "Use the STAR method (Situation, Task, Action, Result). Focus on objective metrics, benchmarks, respectful communication, and team alignment.",
            "ideal_answer": "Situation: In our team project, a teammate wanted to implement an ORM for an analytics dashboard, while I advocated for raw, optimized SQL queries due to latency concerns. Task: We needed to settle on a clean architecture without delaying our two-week sprint milestone. Action: Instead of an ideological debate, I built a quick benchmark script with mock data simulating 50,000 records. The benchmark demonstrated that raw queries with indexing ran in 12ms, while the ORM generated N+1 queries taking over 450ms. I shared these findings constructively with my colleague and suggested we use the ORM for standard CRUD while using raw queries for the analytics endpoints. Result: My teammate appreciated the objective data, our hybrid solution met the performance SLA, and the sprint was delivered on time.",
            "key_concepts": ["star", "situation", "task", "action", "result", "benchmark", "objective", "compromise", "communication"]
        },
        {
            "topic": "Handling Production Outages & Pressure",
            "question": "Describe a scenario where a critical bug or production issue occurred right before a deadline. How did you prioritize, diagnose, and resolve it?",
            "hint": "Focus on calm systematic triage: checking logs, reverting or hotfixing, root cause analysis (RCA), and preventative measures.",
            "ideal_answer": "Situation: An hour after deploying a payment integration update, users reported intermittent failure toasts during checkout. Task: As part of the engineering team, I needed to urgently halt customer impact, restore functionality, and identify the root cause. Action: I first checked our APM error logs and Sentry alerts, discovering an unhandled null response from the third-party payment gateway's webhook. I coordinated with my team lead to roll back to the previous stable release, immediately restoring customer checkout within 8 minutes. Afterward, I reproduced the bug in our staging environment, added defensive parsing with fallbacks and unit test coverage for null payloads, and redeployed safely. Result: Checkout success rate recovered to 99.8%, and we instituted an automated integration test suite to catch third-party schema drifts before production.",
            "key_concepts": ["outage", "rollback", "logs", "root cause", "triage", "sentry", "apm", "monitoring", "post-mortem", "hotfix"]
        }
    ]
}

def generate_mock_interview(
    job: Dict[str, Any],
    user: Dict[str, Any],
    focus_area: str = "comprehensive"
) -> Dict[str, Any]:
    """
    Generates a 5-question mock interview session tailored to the target company,
    job description, and candidate's skills.
    """
    company = (job.get("company") or "Tech Company").strip()
    title = (job.get("title") or "Software Engineer").strip()
    user_skills = user.get("skills") or ["Python", "SQL", "Git"]
    if isinstance(user_skills, str):
        try:
            import json
            user_skills = json.loads(user_skills)
        except Exception:
            user_skills = ["Software Engineering"]

    exp_level = (user.get("experience_level") or "fresher").lower()

    # Determine primary tech focus from job snippet / title
    snippet = ((job.get("snippet") or "") + " " + title).lower()
    
    questions = []
    
    # 1. Core Technical / Language Question
    if "react" in snippet or "frontend" in snippet or "javascript" in snippet:
        q1 = INTERVIEW_QUESTION_BANKS["javascript_react"][0].copy()
    else:
        q1 = INTERVIEW_QUESTION_BANKS["python"][0].copy()
    q1["id"] = "q1"
    q1["round"] = "Round 1: Technical Foundations"
    q1["difficulty"] = "Mid" if exp_level != "fresher" else "Entry"
    questions.append(q1)

    # 2. Database & Data Architecture
    q2 = INTERVIEW_QUESTION_BANKS["sql"][0].copy()
    q2["id"] = "q2"
    q2["round"] = "Round 1: Database & Data Architecture"
    q2["difficulty"] = "Mid"
    questions.append(q2)

    # 3. Asynchronous / Concurrency / Frameworks
    if "python" in snippet or "django" in snippet or "fastapi" in snippet or "backend" in snippet:
        q3 = INTERVIEW_QUESTION_BANKS["python"][1].copy()
    elif "react" in snippet or "frontend" in snippet:
        q3 = INTERVIEW_QUESTION_BANKS["javascript_react"][1].copy()
    else:
        q3 = INTERVIEW_QUESTION_BANKS["python"][2].copy()
    q3["id"] = "q3"
    q3["round"] = "Round 2: Architecture & Concurrency"
    q3["difficulty"] = "Senior" if exp_level in ("mid", "senior") else "Mid"
    questions.append(q3)

    # 4. System Design / Scalability
    q4 = INTERVIEW_QUESTION_BANKS["system_design"][0].copy()
    q4["id"] = "q4"
    q4["round"] = "Round 2: Scalability & System Design"
    q4["difficulty"] = "Senior" if exp_level in ("mid", "senior") else "Mid"
    questions.append(q4)

    # 5. Behavioral / Company Fit (STAR)
    q5 = INTERVIEW_QUESTION_BANKS["behavioral"][0].copy()
    q5["id"] = "q5"
    q5["round"] = "Round 3: Leadership & Behavioral (STAR)"
    q5["difficulty"] = "General"
    q5["question"] = f"At {company}, software engineers frequently deal with cross-team dependencies. {q5['question']}"
    questions.append(q5)

    return {
        "session_id": f"sim_{job.get('id', 'default')[:8]}",
        "company": company,
        "title": title,
        "candidate_name": user.get("name") or "Candidate",
        "experience_level": exp_level,
        "total_questions": len(questions),
        "questions": questions
    }

def evaluate_interview_answer(
    question_data: Dict[str, Any],
    candidate_answer: str,
    experience_level: str = "fresher"
) -> Dict[str, Any]:
    """
    Evaluates candidate's written or transcribed answer against key technical concepts,
    depth, structure, and gives score (out of 10), feedback, and model answer.
    """
    ans = (candidate_answer or "").strip()
    if len(ans) < 15:
        return {
            "score": 2.0,
            "badge": "Needs Elaboration",
            "badge_color": "#ef4444",
            "feedback": "Your answer is too brief. In a real technical interview, aim to explain the 'how' and 'why' behind your concepts, mentioning architectural tradeoffs or examples.",
            "strengths": ["Attempted response"],
            "missing_points": ["Technical depth and explanation of mechanisms", "Tradeoffs or examples"],
            "ideal_answer": question_data.get("ideal_answer", "")
        }

    ans_lower = ans.lower()
    key_concepts = question_data.get("key_concepts", [])
    matched_concepts = [kc for kc in key_concepts if kc in ans_lower]
    match_ratio = len(matched_concepts) / max(len(key_concepts), 1)

    # Base score on concept matching & length
    word_count = len(ans.split())
    length_bonus = min(word_count / 80.0, 1.0) * 2.5
    concept_score = match_ratio * 6.5
    
    # Experience penalty/leniency
    raw_score = concept_score + length_bonus
    if experience_level == "fresher":
        raw_score += 1.0 # slightly more lenient for freshers

    final_score = round(max(min(raw_score, 10.0), 3.0), 1)

    # Formulate strengths & missing points
    strengths = []
    missing_points = []

    if matched_concepts:
        strengths.append(f"Accurately mentioned core concepts: {', '.join(matched_concepts[:3])}")
    if word_count > 60:
        strengths.append("Provided detailed context and structural reasoning.")
    else:
        missing_points.append("Could expand more on internal architecture or real-world tradeoffs.")

    unmatched = [kc for kc in key_concepts if kc not in ans_lower]
    if unmatched:
        missing_points.append(f"Consider touching on: {', '.join(unmatched[:3])}")

    if final_score >= 8.0:
        badge = "🌟 Strong Hire"
        badge_color = "#10b981"
        feedback = "Excellent answer! You demonstrated solid technical command, accurate terminology, and clear reasoning that interviewers look for."
    elif final_score >= 6.0:
        badge = "👍 Good Attempt"
        badge_color = "#0284c7"
        feedback = "Solid foundation. You have the right intuition; enriching your answer with edge-case considerations or specific metric tradeoffs will make it an interview-topper."
    else:
        badge = "⚠️ Needs Polish"
        badge_color = "#f59e0b"
        feedback = "Fair start, but missing key underlying mechanisms. Review the ideal model answer below to study the terminology and architectural depth expected."

    return {
        "score": final_score,
        "badge": badge,
        "badge_color": badge_color,
        "feedback": feedback,
        "strengths": strengths if strengths else ["Addressed the prompt directly."],
        "missing_points": missing_points if missing_points else ["No major gaps found!"],
        "ideal_answer": question_data.get("ideal_answer", "")
    }
