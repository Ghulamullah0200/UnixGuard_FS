# Course Learning Outcome (CLO) & Program Learning Outcome (PLO) Mapping

This project is structured to meet standard university assessment criteria for an undergraduate course in **Operating Systems Theory and Laboratory**.

---

## 1. Course Learning Outcomes (CLOs)

| CLO ID | CLO Description | Project Implementation Evidence |
|---|---|---|
| **CLO-1** | Explain the structure and core operations of operating system file systems, including inodes, directories, and links. | **VFS Database Mapping:** Decoupled `inodes` and `filesystem_nodes` tables showing hard link and symlink mechanics. |
| **CLO-2** | Analyze access control lists, permissions, and security configurations in multi-user systems. | **Access Resolution Engine:** Implementation of octal-to-symbolic conversions, `rwx` owner/group/other checks, SUID, SGID, and Sticky Bit verification. |
| **CLO-3** | Design and analyze concurrency and scheduling models including multi-threading, thread synchronization, and CPU scheduling. | **Multi-Threaded Auditing & CPU Scheduler:** Code executing scanning tasks concurrently using `ThreadPoolExecutor` and Gantt charts for RR, FCFS, and Priority schedulers. |
| **CLO-4** | Develop practical system simulations demonstrating theoretical concepts. | **Full Stack Web SPA:** Python backend with a custom CSS/JS UI and terminal console simulation. |

---

## 2. Program Learning Outcomes (PLOs)

| PLO ID | PLO Title | Alignment with Project |
|---|---|---|
| **PLO-1** | **Engineering Knowledge / Computing Fundamentals** | Implementation of data structure traversals (recursive file tree traversal) and core kernel algorithms (Round Robin scheduling queue management). |
| **PLO-2** | **Problem Analysis** | Automatic scanning and analysis of security risks within the virtual filesystem, categorizing them by severity (CRITICAL, HIGH, LOW). |
| **PLO-3** | **Design/Development of Solutions** | Creation of a fully-realized web simulator with REST API endpoints, mock terminal shell, and interactive permission calculators. |
| **PLO-4** | **Modern Tool Usage** | Utilizing modern web and backend development stacks (Python, FastAPI, SQLAlchemy, SQLite, Chart.js). |
| **PLO-5** | **Communication / Presentation** | Exhaustive project documentation, Viva preparation guide, and clean user manual for presentation and viva defense. |
