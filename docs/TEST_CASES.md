# UnixGuard FS — Validation & Test Cases

This document defines the verification and validation test suite created to assert the correctness of UnixGuard FS services.

---

## 1. Permission and Access Control Test Suite (`test_permissions.py`)

### TC-PERM-01: Octal-to-Symbolic Conversions
*   **Description:** Asserts that standard octal codes convert to correct symbolic strings.
*   **Inputs / Expected Outputs:**
    - `0755` ➔ `rwxr-xr-x`
    - `0644` ➔ `rw-r--r--`
    - `0777` ➔ `rwxrwxrwx`
    - `0600` ➔ `rw-------`

### TC-PERM-02: Special Permissions Resolution
*   **Description:** Verifies that special bits (Sticky Bit, SetUID, SetGID) are correctly parsed and appended in symbolic format.
*   **Inputs / Expected Outputs:**
    - `1777` ➔ `rwxrwxrwt` (Sticky bit)
    - `4755` ➔ `rwsr-xr-x` (SetUID)
    - `2755` ➔ `rwxr-sr-x` (SetGID)

### TC-PERM-03: Access Control Decision Logic
*   **Description:** Validates user/group/other access rights resolution.
*   **Test Matrix:**
    - Owner `alice` requesting Read on a `0644` file owned by `alice` ➔ **ALLOWED** (Category: owner)
    - User `bob` requesting Write on a `0644` file owned by `root:root` ➔ **DENIED** (Category: others)
    - User `alice` (in `devs` group) requesting Execute on a `0750` file owned by `root:devs` ➔ **ALLOWED** (Category: group)

---

## 2. Terminal Simulator Test Suite (`test_terminal.py`)

### TC-TERM-01: Basic Shell Commands
*   **Description:** Asserts core commands return standard directory output.
*   **Commands Verified:**
    - `pwd` ➔ Returns `/`
    - `ls` ➔ Contains `home`
    - `whoami` ➔ Returns active session user

### TC-TERM-02: Directory Navigation & Manipulation
*   **Description:** Verifies directory traversal and creation.
*   **Sequence:**
    - `cd home` ➔ `pwd` matches `/home`
    - `cd ..` ➔ `pwd` matches `/`
    - `mkdir testdir` ➔ `ls` contains `testdir`

### TC-TERM-03: File Creation & Redirection
*   **Description:** Asserts file touch, write, and read functions.
*   - `touch newfile.txt`
    - `echo hello > newfile.txt`
    - `cat newfile.txt` ➔ Output contains `hello`
    - `rm newfile.txt` ➔ Command completes successfully

---

## 3. Security Auditor Test Suite (`test_audit.py`)

### TC-AUDIT-01: Scan Execution
*   **Description:** Ensures the scanning task starts, scans files, and completes without errors.
*   **Assertions:** `audit.completed_at` is set, and `audit.total_files > 0`.

### TC-AUDIT-02: Vulnerability Detections
*   **Description:** Validates the classification engine detects target misconfigurations.
*   **Checks:**
    - Detects world-writable files (e.g., `/tmp/insecure_script.sh` [0777]).
    - Detects broken symbolic links.
    - Detects sensitive files accessible by others (e.g., `/etc/database.env`).

### TC-AUDIT-03: Multi-Threaded Task Logging
*   **Description:** Verifies that scan tasks are split among threads and logged.
*   **Assertions:** Thread names are stored and multiple threads are utilized.

---

## 4. CPU Scheduler Test Suite (`test_scheduler.py`)

### TC-SCHED-01: FCFS Correctness
*   **Description:** Asserts FCFS runs jobs in arrival order without overlap.

### TC-SCHED-02: Round Robin Slicing
*   **Description:** Verifies that time quantum slicing operates correctly.
*   **Check:** Each Gantt interval block duration is `≤ quantum`.

### TC-SCHED-03: Priority Sorting
*   **Description:** Validates that priority scheduling executes high-priority processes first.
