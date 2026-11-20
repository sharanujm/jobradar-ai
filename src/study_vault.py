import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Any

from src.database import get_connection, DB_PATH

RESOURCES_DIR = Path(__file__).resolve().parent.parent / "data" / "resources"
RESOURCES_DIR.mkdir(parents=True, exist_ok=True)

CURATED_PRELOADED_RESOURCES = [
    {
        "title": "Top 100 SDE Technical Interview Questions & Core Concepts",
        "category": "CS Fundamentals",
        "resource_type": "guide",
        "description": "Essential interview revision covering OOP, OS, DBMS, Computer Networks & System Architecture for software roles.",
        "tags": ["OOP", "DBMS", "OS", "Networks", "Interview"],
        "content_text": """# Top 100 SDE Technical Interview Guide

## 1. Object-Oriented Programming (OOP)
- **Encapsulation**: Bundling data with methods operating on that data; hiding internal state.
- **Abstraction**: Showing essential features and hiding background implementation details.
- **Inheritance**: Deriving new classes from existing ones (code reusability).
- **Polymorphism**: Compile-time (Method Overloading) vs Runtime (Method Overriding).
- **SOLID Principles**:
  - **S**: Single Responsibility Principle
  - **O**: Open/Closed Principle (Open for extension, closed for modification)
  - **L**: Liskov Substitution Principle
  - **I**: Interface Segregation Principle
  - **D**: Dependency Inversion Principle

## 2. Database Management Systems (DBMS)
- **ACID Properties**:
  - **Atomicity**: All or nothing transaction execution.
  - **Consistency**: Database preserves integrity constraints before & after.
  - **Isolation**: Concurrent transactions do not interfere with each other.
  - **Durability**: Committed data is permanently saved even during power failure.
- **Indexing**: B-Tree and Hash Indexing to speed up read queries at the cost of slower writes.
- **Normalization**: Eliminating data redundancy (1NF, 2NF, 3NF, BCNF).
- **Primary Key vs Foreign Key vs Unique Key**:
  - Primary Key: Unique, cannot be NULL.
  - Unique Key: Unique, allows at most one NULL.
  - Foreign Key: Refers to the Primary Key of another table.

## 3. Operating Systems (OS)
- **Process vs Thread**:
  - Process: Program in execution with its own dedicated memory space (Stack, Heap, Data, Code).
  - Thread: Lightweight unit of execution within a process, sharing heap and address space.
- **Deadlock Conditions (Coffman Conditions)**:
  1. Mutual Exclusion
  2. Hold and Wait
  3. No Preemption
  4. Circular Wait
- **Virtual Memory & Paging**:
  - Allows OS to execute processes larger than physical RAM by paging between RAM and disk swap space.

## 4. Computer Networks (CN)
- **TCP vs UDP**:
  - TCP: Connection-oriented, reliable, ordered, error-checked, slower (e.g. HTTP, Email, SSH).
  - UDP: Connectionless, fast, no delivery guarantee (e.g. Video streaming, DNS, VoIP, Online gaming).
- **What happens when you type google.com into your browser?**:
  1. Browser checks cache (DNS cache in browser, OS, router).
  2. DNS resolution queries recursive resolver -> Root server -> TLD server -> Authoritative server.
  3. TCP 3-way handshake established (SYN -> SYN-ACK -> ACK).
  4. TLS/SSL handshake negotiates encryption keys.
  5. HTTP GET request sent.
  6. Server responds with HTML/CSS/JS assets.
  7. Browser DOM tree built and painted.
"""
    },
    {
        "title": "Ultimate 14 Algorithmic Patterns & DSA Cheat Sheet",
        "category": "DSA & Coding",
        "resource_type": "cheatsheet",
        "description": "Master the 14 core patterns used in 95% of LeetCode & Coding Round questions.",
        "tags": ["DSA", "LeetCode", "Algorithms", "Coding Round"],
        "content_text": """# 14 Algorithmic Patterns for Technical Rounds

1. **Two Pointers**: Used when input is sorted array or LinkedList. Finding pairs that sum to target, removing duplicates.
   - Time: O(N), Space: O(1)
2. **Sliding Window**: Subarrays or substrings with a given property (e.g., maximum sum subarray of size K, longest substring with distinct characters).
   - Time: O(N)
3. **Fast & Slow Pointers (Floyd's Tortoise & Hare)**: Cycle detection in LinkedList, finding middle node, palindrome check.
4. **Merge Intervals**: Overlapping interval problems (Meeting rooms, scheduling conflicts).
   - Tip: Sort intervals by start time first!
5. **Cyclic Sort**: Finding missing or duplicate numbers in array with numbers in range [1, N].
   - Time: O(N), Space: O(1)
6. **In-place Reversal of a LinkedList**: Reverse LinkedList or sub-segment without extra space.
7. **Tree BFS (Breadth-First Search)**: Level-order traversal using a Queue (`collections.deque`).
8. **Tree DFS (Depth-First Search)**: Pre-order, In-order, Post-order traversal using Recursion/Stack.
9. **Two Heaps**: Finding median in a dynamic data stream using a Max-Heap for small half and Min-Heap for large half.
10. **Subsets & Permutations**: Backtracking algorithms to generate combinations, phone keypad, subset sums.
11. **Modified Binary Search**: Searching in rotated sorted array, peak element, search range.
12. **Top 'K' Elements**: Using a Min-Heap of size K to find K largest elements in O(N log K) time.
13. **K-way Merge**: Merging K sorted lists or arrays using a PriorityQueue.
14. **0/1 Knapsack & Dynamic Programming**: Memoization (Top-down) and Tabulation (Bottom-up) for optimization problems.
"""
    },
    {
        "title": "HR & Behavioral STAR Method Answer Framework Guide",
        "category": "HR & Behavioral",
        "resource_type": "guide",
        "description": "How to answer situational and behavioral questions with winning structure and metrics.",
        "tags": ["HR Round", "Behavioral", "STAR Method", "Interview Tips"],
        "content_text": """# Cracking the Behavioral & HR Interview (STAR Method)

## The STAR Framework:
- **S - Situation**: Set the scene. Context, company, project, or problem (15% of answer).
- **T - Task**: What was your specific responsibility or challenge? (15% of answer).
- **A - Action**: What concrete steps did YOU take? Tools, teamwork, leadership (50% of answer).
- **R - Result**: What was the outcome? Use quantifiable metrics! (20% of answer).

---

## 3 Core Behavioral Questions & Winning Answers

### Question 1: "Tell me about a difficult technical bug you solved."
- **Situation**: During my final-year project, our React frontend kept desyncing with the FastAPI backend under rapid state updates.
- **Task**: I needed to fix race conditions without degrading user experience or slowing down the API.
- **Action**: I used browser DevTools performance profiling to identify unbatched network requests. I implemented debouncing on inputs, added request cancellation tokens using AbortController, and cached frequent queries in localStorage.
- **Result**: Reduced redundant API calls by 70% and eliminated UI freeze, ensuring smooth 60fps interaction.

### Question 2: "Describe a situation where you had a disagreement with a team member."
- **Situation**: In a hackathon, a teammate wanted to use MongoDB while I advocated for PostgreSQL.
- **Task**: We had only 24 hours and needed to decide on an architecture without delaying development.
- **Action**: Instead of debating opinions, I listed our schema requirements: we had relational data (users, jobs, applications) requiring strict foreign keys. I demonstrated how PostgreSQL prevented corrupt relationships while offering JSONB for flexibility.
- **Result**: The team agreed on PostgreSQL, and having relational integrity allowed us to build the analytics dashboard in half the time without data bugs.

### Question 3: "Why should we hire you as a fresher over other candidates?"
- **Structure**:
  1. Highlight hands-on project experience with their specific stack.
  2. Prove quick learning agility with examples.
  3. Show genuine enthusiasm for their domain and continuous delivery mindset.
"""
    },
    {
        "title": "Top 50 Most-Asked SQL Queries for Developer Interviews",
        "category": "Databases & SQL",
        "resource_type": "cheatsheet",
        "description": "Master window functions, CTEs, self joins, second-highest salary, and duplicate queries.",
        "tags": ["SQL", "Queries", "Window Functions", "Database"],
        "content_text": """# Top SQL Query Interview Practice Sheet

## 1. N-th Highest Salary (Using Window Function)
```sql
SELECT salary FROM (
    SELECT salary, DENSE_RANK() OVER (ORDER BY salary DESC) as rnk
    FROM employees
) ranked
WHERE rnk = 2; -- 2nd highest salary
```

## 2. Find Duplicate Records in a Table
```sql
SELECT email, COUNT(*) as count
FROM users
GROUP BY email
HAVING COUNT(*) > 1;
```

## 3. Delete Duplicate Records Keeping Lowest ID
```sql
DELETE FROM users 
WHERE id NOT IN (
    SELECT MIN(id) 
    FROM users 
    GROUP BY email
);
```

## 4. Manager-Employee Hierarchy (Self Join)
```sql
SELECT e.name AS Employee, m.name AS Manager
FROM employees e
LEFT JOIN employees m ON e.manager_id = m.id;
```

## 5. Department-wise Highest Paid Employee
```sql
SELECT department_id, name, salary FROM (
    SELECT department_id, name, salary,
           ROW_NUMBER() OVER (PARTITION BY department_id ORDER BY salary DESC) as rank
    FROM employees
) dept_salaries
WHERE rank = 1;
```

## 6. Running Total of Sales (Cumulative Sum)
```sql
SELECT order_date, amount,
       SUM(amount) OVER (ORDER BY order_date) AS running_total
FROM sales;
```
"""
    },
    {
        "title": "System Design & Web Architecture Essentials for Freshers",
        "category": "System Design",
        "resource_type": "guide",
        "description": "Fundamental components of scalable web applications: CDNs, Caching, Load Balancers & Databases.",
        "tags": ["System Design", "Architecture", "Scalability", "Backend"],
        "content_text": """# System Design Primer for Junior Engineers

## 1. Horizontal vs Vertical Scaling
- **Vertical Scaling (Scale-Up)**: Adding more CPU/RAM to a single server. Limited by hardware ceiling, single point of failure.
- **Horizontal Scaling (Scale-Out)**: Adding more server nodes. Resilient, fault-tolerant, requires Load Balancing.

## 2. Load Balancing Algorithms
- **Round Robin**: Distributes requests sequentially.
- **Least Connections**: Sends requests to server handling fewest active connections.
- **IP Hash**: Hashes client IP to ensure same client reaches same server (session stickiness).

## 3. Caching Strategies
- **Redis / Memcached**: In-memory key-value stores.
- **Cache-Aside (Lazy Loading)**: App checks cache; if miss, loads from DB and writes to cache.
- **Write-Through**: Data written to cache and DB simultaneously.
- **Eviction Policies**: LRU (Least Recently Used), LFU (Least Frequently Used), FIFO.

## 4. SQL vs NoSQL Decisions
- Use **SQL (Relational)** when: Structured schema, ACID compliance needed, complex JOIN queries (Fintech, CRM, E-commerce orders).
- Use **NoSQL (Document/KV)** when: Unstructured or polymorphic data, massive write scale, no complex relational joins (IoT sensor telemetry, social feed streams).

## 5. Message Queues & Asynchronous Processing
- **Tools**: RabbitMQ, Kafka, Celery, Redis Queues.
- **Use Case**: Decouple slow tasks (sending emails, video transcoding, PDF parsing) from fast web request-response cycles.
"""
    },
    {
        "title": "NeetCode 150 & LeetCode Blind 75 Preparation Roadmap",
        "category": "DSA & Coding",
        "resource_type": "link",
        "url": "https://neetcode.io/roadmap",
        "description": "Interactive topic-by-topic visual roadmap to master technical coding interviews in 6-8 weeks.",
        "tags": ["Roadmap", "LeetCode", "NeetCode", "DSA Practice"],
        "content_text": "Follow the structured topic sequence: Arrays & Hashing -> Two Pointers -> Sliding Window -> Stack -> Binary Search -> Linked List -> Trees -> Tries -> Heap -> Backtracking -> Graphs -> 1D DP -> 2D DP."
    }
]

def init_study_vault_db(db_path: Path = DB_PATH) -> None:
    """Creates the study_resources table and loads curated resources."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS study_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT DEFAULT '',
            title TEXT,
            category TEXT DEFAULT 'General',
            resource_type TEXT DEFAULT 'guide',
            file_path TEXT DEFAULT '',
            url TEXT DEFAULT '',
            content_text TEXT DEFAULT '',
            description TEXT DEFAULT '',
            tags TEXT DEFAULT '[]',
            is_completed INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_resources_user ON study_resources(user_email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_resources_cat ON study_resources(category)")

    # Pre-populate starter resources if none exist
    cursor.execute("SELECT COUNT(*) FROM study_resources WHERE user_email = ''")
    count = cursor.fetchone()[0]

    if count == 0:
        for res in CURATED_PRELOADED_RESOURCES:
            cursor.execute("""
                INSERT INTO study_resources 
                (user_email, title, category, resource_type, file_path, url, content_text, description, tags, is_completed)
                VALUES ('', ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                res.get("title", "Study Resource"),
                res.get("category", "General"),
                res.get("resource_type", "guide"),
                res.get("file_path", ""),
                res.get("url", ""),
                res.get("content_text", ""),
                res.get("description", ""),
                json.dumps(res.get("tags", []))
            ))

    conn.commit()
    conn.close()

def get_resources_for_user(user_email: str = "", db_path: Path = DB_PATH) -> List[Dict[str, Any]]:
    """Fetches user uploaded resources plus curated starter resources."""
    init_study_vault_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    clean_email = (user_email or "").strip().lower()
    cursor.execute("""
        SELECT * FROM study_resources 
        WHERE user_email = '' OR user_email = ?
        ORDER BY is_completed ASC, id DESC
    """, (clean_email,))

    rows = cursor.fetchall()
    conn.close()

    results = []
    for row in rows:
        item = dict(row)
        try:
            item["tags"] = json.loads(item.get("tags") or "[]")
        except Exception:
            item["tags"] = []
        item["is_user_uploaded"] = bool(item.get("user_email"))
        results.append(item)
    return results

def add_resource(data: dict, db_path: Path = DB_PATH) -> Dict[str, Any]:
    """Adds a new study resource (file upload, link, or custom note)."""
    init_study_vault_db(db_path)
    conn = get_connection(db_path)
    cursor = conn.cursor()

    tags = data.get("tags") or []
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except Exception:
            tags = [t.strip() for t in tags.split(",") if t.strip()]

    cursor.execute("""
        INSERT INTO study_resources 
        (user_email, title, category, resource_type, file_path, url, content_text, description, tags, is_completed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (
        data.get("user_email", "").strip().lower(),
        data.get("title", "New Resource"),
        data.get("category", "General"),
        data.get("resource_type", "pdf"),
        data.get("file_path", ""),
        data.get("url", ""),
        data.get("content_text", ""),
        data.get("description", ""),
        json.dumps(tags)
    ))

    resource_id = cursor.lastrowid
    conn.commit()
    conn.close()

    data["id"] = resource_id
    data["tags"] = tags
    data["is_completed"] = 0
    return data

def toggle_resource_completion(resource_id: int, user_email: str, db_path: Path = DB_PATH) -> bool:
    """Toggles the completion status of a resource."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT is_completed FROM study_resources WHERE id = ?", (resource_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False

    next_status = 0 if row[0] == 1 else 1
    cursor.execute("UPDATE study_resources SET is_completed = ? WHERE id = ?", (next_status, resource_id))
    conn.commit()
    conn.close()
    return bool(next_status)

def delete_resource(resource_id: int, user_email: str, db_path: Path = DB_PATH) -> bool:
    """Deletes a resource if it belongs to the user or is a custom item."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT file_path FROM study_resources WHERE id = ?", (resource_id,))
    row = cursor.fetchone()
    if row and row[0]:
        try:
            fpath = Path(row[0])
            if fpath.exists() and fpath.is_file():
                fpath.unlink()
        except Exception:
            pass

    cursor.execute("DELETE FROM study_resources WHERE id = ?", (resource_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted
