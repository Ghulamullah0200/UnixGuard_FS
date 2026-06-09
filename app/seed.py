"""
seed.py — Populate the database with default disk blocks, a hierarchical directory
structure, AND 300+ virtual-memory processes with pre-executed read/write accesses
so the VM simulator already shows page faults and swap activity on first load.
"""

import random
from datetime import datetime, timezone
from app.database import engine, SessionLocal, Base
from app.models import FilesystemNode, DiskBlock, VirtualMemoryProcess, VirtualPage
from app.services.filesystem_service import ensure_disk_blocks, create_node, update_file_content

# VM constants — must match vm_service.py
PAGE_SIZE = 4096
VIRTUAL_PAGES = 16
PHYSICAL_FRAMES = 8
SWAP_BLOCKS = 32


# ──────────────────────────────────────────────────────────────
# Helper: create a VM process + 16 blank pages (same as vm_service.create_process)
# ──────────────────────────────────────────────────────────────
def _create_process(db, name, privilege_ring=3):
    proc = VirtualMemoryProcess(name=name, state="READY", privilege_ring=privilege_ring)
    db.add(proc)
    db.flush()  # get proc.id without full commit

    pages = []
    for p_num in range(VIRTUAL_PAGES):
        page = VirtualPage(
            process_id=proc.id,
            page_number=p_num,
            frame_number=None,
            is_valid=False,
            is_dirty=False,
            is_referenced=False,
            swap_block=None,
            allocated_content=None,
        )
        db.add(page)
        pages.append(page)

    db.flush()
    return proc, pages


# ──────────────────────────────────────────────────────────────
# Helper: simulate a memory access (simplified inline version)
# Returns the log description for display purposes
# ──────────────────────────────────────────────────────────────
def _simulate_access(db, proc, pages, address, operation, data=None):
    """Lightweight in-seed memory access that mirrors vm_service.access_memory logic."""
    page_num = address // PAGE_SIZE
    if page_num >= VIRTUAL_PAGES:
        return

    page = pages[page_num]

    if page.is_valid:
        # Page Hit
        page.is_referenced = True
        if operation == "write":
            page.is_dirty = True
            page.allocated_content = data or ""
        return

    # ── Page Fault — find a free frame or evict ──────────────
    # Collect all currently occupied frames across ALL processes
    all_valid = db.query(VirtualPage).filter(VirtualPage.is_valid == True).all()
    occupied = {p.frame_number for p in all_valid if p.frame_number is not None}
    free_frames = [f for f in range(PHYSICAL_FRAMES) if f not in occupied]

    target_frame = None

    if free_frames:
        target_frame = free_frames[0]
    else:
        # Clock (Second-Chance) replacement
        frame_map = {p.frame_number: p for p in all_valid if p.frame_number is not None}
        victim = None
        sweeps = 0
        cursor = 0
        while victim is None and sweeps < 2:
            candidate = frame_map.get(cursor)
            if candidate:
                if candidate.is_referenced:
                    candidate.is_referenced = False
                else:
                    victim = candidate
                    target_frame = cursor
                    break
            cursor += 1
            if cursor >= PHYSICAL_FRAMES:
                cursor = 0
                sweeps += 1

        if victim is None:
            # Fallback
            victim = all_valid[0]
            target_frame = victim.frame_number

        # Evict victim
        if victim.is_dirty:
            # Find a free swap block
            used_swaps = {p.swap_block for p in db.query(VirtualPage).filter(
                VirtualPage.swap_block.isnot(None)).all()}
            free_swaps = [sb for sb in range(SWAP_BLOCKS) if sb not in used_swaps]
            if free_swaps:
                victim.swap_block = free_swaps[0]
            victim.is_valid = False
            victim.frame_number = None
            victim.is_dirty = False
            victim.is_referenced = False
        else:
            victim.is_valid = False
            victim.frame_number = None
            victim.is_referenced = False

    # Page-in the requested page
    if page.swap_block is not None:
        page.swap_block = None  # free the swap block

    page.frame_number = target_frame
    page.is_valid = True
    page.is_referenced = True

    if operation == "write":
        page.is_dirty = True
        page.allocated_content = data or ""
    else:
        page.is_dirty = False

    db.flush()


# ──────────────────────────────────────────────────────────────
# Process name templates for realistic demo data
# ──────────────────────────────────────────────────────────────
_PROCESS_CATEGORIES = {
    "browsers": [
        "Chrome", "Firefox", "Safari", "Edge", "Opera", "Brave", "Vivaldi",
        "Chromium", "Tor-Browser", "Waterfox",
    ],
    "editors": [
        "VSCode", "Vim", "Nano", "Emacs", "Sublime", "Atom", "Notepad++",
        "IntelliJ", "PyCharm", "WebStorm",
    ],
    "system": [
        "systemd", "cron", "sshd", "nginx", "httpd", "dockerd", "kubelet",
        "journald", "networkd", "resolved", "udevd", "polkitd", "dbus",
        "ModemManager", "avahi-daemon",
    ],
    "user_apps": [
        "Spotify", "Discord", "Slack", "Telegram", "Signal", "Zoom",
        "Teams", "Skype", "OBS-Studio", "VLC", "Audacity", "GIMP",
        "Blender", "Kdenlive", "Thunderbird",
    ],
    "servers": [
        "postgres", "mysql", "redis", "mongodb", "rabbitmq", "kafka",
        "elasticsearch", "grafana", "prometheus", "influxdb", "consul",
        "vault", "etcd", "minio", "haproxy",
    ],
    "dev_tools": [
        "node", "python3", "java", "gcc", "rustc", "go", "ruby", "php",
        "dotnet", "perl", "lua", "tsc", "webpack", "vite", "jest",
    ],
    "ml_data": [
        "jupyter", "tensorflow", "pytorch", "pandas-worker", "sklearn",
        "numpy-proc", "matplotlib", "keras-fit", "xgboost", "lightgbm",
    ],
    "games": [
        "minecraft", "steam", "csgo", "valorant", "dota2", "roblox",
        "fortnite", "apex", "genshin", "overwatch",
    ],
    "utilities": [
        "htop", "top", "iotop", "iftop", "nethogs", "ncdu", "tmux",
        "screen", "rsync", "tar", "gzip", "curl", "wget", "ssh-agent",
        "gpg-agent",
    ],
    "daemons": [
        "bluetoothd", "cupsd", "ntpd", "snmpd", "atd", "xinetd",
        "smartd", "irqbalance", "lvm2", "mdraid",
    ],
}

_WRITE_DATA_TEMPLATES = [
    "heap_alloc_{pid}_{page}",
    "stack_frame_{pid}_var_{page}",
    "buffer[{pid}][{page}]='data'",
    "malloc({pid},{page},4096)",
    "mmap_region_{pid}_p{page}",
    "cache_line_{pid}_{page}",
    "shared_mem_{pid}_{page}",
    "text_segment_{pid}",
    "bss_initialized_{pid}",
    "config_loaded_{pid}_{page}",
    "socket_buf_{pid}_{page}",
    "pipe_data_{pid}_{page}",
    "tmp_file_{pid}_{page}",
    "log_buffer_{pid}_{page}",
    "render_ctx_{pid}_{page}",
]


def _generate_process_names(count):
    """Generate `count` unique realistic process names."""
    names = []
    # First pass: use all base names
    for category_names in _PROCESS_CATEGORIES.values():
        for name in category_names:
            names.append(name)
            if len(names) >= count:
                return names

    # Second pass: append instance numbers to fill remaining
    instance = 2
    while len(names) < count:
        for category_names in _PROCESS_CATEGORIES.values():
            for base_name in category_names:
                names.append(f"{base_name}-{instance}")
                if len(names) >= count:
                    return names
        instance += 1

    return names


# ──────────────────────────────────────────────────────────────
# Main Seed
# ──────────────────────────────────────────────────────────────
def seed_database():
    """Drop existing tables, recreate, populate disk blocks, seed directory tree,
    AND create 300+ VM processes with pre-executed memory accesses."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # ────────────────────────────────────────────
        # 1. Filesystem seed (unchanged from original)
        # ────────────────────────────────────────────
        print("[seed] Initializing 256 virtual disk blocks...")
        ensure_disk_blocks(db)

        print("[seed] Seeding directory tree...")
        root = create_node(db, name="/", node_type="directory", parent_id=None)

        # /home
        home = create_node(db, name="home", node_type="directory", parent_id=root.id)
        h_admin = create_node(db, name="admin", node_type="directory", parent_id=home.id)
        create_node(db, name="notes.txt", node_type="file", parent_id=h_admin.id,
                    content="Admin private notes — server credentials are stored in /etc/database.env")

        h_dev = create_node(db, name="developer", node_type="directory", parent_id=home.id)
        create_node(db, name="app.py", node_type="file", parent_id=h_dev.id,
                    content="#!/usr/bin/env python3\n# Main application entry point\nprint('Hello UnixGuard')")
        create_node(db, name="deploy.sh", node_type="file", parent_id=h_dev.id,
                    content="#!/bin/bash\n# Deployment script\necho 'Deploying application...'")

        h_intern = create_node(db, name="intern", node_type="directory", parent_id=home.id)
        create_node(db, name="tasks.txt", node_type="file", parent_id=h_intern.id,
                    content="TODO:\n- Learn Unix virtual memory\n- Complete OS virtual memory assignment")

        # /etc
        etc = create_node(db, name="etc", node_type="directory", parent_id=root.id)
        create_node(db, name="database.env", node_type="file", parent_id=etc.id,
                    content="DB_HOST=localhost\nDB_USER=admin\nDB_PASS=supersecret123\nDB_NAME=production")
        create_node(db, name="app.conf", node_type="file", parent_id=etc.id,
                    content="[server]\nport=8080\nworkers=4\nlog_level=info")

        # /var
        var = create_node(db, name="var", node_type="directory", parent_id=root.id)
        logs = create_node(db, name="logs", node_type="directory", parent_id=var.id)
        create_node(db, name="access.log", node_type="file", parent_id=logs.id,
                    content="192.168.1.1 - - [01/Jan/2025:00:00:01] \"GET / HTTP/1.1\" 200\n192.168.1.2 - - [01/Jan/2025:00:00:02] \"POST /login HTTP/1.1\" 302")
        create_node(db, name="security.log", node_type="file", parent_id=logs.id,
                    content="[WARN] Failed login attempt from 10.0.0.5\n[ALERT] Privilege escalation detected")

        # /shared
        shared = create_node(db, name="shared", node_type="directory", parent_id=root.id)
        create_node(db, name="report.txt", node_type="file", parent_id=shared.id,
                    content="Quarterly report draft — contains revenue figures")
        create_node(db, name="team-notes.txt", node_type="file", parent_id=shared.id,
                    content="Team meeting notes:\n- Discuss virtual memory paging\n- Review page fault handler simulation")
        create_node(db, name="broken-link", node_type="symlink", parent_id=shared.id,
                    target_path="/nonexistent/path/file.txt")

        # /tmp
        create_node(db, name="tmp", node_type="directory", parent_id=root.id)

        db.commit()
        print("[seed] Filesystem seeded successfully.")

        # ────────────────────────────────────────────
        # 2. Virtual Memory seed — 320 processes
        # ────────────────────────────────────────────
        TOTAL_PROCS = 320
        print(f"[seed] Creating {TOTAL_PROCS} VM processes with memory accesses...")

        random.seed(42)  # deterministic for reproducibility
        process_names = _generate_process_names(TOTAL_PROCS)

        all_processes = []
        for name in process_names:
            proc, pages = _create_process(db, name)
            all_processes.append((proc, pages))

        db.flush()
        print(f"[seed] {TOTAL_PROCS} processes created. Executing memory access commands...")

        # ── Execute a series of read/write operations across processes ──
        # Strategy:
        #   - First 8 processes each write to page 0 → fills all 8 RAM frames
        #   - Next processes trigger page faults → demonstrates swapping
        #   - Mix of reads and writes across many processes
        access_count = 0

        # Phase 1: Fill up RAM completely (8 frames) with first 8 processes
        print("[seed]   Phase 1: Filling 8 physical RAM frames...")
        for i in range(min(8, TOTAL_PROCS)):
            proc, pages = all_processes[i]
            addr = 0 * PAGE_SIZE  # Page 0
            data = f"heap_alloc_{proc.id}_p0"
            _simulate_access(db, proc, pages, addr, "write", data)
            access_count += 1

        db.flush()

        # Phase 2: Cause page faults and swapping for processes 9-50
        print("[seed]   Phase 2: Triggering page faults and swap-outs (processes 9-50)...")
        for i in range(8, min(50, TOTAL_PROCS)):
            proc, pages = all_processes[i]
            # Write to page 0 → will evict someone from RAM
            data_template = random.choice(_WRITE_DATA_TEMPLATES)
            data = data_template.format(pid=proc.id, page=0)
            _simulate_access(db, proc, pages, 0 * PAGE_SIZE, "write", data)
            access_count += 1

            # Also write to page 1 for some processes → more swapping
            if i % 3 == 0:
                data = data_template.format(pid=proc.id, page=1)
                _simulate_access(db, proc, pages, 1 * PAGE_SIZE, "write", data)
                access_count += 1

        db.flush()

        # Phase 3: Scattered reads and writes for processes 51-200
        print("[seed]   Phase 3: Mixed read/write workload (processes 51-200)...")
        for i in range(50, min(200, TOTAL_PROCS)):
            proc, pages = all_processes[i]
            # Random page access
            page_num = random.randint(0, 7)
            addr = page_num * PAGE_SIZE

            if random.random() < 0.6:
                # Write
                tmpl = random.choice(_WRITE_DATA_TEMPLATES)
                data = tmpl.format(pid=proc.id, page=page_num)
                _simulate_access(db, proc, pages, addr, "write", data)
            else:
                # Read
                _simulate_access(db, proc, pages, addr, "read")
            access_count += 1

        db.flush()

        # Phase 4: Heavy write workload for processes 201-320
        # Multiple pages per process → fills swap space
        print("[seed]   Phase 4: Heavy multi-page writes (processes 201-320)...")
        for i in range(200, TOTAL_PROCS):
            proc, pages = all_processes[i]
            # Write to 2-4 random pages
            num_pages = random.randint(2, 4)
            for _ in range(num_pages):
                page_num = random.randint(0, 15)
                addr = page_num * PAGE_SIZE
                tmpl = random.choice(_WRITE_DATA_TEMPLATES)
                data = tmpl.format(pid=proc.id, page=page_num)
                _simulate_access(db, proc, pages, addr, "write", data)
                access_count += 1

            # Flush periodically to avoid huge pending changes
            if i % 50 == 0:
                db.flush()

        db.commit()
        print(f"[seed] VM seed complete: {TOTAL_PROCS} processes, {access_count} memory accesses executed.")
        print("[seed] Database seeded successfully (all done).")

    except Exception as e:
        db.rollback()
        print(f"[seed] Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
