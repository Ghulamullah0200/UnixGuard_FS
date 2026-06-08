# UnixGuard FS — Viva Voce Preparation Guide
# UnixGuard FS — Viva Voce Preparation Guide

This guide compiles common conceptual and implementation questions that examiners are likely to ask during the project evaluation and viva.

---

### Q1: What is the main objective of this project?
**Answer:** The objective is to build a web-based, secure educational simulator for Unix filesystem structures, access control, security auditing, and CPU scheduling. It helps students explore OS concepts in an interactive interface and sandboxed environment without risking damage to their host system.

---

### Q2: How is the Unix file system structure represented in this database?
**Answer:** We decouple filenames from metadata by using two database tables:
1.  **`inodes` table:** Stores metadata (owner, group, size, permissions, type, link count).
2.  **`filesystem_nodes` table:** Represents directory entries mapping names to parent nodes and inode records.
This separates the name of a file from its actual metadata block, which allows us to implement hard links (multiple name rows pointing to a single inode row).

---

### Q3: What is the difference between a Hard Link and a Symbolic Link in your simulator?
**Answer:** 
*   **Hard Link:** A new record in `filesystem_nodes` that points to the *same* `inode_id`. The inode's `link_count` is incremented. When you delete a hard link, the record is removed and the `link_count` decrements, but the actual inode and file data persist until `link_count` drops to 0.
*   **Symbolic (Soft) Link:** A unique inode with its type set to `symlink` and its `target_path` field containing the path to another node. It does not share the same inode. If the target file is deleted, the symlink becomes "broken," which our auditor flags.

---

### Q4: How is Unix access control computed in this application?
**Answer:** We evaluate permissions following standard Unix access resolution:
1.  **Owner Check:** If the current username matches the inode's owner, we check the owner's `rwx` permissions.
2.  **Group Check:** If the user shares a group with the file, we check the group's `rwx` permissions.
3.  **Others Check:** If the user is neither the owner nor a group member, we check the others' `rwx` permissions.
If the check succeeds, access is allowed. If not, it is denied. We also check special bits like the Sticky Bit to ensure only owners can delete files in shared directories.

---

### Q5: How does your Security Auditor implement Multi-Threading, and how is it thread-safe?
**Answer:**
*   **Concurrency:** We use Python's `ThreadPoolExecutor` from `concurrent.futures`. We break the filesystem tree into root directories (e.g. `/home`, `/etc`, `/var`, `/tmp`) and assign each directory scan task to a separate thread worker.
*   **Thread Safety:**
    1.  Each thread instantiates its own SQLAlchemy `Session` block via `SessionLocal()`, ensuring database sessions are not shared.
    2.  We use a `threading.Lock` when appending scan findings to the database to prevent write conflicts.

---

### Q6: Can you explain the scheduling algorithms demonstrated in the Scheduler module?
**Answer:**
1.  **First-Come, First-Served (FCFS):** A non-preemptive algorithm that runs jobs in order of arrival.
2.  **Priority Scheduling:** Runs arriving jobs in order of priority (lower number represents higher priority).
3.  **Round Robin (RR):** A preemptive algorithm where each job is allocated a small time slice (time quantum) in a FIFO queue. If a job is not completed within its slice, it is put at the end of the queue.

---

### Q7: Why did you use SQLite and SQLAlchemy instead of the actual OS filesystem?
**Answer:** 
1.  **Security:** Interacting with real OS system folders requires root/administrator privileges and risks accidental file deletion or privilege changes. A virtual database filesystem is completely safe.
2.  **Cross-Platform Portability:** Using SQLite ensures that the simulator runs the exact same way on Windows, macOS, and Linux without OS-specific filesystem differences.
