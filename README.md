# UnixGuard FS
> **Web-Based Unix File System Simulator and Security Auditor**

UnixGuard FS is an educational simulator designed for Operating Systems Theory courses. It provides a visual interface and sandboxed terminal for exploring virtual inodes, directory structures, hard links, symbolic links, access-control permissions, multi-threaded security scanning, and CPU scheduling.

---

## Key Features
*   **Virtual File System (VFS):** Decoupled filename and inode database layout simulating directories, files, hard links, and symbolic links.
*   **Terminal Simulator:** Interactive, allowlist-based shell console supporting standard commands (`ls`, `cd`, `chmod`, `ln`, `cat`, etc.).
*   **Access Control Resolution:** Core engine calculating owner, group, other, and special permission bits (SUID, SGID, Sticky Bit).
*   **Security Auditor:** Concurrent directory tree scanner using `ThreadPoolExecutor` to find world-writable files, broken symlinks, and sensitive exposures.
*   **Scheduling Simulator:** Educational module demonstrating FCFS, Round Robin, and Priority scheduling algorithms with Gantt charts.
*   **Premium Web UI:** Modern, dark-themed responsive single-page dashboard.

---

## Quick Start

### Windows
1. Double-click `run.bat`.
2. Open your browser to: [http://127.0.0.1:8000](http://127.0.0.1:8000)

### Linux / macOS
1. Open a terminal and run:
   ```bash
   chmod +x run.sh
   ./run.sh
   ```
2. Open your browser to: [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## Technical Details
*   **Backend:** Python 3.12+, FastAPI, SQLAlchemy, SQLite
*   **Frontend:** HTML5, CSS3 Grid/Variables, Vanilla Javascript, Chart.js
*   **Testing:** Pytest (run tests using `pytest tests/ -v`)

---

## Academic Documentation
Refer to the `docs/` folder for comprehensive documentation files:
- [PROJECT_REPORT_DRAFT.md](docs/PROJECT_REPORT_DRAFT.md) — Main academic project report.
- [USER_GUIDE.md](docs/USER_GUIDE.md) — Detailed manual on using each interface feature.
- [VIVA_GUIDE.md](docs/VIVA_GUIDE.md) — Questions and answers for viva voce preparation.
- [CLO_PLO_MAPPING.md](docs/CLO_PLO_MAPPING.md) — Course learning outcomes mapping.
- [TEST_CASES.md](docs/TEST_CASES.md) — Validations covering services and terminal commands.
- [SCREENSHOT_CHECKLIST.md](docs/SCREENSHOT_CHECKLIST.md) — Recommended screenshots for student reports.
