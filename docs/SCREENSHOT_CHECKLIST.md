# Report Screenshot Checklist

To make your academic project report look professional, insert screenshots of the running dashboard. Use this checklist to capture key states:

---

## 1. Dashboard Overview
- [ ] **Tab:** Dashboard (`http://127.0.0.1:8000/`)
- [ ] **Details to include:** The stats grid displaying counts for files, directories, high-risk findings, and active scan tasks, along with the interactive visual directory tree.

---

## 2. File Explorer & Node Inspector
- [ ] **Tab:** File Explorer
- [ ] **Details to include:** A selected directory or file node highlighting the detailed attributes in the inspector card (Inode, Size, Path, Symbolic/Octal permissions, and access explanation).

---

## 3. Terminal Simulator Console
- [ ] **Tab:** Terminal
- [ ] **Action:** Run a sequence of standard Unix commands:
  ```bash
  help
  pwd
  ls -l
  cd home
  tree
  ```
- [ ] **Details to include:** The command execution history and current prompt matching the active directory.

---

## 4. Permission Calculator
- [ ] **Tab:** Permission Calculator
- [ ] **Action:** Toggle checkmarks or click a quick example button (e.g. `1777`).
- [ ] **Details to include:** The resulting octal display, symbolic code, standard `chmod` command, and full text explanation card.

---

## 5. Access Control Test Engine
- [ ] **Tab:** Access Control
- [ ] **Action:** Configure a check:
  - **User:** `bob`
  - **Node:** Select `/etc/database.env` (permissions: `0600`, owner: `root`)
  - **Operation:** `read`
- [ ] **Details to include:** The red **ACCESS DENIED** banner with the detailed access decision reasoning.

---

## 6. Security Audit Findings
- [ ] **Tab:** Security Auditor
- [ ] **Action:** Click "Run Security Scan".
- [ ] **Details to include:** The scan stats card (Scanned Files, Total Findings, Critical, High) and the structured table showing severity badges and descriptions.

---

## 7. Multi-Threaded Progress
- [ ] **Tab:** Multi-Threading
- [ ] **Details to include:** The list of thread workers showing the thread names (e.g., `ThreadPoolExecutor-0_0`), assigned paths, and file scan counts.

---

## 8. CPU Scheduler & Gantt Chart
- [ ] **Tab:** Scheduling
- [ ] **Action:** Run FCFS or Round Robin scheduler algorithm.
- [ ] **Details to include:** Average waiting and turnaround times, process execution table, and the dynamic colored Gantt chart block visualization.
