# UnixGuard FS — User Guide & Lab Manual

Welcome to **UnixGuard FS**! This guide explains how to install, launch, and use the simulator to study Unix file system concepts and security auditing.

---

## 1. Quick Start

### Windows Setup
1. Double-click the `run.bat` file in the project root folder.
2. The batch script will automatically:
   - Create a Python virtual environment (`venv`).
   - Install all necessary dependencies from `requirements.txt`.
   - Seed the database (`unixguard.db`) with standard directories, users, and vulnerable test configurations.
   - Start the FastAPI web application using Uvicorn on port `8000`.
3. Open your browser and navigate to: `http://127.0.0.1:8000`

### Unix/macOS Setup
1. Open a terminal, navigate to the directory, and make the shell script executable:
   ```bash
   chmod +x run.sh
   ```
2. Run the orchestration script:
   ```bash
   ./run.sh
   ```
3. Open your browser at: `http://127.0.0.1:8000`

---

## 2. Using the Dashboard
The **Dashboard** tab is the central hub. It displays:
*   **Total Node Stats:** Count of overall virtual directories, files, and links.
*   **Vulnerability Metric:** Count of high-risk findings identified during security scans.
*   **Interactive File Tree:** A visualization of the virtual database tree. You can click nodes to view details or collapse directory branches.

---

## 3. Terminal Simulator
The **Terminal** tab provides a simulated Unix shell console. It is fully sandboxed. You can choose different users (e.g., `admin`, `alice`, `bob`, `developer`, `guest`) to test access control limits.

### Available Commands:
1.  `pwd` - Print current working directory.
2.  `cd <path>` - Change virtual working directory.
3.  `ls [-l]` - List directory contents. Use `-l` for detail/permission views.
4.  `mkdir <name>` - Create a new virtual directory.
5.  `touch <name>` - Create an empty virtual file.
6.  `echo <text> [> or >>] <file>` - Write text contents to a virtual file.
7.  `cat <file>` - Print file contents.
8.  `rm <path>` - Remove a file.
9.  `rmdir <path>` - Remove an empty directory.
10. `chmod <octal> <path>` - Modify permission bits (e.g. `chmod 755 file.txt`).
11. `chown <owner>[:group] <path>` - Change ownership and group associations.
12. `ln [-s] <target> <link>` - Create links. Use `-s` for symbolic (soft) links.
13. `stat <path>` - Display exhaustive inode and permission details.
14. `whoami` - Show the active user context.
15. `tree [<path>]` - Draw a text-based hierarchy tree.
16. `help` - Show available commands.
17. `clear` - Clear console output.

---

## 4. Permission Calculator
The **Permission Calculator** is an interactive utility for converting between:
- Checkbox selections (Read/Write/Execute for Owner, Group, Others).
- Octal notation (e.g., `0644`).
- Symbolic notation (e.g., `rw-r--r--`).
- Special permissions (Sticky Bit `t`, SetUID `s`, SetGID `s`).

Select checkmarks or click quick examples (like `1777` or `755`) to view permission explanations and target command examples.

---

## 5. Security Auditor & Concurrency
1.  Navigate to the **Security Auditor** tab and click **Run Security Scan**.
2.  The engine runs a multi-threaded check to scan all paths.
3.  It flags common Unix misconfigurations:
    - **World-Writable Inodes:** Inodes anyone can write to (like `/tmp` without the sticky bit).
    - **Broken Symbolic Links:** Soft links pointing to deleted paths.
    - **Sensitive Exposure:** Confidential files (like `database.env`) that are readable by "others".
4.  The **Multi-Threading** tab logs details of each thread execution (thread ID, assigned branch, performance metrics).

---

## 6. CPU Scheduling Simulator
The **Scheduling** tab demonstrates core OS process scheduling behavior:
1.  Click **FCFS**, **Round Robin**, or **Priority**.
2.  Adjust the **Time Quantum** input to configure Round Robin intervals.
3.  The simulator processes a set of test jobs, calculating waiting and turnaround times.
4.  It outputs a colored **Gantt Chart** and a **Comparison Chart** showing metrics for each job.
