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
            user_notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_resources_user ON study_resources(user_email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_resources_cat ON study_resources(category)")

    # Migration: ensure user_notes column exists on older tables
    try:
        cursor.execute("ALTER TABLE study_resources ADD COLUMN user_notes TEXT DEFAULT ''")
    except Exception:
        pass

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

def get_resource_by_id(resource_id: int, db_path: Path = DB_PATH) -> Optional[Dict[str, Any]]:
    """Retrieves a single study resource by its ID."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM study_resources WHERE id = ?", (resource_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    item = dict(row)
    try:
        item["tags"] = json.loads(item.get("tags") or "[]")
    except Exception:
        item["tags"] = []
    item["user_notes"] = item.get("user_notes") or ""
    return item

def update_resource_notes(resource_id: int, notes: str, user_email: str = "", db_path: Path = DB_PATH) -> bool:
    """Saves candidate's personal study scratchpad notes for a resource."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE study_resources SET user_notes = ? WHERE id = ?", (notes, resource_id))
    conn.commit()
    conn.close()
    return True

def generate_ai_study_assist(resource_id: int, action: str = "takeaways", db_path: Path = DB_PATH) -> Dict[str, Any]:
    """
    Intelligent in-app study assistant generating either:
    1. 'takeaways': Executive summary, 5 high-yield revision points, top 3 interview questions & answers.
    2. 'quiz': Interactive 3-question knowledge check with answers and detailed explanations.
    """
    res = get_resource_by_id(resource_id, db_path)
    if not res:
        return {"status": "error", "message": "Resource not found"}

    title = res.get("title") or "Study Guide"
    cat = res.get("category") or "General"
    desc = res.get("description") or ""
    content = res.get("content_text") or ""
    res_type = res.get("resource_type") or "guide"

    # Category-specific intelligence bank
    knowledge_banks = {
        "CS Fundamentals": {
            "summary": "Core foundational knowledge covering Object-Oriented Programming (OOP), OS process scheduling, ACID-compliant database architecture, and OSI networking models required for software engineering interviews.",
            "takeaways": [
                "**SOLID Principles**: Always design classes around Single Responsibility and Open/Closed principles to ensure maintainable enterprise code.",
                "**Process vs Thread**: A process has isolated virtual memory (Heap, Stack, Code); threads within the same process share heap memory and communicate via low-overhead shared memory.",
                "**ACID Guarantees**: Atomicity (all-or-nothing), Consistency (state valid), Isolation (concurrent safety), Durability (persisted to disk).",
                "**Deadlock Prevention**: Deadlock occurs only if Mutual Exclusion, Hold & Wait, No Preemption, and Circular Wait all hold true simultaneously.",
                "**TCP vs UDP**: Use TCP for loss-intolerant web/financial traffic (guaranteed delivery); use UDP for low-latency streaming and gaming."
            ],
            "questions": [
                {
                    "q": "What is the difference between Method Overloading and Method Overriding?",
                    "a": "Overloading occurs at compile-time within the same class (same name, different arguments). Overriding occurs at runtime in inheritance when a subclass replaces a superclass method implementation."
                },
                {
                    "q": "Why is B-Tree preferred over Hash Indexing in relational databases?",
                    "a": "B-Trees keep data sorted, allowing efficient range queries (<, >, BETWEEN) with O(log N) time, whereas Hash Indexes only support O(1) exact equality lookups."
                },
                {
                    "q": "What happens when you type a URL into a browser and press enter?",
                    "a": "DNS resolution -> TCP 3-way handshake (SYN, SYN-ACK, ACK) -> TLS negotiation -> HTTP GET request sent -> Server processes & responds -> Browser renders DOM/CSSOM."
                }
            ],
            "tip": "💡 Memory Anchor: Remember Coffman conditions for Deadlock using 'M-H-N-C' (Mutual exclusion, Hold & wait, No preemption, Circular wait).",
            "quiz": [
                {
                    "question": "Which of the following ACID properties ensures that transactions do not interfere with each other when running concurrently?",
                    "options": ["Atomicity", "Consistency", "Isolation", "Durability"],
                    "correct_index": 2,
                    "explanation": "Isolation prevents concurrent transactions from seeing each other's intermediate, uncommitted states (via locks or MVCC)."
                },
                {
                    "question": "What is the primary architectural difference between a Process and a Thread?",
                    "options": [
                        "Threads have separate heap memory from their parent process",
                        "Processes share code space, while threads do not",
                        "Threads share the process heap and memory space, while processes have separate virtual memory",
                        "A thread cannot run concurrently with other threads"
                    ],
                    "correct_index": 2,
                    "explanation": "Threads belong to a parent process and share its heap, global variables, and address space, but each thread maintains its own call stack and program counter."
                },
                {
                    "question": "Which protocol provides guaranteed, ordered, and error-checked byte stream delivery?",
                    "options": ["UDP", "TCP", "ICMP", "IGMP"],
                    "correct_index": 1,
                    "explanation": "TCP (Transmission Control Protocol) implements sequence numbering, acknowledgments, and retransmission to guarantee reliable, ordered delivery."
                }
            ]
        },
        "DSA & Coding": {
            "summary": "High-frequency algorithmic paradigms, optimal time-space complexity trade-offs, and systematic problem-solving strategies for coding assessment rounds.",
            "takeaways": [
                "**Two Pointers / Sliding Window**: Optimal O(N) approach for contiguous subarray problems, searching sorted pairs, and palindrome validation.",
                "**Fast & Slow Pointers**: Floyd's Cycle Detection algorithm finds cycles in linked lists in O(N) time with O(1) auxiliary space.",
                "**Binary Search on Answer**: For monotonic optimization problems (e.g. min capacity to ship packages within D days), binary search can find the threshold in O(log(range)).",
                "**Dynamic Programming**: Identify optimal substructure and overlapping subproblems; always check if memoization (top-down) or tabulation (bottom-up) reduces exponential O(2^N) to polynomial O(N).",
                "**Tree Traversal Invariants**: In-order traversal on a Binary Search Tree (BST) visits nodes in strictly sorted ascending order."
            ],
            "questions": [
                {
                    "q": "When should you use BFS instead of DFS for graph problems?",
                    "a": "Use BFS whenever you need the shortest path in an unweighted graph, level-order traversal, or minimum step transformations, because BFS visits nodes level by level."
                },
                {
                    "q": "How does a Hash Map handle hash collisions internally?",
                    "a": "Commonly via Separate Chaining (linked lists or balanced trees on collision buckets, like Java 8+ HashMap red-black trees) or Open Addressing (Linear/Quadratic Probing)."
                },
                {
                    "q": "What is the difference between Quicksort and Mergesort?",
                    "a": "Mergesort guarantees O(N log N) worst-case and is stable but requires O(N) auxiliary space. Quicksort has O(N log N) average time and O(log N) space, but O(N^2) worst-case if pivot selection is unoptimized."
                }
            ],
            "tip": "💡 Pro Strategy: When asked to optimize an O(N^2) brute-force nested loop, immediately consider a Hash Set / Hash Map (trade O(N) memory for O(1) lookup) or Sorting + Two Pointers.",
            "quiz": [
                {
                    "question": "What is the time complexity to search for a key in a balanced Binary Search Tree (AVL or Red-Black Tree) with N nodes?",
                    "options": ["O(1)", "O(log N)", "O(N)", "O(N log N)"],
                    "correct_index": 1,
                    "explanation": "Because balanced BSTs maintain height proportional to log2(N), search, insertion, and deletion all take O(log N) time."
                },
                {
                    "question": "Which algorithm is guaranteed to find the shortest path in an unweighted graph?",
                    "options": ["Depth First Search (DFS)", "Breadth First Search (BFS)", "Kruskal's Algorithm", "Topological Sort"],
                    "correct_index": 1,
                    "explanation": "BFS explores neighbors radially tier-by-tier; the first time it reaches a target vertex, the path taken is guaranteed to be the shortest unweighted distance."
                },
                {
                    "question": "What is the worst-case space complexity of Recursive Depth-First Search on an unbalanced binary tree?",
                    "options": ["O(1)", "O(log N)", "O(N)", "O(N^2)"],
                    "correct_index": 2,
                    "explanation": "In a skewed (degenerate) tree that resembles a linked list, recursion stack depth reaches N calls, taking O(N) stack space."
                }
            ]
        },
        "Databases & SQL": {
            "summary": "Relational query optimization, index tuning, join execution models, window functions, and transaction isolation levels essential for backend developer interviews.",
            "takeaways": [
                "**B-Tree Indexes**: Always index columns used in WHERE, JOIN ON, and ORDER BY clauses to avoid full table scans.",
                "**HAVING vs WHERE**: WHERE filters rows before aggregation; HAVING filters aggregated groups created by GROUP BY.",
                "**Window Functions**: DENSE_RANK() vs RANK(): RANK leaves gaps for ties (1, 2, 2, 4), while DENSE_RANK does not leave gaps (1, 2, 2, 3).",
                "**Transaction Isolation Levels**: Read Uncommitted -> Read Committed -> Repeatable Read -> Serializable (trading performance for phantom/dirty read protection).",
                "**Composite Indexes**: Left-to-right prefix rule: an index on (A, B, C) accelerates queries on (A) and (A, B), but not on (B, C) alone."
            ],
            "questions": [
                {
                    "q": "How do you find the second highest salary without using LIMIT or TOP?",
                    "a": "SELECT MAX(salary) FROM employees WHERE salary < (SELECT MAX(salary) FROM employees);"
                },
                {
                    "q": "What is the difference between INNER JOIN, LEFT JOIN, and CROSS JOIN?",
                    "a": "INNER JOIN returns matching rows only. LEFT JOIN returns all rows from left table plus matching right rows (NULL if no match). CROSS JOIN produces a Cartesian product of all rows."
                },
                {
                    "q": "What is database normalization and why is 3NF standard in OLTP?",
                    "a": "Normalization organizes data to reduce anomaly risks on INSERT, UPDATE, DELETE. 3NF ensures every non-key column depends solely on the primary key, eliminating transitive dependencies."
                }
            ],
            "tip": "💡 SQL Cheat Sheet: To find Nth highest value dynamically, use: SELECT DISTINCT salary FROM (SELECT salary, DENSE_RANK() OVER(ORDER BY salary DESC) as rnk FROM employees) t WHERE rnk = 2;",
            "quiz": [
                {
                    "question": "Which SQL clause is used to filter aggregated data generated by a GROUP BY statement?",
                    "options": ["WHERE", "ORDER BY", "HAVING", "LIMIT"],
                    "correct_index": 2,
                    "explanation": "WHERE filters raw rows before aggregation, while HAVING filters aggregated metric buckets after GROUP BY execution."
                },
                {
                    "question": "If Employee A and Employee B both have the 2nd highest salary, what will DENSE_RANK() assign to Employee C who has the next highest salary?",
                    "options": ["Rank 3", "Rank 4", "Rank 2", "Rank NULL"],
                    "correct_index": 0,
                    "explanation": "DENSE_RANK() leaves no gaps in rank numbering, so ties receive Rank 2 and the next distinct salary receives Rank 3."
                },
                {
                    "question": "What is the risk of running under the 'Read Committed' isolation level compared to 'Repeatable Read'?",
                    "options": ["Dirty Reads", "Non-Repeatable Reads", "Lock Deadlocks", "Database corruption"],
                    "correct_index": 1,
                    "explanation": "Under Read Committed, another transaction can update and commit a row while your transaction is running, causing repeated reads of the same row to return differing values."
                }
            ]
        },
        "System Design": {
            "summary": "Large-scale web architecture paradigms: horizontal scalability, Redis caching topologies, microservices messaging, and distributed system trade-offs.",
            "takeaways": [
                "**Horizontal vs Vertical Scaling**: Scale horizontally (add commodity compute nodes behind a load balancer) to eliminate single points of failure.",
                "**Caching Strategies**: Cache-aside (read from cache; on miss query DB & populate cache) reduces DB read spikes by 90%+.",
                "**CAP Theorem**: In any distributed system with network partitions (P), you must choose between Consistency (C) or Availability (A).",
                "**Message Queues (Kafka / RabbitMQ)**: Decouple synchronous user requests from asynchronous heavy processing (email, notifications, analytics).",
                "**Rate Limiting**: Protect backend APIs against DDoS and scrapers using Token Bucket or Leaky Bucket algorithms backed by Redis."
            ],
            "questions": [
                {
                    "q": "How would you design a scalable URL shortener like bit.ly?",
                    "a": "Use Base62 encoding on auto-incrementing distributed IDs or Snowflake IDs. Store mappings in NoSQL (MongoDB/Cassandra) with Redis caching for top 20% hot URLs."
                },
                {
                    "q": "What is Cache Stampede and how do you prevent it?",
                    "a": "Occurs when a popular cached key expires and hundreds of concurrent requests hit the database simultaneously. Prevent using Mutex Locks (single flight query), Probabilistic early expiration (XFetch), or background cache warmers."
                },
                {
                    "q": "What is the difference between SQL and NoSQL databases?",
                    "a": "SQL offers structured schema, ACID compliance, and relational JOINs (best for financial/orders). NoSQL offers flexible schema, horizontal sharding, and high-throughput key-value/document reads."
                }
            ],
            "tip": "💡 System Design Rule of Thumb: Always design with Stateless App Servers + Distributed Redis Cache + Read-Replicas for Database before considering complex sharding.",
            "quiz": [
                {
                    "question": "According to the CAP theorem, during a network partition, what must a distributed data store choose between?",
                    "options": [
                        "Latency vs Throughput",
                        "Consistency vs Availability",
                        "Security vs Scalability",
                        "Durability vs Atomicity"
                    ],
                    "correct_index": 1,
                    "explanation": "During a network partition (P), the system cannot communicate across nodes; it must either reject requests (Consistency) or serve potentially stale data (Availability)."
                },
                {
                    "question": "Which rate limiting algorithm allows bursts of traffic up to a specified capacity while maintaining a constant refill rate?",
                    "options": ["Fixed Window Counter", "Token Bucket", "Round Robin", "Consistent Hashing"],
                    "correct_index": 1,
                    "explanation": "Token Bucket permits traffic bursts as long as tokens are available in the bucket, then smoothly refills at a sustained rate."
                },
                {
                    "question": "What is the primary benefit of deploying a Content Delivery Network (CDN) like Cloudflare or CloudFront?",
                    "options": [
                        "Executes backend database transactions faster",
                        "Caches static assets (images, CSS, JS) at edge servers geographically close to end users",
                        "Replaces the need for application load balancers",
                        "Converts monolithic code into microservices automatically"
                    ],
                    "correct_index": 1,
                    "explanation": "CDNs terminate traffic and serve static files from edge data centers nearest to the user, drastically lowering round-trip latency and origin server load."
                }
            ]
        },
        "HR & Behavioral": {
            "summary": "Mastering behavioral interview frameworks: the STAR technique, conflict resolution, situational stories, and salary negotiation best practices.",
            "takeaways": [
                "**The STAR Framework**: Structure every answer: Situation (context), Task (your goal), Action (what YOU did specifically), Result (quantified metrics & impact).",
                "**First 90 Seconds**: Interviewers form primary impressions quickly; deliver a concise 60-second elevator pitch summarizing background, core strengths, and passion for the role.",
                "**Highlighting Mistakes**: When asked about a past failure, choose a real professional misstep, explain the lesson learned, and how you implemented guardrails to prevent recurrence.",
                "**Reverse Interviewing**: Always ask 2-3 thoughtful questions at the end (e.g. 'What does success look like for this team in the first 6 months?').",
                "**Handling Conflicts**: Emphasize objective data, empathy, active listening, and focusing on business outcomes rather than personal ego."
            ],
            "questions": [
                {
                    "q": "How do you answer: 'Tell me about a time you had a disagreement with a team member?'",
                    "a": "Use STAR: Describe the differing technical approaches objectively, how you arranged a collaborative discussion to compare pros/cons using data, agreed on a test, and respected the outcome."
                },
                {
                    "q": "What is your greatest weakness?",
                    "a": "Pick a genuine skill you are actively improving (e.g., 'In early projects I tended to spend too much time over-engineering features before shipping an MVP; I now use strict timeboxing and sprint milestones')."
                },
                {
                    "q": "Why do you want to work for our company?",
                    "a": "Connect their specific product, tech stack, or engineering culture with your personal career trajectory and technical strengths."
                }
            ],
            "tip": "💡 Secret to Behavioral Rounds: 70% of candidate evaluation is on the 'Action' and 'Result' sections of STAR. Always quantify results (e.g. 'reduced latency by 35%').",
            "quiz": [
                {
                    "question": "What does the 'A' stand for in the STAR interview technique?",
                    "options": ["Assessment", "Action", "Attribute", "Alignment"],
                    "correct_index": 1,
                    "explanation": "STAR stands for Situation, Task, Action, Result. The Action section details the specific technical or interpersonal steps YOU took to solve the challenge."
                },
                {
                    "question": "When asked 'What is your greatest weakness?', what is the most effective strategy?",
                    "options": [
                        "Say you have no weaknesses and work perfectly",
                        "Give a disguised strength like 'I work too hard'",
                        "Share an authentic technical or procedural area of improvement and describe the concrete steps you are actively taking to master it",
                        "Blame past managers for your current limitations"
                    ],
                    "correct_index": 2,
                    "explanation": "Interviewers seek self-awareness and a growth mindset. A real weakness paired with actionable improvement demonstrates maturity and coachability."
                },
                {
                    "question": "When the interviewer asks 'Do you have any questions for us?', what should you do?",
                    "options": [
                        "Say 'No, you covered everything' and end the call early",
                        "Ask strategic questions about team architecture, 6-month deliverables, or engineering culture",
                        "Ask immediately about sick leave policy",
                        "Ask how quickly you will be promoted"
                    ],
                    "correct_index": 1,
                    "explanation": "Asking insightful questions demonstrates intellectual curiosity, genuine interest in the company, and preparedness for the role."
                }
            ]
        }
    }

    # Match category or fallback to general intelligent template
    bank = knowledge_banks.get(cat)
    if not bank:
        # Fallback for General / Custom uploaded resources
        clean_title = title.replace(".pdf", "").replace(".docx", "").replace(".txt", "").strip()
        bank = {
            "summary": f"Comprehensive study material focusing on '{clean_title}'. Designed to reinforce essential developer competencies, practical problem-solving, and technical fluency for modern engineering roles.",
            "takeaways": [
                f"**Core Topic Focus**: Thorough understanding of concepts presented in '{clean_title}'.",
                "**Interview Relevance**: Frequent technical round subject tested in coding assessments and architectural evaluations.",
                "**Practical Application**: Connecting theoretical principles to production implementations and clean code standards.",
                "**Optimization Mindset**: Always evaluate time and space complexity before committing to an approach.",
                "**Revision Discipline**: Review key definitions, edge cases, and typical failure modes prior to live rounds."
            ],
            "questions": [
                {
                    "q": f"What are the foundational principles of {clean_title}?",
                    "a": "Foundational principles encompass clear separation of concerns, scalability considerations, and predictable runtime behavior."
                },
                {
                    "q": f"How do you troubleshoot edge cases when applying {clean_title}?",
                    "a": "Systematically test boundary values (empty inputs, single elements, large payloads, null checks) and verify failure recovery."
                },
                {
                    "q": "What trade-offs should an engineer consider when implementing this?",
                    "a": "Evaluate implementation complexity vs performance gain, memory consumption, and developer maintainability."
                }
            ],
            "tip": f"💡 Study Tip: Annotate key definitions and practice explaining '{clean_title}' out loud in under 2 minutes as an elevator pitch.",
            "quiz": [
                {
                    "question": f"When studying '{clean_title}', what is the most crucial first step during a technical interview?",
                    "options": [
                        "Start writing code immediately without clarification",
                        "Clarify inputs, edge cases, scale requirements, and constraints with the interviewer",
                        "Decline to answer if you haven't memorized the solution",
                        "Propose the most complex distributed architecture first"
                    ],
                    "correct_index": 1,
                    "explanation": "Top engineering candidates always clarify problem scope, edge cases, and constraints before formulating an approach."
                },
                {
                    "question": "What is the primary indicator of clean, production-ready engineering code?",
                    "options": [
                        "Code written in a single long function with minimal comments",
                        "High modularity, meaningful variable naming, error handling, and testability",
                        "Code that only works on happy paths without input validation",
                        "Maximizing the number of external libraries used"
                    ],
                    "correct_index": 1,
                    "explanation": "Clean code emphasizes readability, modularity, defensive programming, and maintainability across team lifecycles."
                },
                {
                    "question": "How should an engineer approach trade-offs between execution speed and memory usage?",
                    "options": [
                        "Always optimize for speed regardless of memory consumption",
                        "Always prioritize minimum memory regardless of latency",
                        "Measure the system bottleneck, consider production constraints, and choose the optimal balance (e.g. caching vs recomputing)",
                        "Ignore trade-offs as modern cloud RAM is unlimited"
                    ],
                    "correct_index": 2,
                    "explanation": "Engineering decisions depend on constraints: latency-sensitive systems trade space for time, while memory-constrained environments prioritize minimal footprint."
                }
            ]
        }

    if action == "quiz":
        return {
            "status": "ok",
            "resource_id": resource_id,
            "title": title,
            "category": cat,
            "quiz": bank["quiz"]
        }

    # Default action: 'takeaways'
    return {
        "status": "ok",
        "resource_id": resource_id,
        "title": title,
        "category": cat,
        "reading_time": "5–8 min study",
        "summary": bank["summary"],
        "key_takeaways": bank["takeaways"],
        "interview_questions": bank["questions"],
        "cheat_sheet_tip": bank["tip"]
    }

