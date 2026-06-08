# UnixGuard FS — Web-Based Unix File System Simulator & Security Auditor
## University Operating Systems Course Project Report

---

### 1. Abstract
In modern operating systems education, translating abstract concepts such as inodes, directory structures, access control lists, multi-threaded task execution, and CPU scheduling into tangible student experiences is a persistent challenge. Traditional Unix servers present a steep learning curve and risk accidental host damage if students experiment with destructive commands or insecure permissions. 

**UnixGuard FS** is an educational, web-based Unix File System Simulator and Security Auditor designed to solve this problem. Built using Python, FastAPI, and SQLAlchemy (SQLite), it offers an isolated, visual environment where students can explore:
- Virtual Inode structures, hard links, and symbolic links.
- Unix octal and symbolic permission modes (including special bits like SUID, SGID, and Sticky Bit).
- Real-time Unix access-control resolution (Owner, Group, Others).
- Multi-threaded security vulnerability scans using a ThreadPoolExecutor.
- Educational CPU scheduling simulations (FCFS, Round Robin, and Priority) visualized with Gantt charts.

This project delivers a safe, high-fidelity environment that helps students visualize core OS principles, run security audits, and execute Unix commands via a terminal simulator, without risk to the host system.

---

### 2. Introduction & Problem Statement
Operating systems manage files, access rights, processes, and CPU time. However, learning these concepts through text commands can be abstract. Students often struggle to visualize:
1. **Inodes & Hard Links:** How multiple directory entries (filenames) point to the same physical metadata block (inode), and how deleting one name does not delete the data if other links exist.
2. **Access Control Resolution:** The exact bitwise comparison logic used by the kernel when a user attempts to read, write, or execute a file.
3. **Vulnerability Mechanics:** How weak permissions (like world-writable directories lacking the Sticky Bit) enable security exploits.
4. **Concurrency and Scheduling:** How multi-threaded workers run parallel scans, and how scheduling algorithms allocate CPU bursts.

**UnixGuard FS** addresses these pain points by simulating a full Unix filesystem in an SQL database, layering a real-time visual web interface and terminal console on top. It helps students connect theory to practice while keeping the code clean enough for academic defense (viva).

---

### 3. System Requirements & Specifications

#### 3.1 Functional Requirements
*   **Virtual File System (VFS):** Inode management, directory tree creation, file creation, hard links, symbolic links (including broken link detection).
*   **Access Control Engine:** Verification of `rwx` permissions, SUID/SGID execution context, and Sticky Bit deletion constraints.
*   **Interactive Terminal:** Support for standard commands (`ls`, `cd`, `chmod`, `ln`, `cat`, `touch`, `mkdir`, `rm`, `stat`, `whoami`, `tree`).
*   **Security Auditor:** Automated detection of world-writable files, root-owned SUIDs, broken symlinks, and unprotected private files.
*   **CPU Scheduler:** Execution of FCFS, Round Robin, and Priority Scheduling algorithms on dummy system jobs.
*   **Responsive UI:** Interactive visual file tree, permission calculator, terminal panel, and live charts.

#### 3.2 Non-Functional Requirements
*   **Security:** Sandboxed filesystem—absolutely no interaction with the host operating system's files or shell processes.
*   **Concurrency:** Audit scanning must use native Python threading (`ThreadPoolExecutor`) with thread-safe database connection handling.
*   **Compatibility:** Cross-platform support (Windows/macOS/Linux) via standard Python execution.

---

### 4. System Architecture & Database Design

#### 4.1 SQLite Inode Schema
The simulated Unix filesystem is represented in SQLite. Inodes are decoupled from names to support hard links:

1. **`inodes` Table:**
   - `id` (INTEGER, Primary Key)
   - `inode_number` (INTEGER, Unique)
   - `node_type` (VARCHAR: file, directory, symlink)
   - `size_bytes` (INTEGER)
   - `permissions_octal` (VARCHAR)
   - `owner_username` (VARCHAR)
   - `group_name` (VARCHAR)
   - `link_count` (INTEGER)
   - `target_path` (VARCHAR, for symlinks)
   - Timestamps (`created_at`, `modified_at`, `accessed_at`)

2. **`filesystem_nodes` Table (Directory Entries):**
   - `id` (INTEGER, Primary Key)
   - `name` (VARCHAR)
   - `parent_id` (INTEGER, Self-Referential FK)
   - `inode_id` (INTEGER, FK to `inodes`)

This decoupling ensures that multiple entries in `filesystem_nodes` can point to the same `inode_id` (simulating hard links).

---

### 5. Core Modules Implementation Analysis

#### 5.1 Access-Control Resolution
The access evaluation mimics standard Unix kernel logic:
1. **User Check:** If `current_user == owner`, check the owner's `rwx` bits.
2. **Group Check:** If `current_user` is in the file's group, check the group's `rwx` bits.
3. **Others Check:** Otherwise, check the others' `rwx` bits.
4. **Special Flags:** SUID execution runs as owner, Sticky Bit limits file deletion in directories to the owner.

#### 5.2 Multi-Threaded Security Scan
The Security Auditor utilizes Python's `concurrent.futures.ThreadPoolExecutor` to scan separate branches of the file tree concurrently. To make this thread-safe:
*   Each thread uses its own SQLAlchemy database session.
*   A `threading.Lock` coordinates safe write operations to the database when inserting findings.
*   Scan progress and thread IDs are logged in the `scan_tasks` table to show concurrency allocations.

#### 5.3 CPU Scheduler Module
Demonstrates CPU scheduling algorithms by simulating execution of process queues:
*   **FCFS:** Non-preemptive execution in arrival order.
*   **Priority:** Execution ordered by process priority level.
*   **Round Robin:** Time-sliced queue scheduling using time quantum intervals.
Provides average waiting times, turnaround times, and Gantt charts.

---

### 6. Academic & Pedagogical Value
UnixGuard FS serves as an effective learning tool by providing:
1. **Hands-on Practice:** An interactive environment to practice commands without administrative risk.
2. **Visual Feedback:** Shows the direct impact of commands (e.g., `chmod`) on the file tree immediately.
3. **Simplified Visualizations:** Explains permission checks and Gantt chart scheduling calculations clearly.
4. **Clean Codebase:** Clean Python codebases that can be used for university lab projects or viva demonstrations.
