"""
seed.py — Populate the database with default disk blocks and a hierarchical directory structure.
"""

from datetime import datetime, timezone
from app.database import engine, SessionLocal, Base
from app.models import FilesystemNode, DiskBlock
from app.services.filesystem_service import ensure_disk_blocks, create_node, update_file_content

def seed_database():
    """Drop existing tables, recreate, populate disk blocks and seed directory tree."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Initialize virtual disk blocks (0 to 255)
        print("[seed] Initializing 256 virtual disk blocks...")
        ensure_disk_blocks(db)

        # ── Root ──────────────────────────────────────
        print("[seed] Seeding directory tree...")
        root = create_node(db, name="/", node_type="directory", parent_id=None)

        # ── /home ─────────────────────────────────────
        home = create_node(db, name="home", node_type="directory", parent_id=root.id)

        # /home/admin
        h_admin = create_node(db, name="admin", node_type="directory", parent_id=home.id)
        create_node(db, name="notes.txt", node_type="file", parent_id=h_admin.id,
                    content="Admin private notes — server credentials are stored in /etc/database.env")

        # /home/developer
        h_dev = create_node(db, name="developer", node_type="directory", parent_id=home.id)
        create_node(db, name="app.py", node_type="file", parent_id=h_dev.id,
                    content="#!/usr/bin/env python3\n# Main application entry point\nprint('Hello UnixGuard')")
        create_node(db, name="deploy.sh", node_type="file", parent_id=h_dev.id,
                    content="#!/bin/bash\n# Deployment script\necho 'Deploying application...'")

        # /home/intern
        h_intern = create_node(db, name="intern", node_type="directory", parent_id=home.id)
        create_node(db, name="tasks.txt", node_type="file", parent_id=h_intern.id,
                    content="TODO:\n- Learn Unix virtual memory\n- Complete OS virtual memory assignment")

        # ── /etc ──────────────────────────────────────
        etc = create_node(db, name="etc", node_type="directory", parent_id=root.id)
        create_node(db, name="database.env", node_type="file", parent_id=etc.id,
                    content="DB_HOST=localhost\nDB_USER=admin\nDB_PASS=supersecret123\nDB_NAME=production")
        create_node(db, name="app.conf", node_type="file", parent_id=etc.id,
                    content="[server]\nport=8080\nworkers=4\nlog_level=info")

        # ── /var ──────────────────────────────────────
        var = create_node(db, name="var", node_type="directory", parent_id=root.id)
        logs = create_node(db, name="logs", node_type="directory", parent_id=var.id)
        create_node(db, name="access.log", node_type="file", parent_id=logs.id,
                    content="192.168.1.1 - - [01/Jan/2025:00:00:01] \"GET / HTTP/1.1\" 200\n192.168.1.2 - - [01/Jan/2025:00:00:02] \"POST /login HTTP/1.1\" 302")
        create_node(db, name="security.log", node_type="file", parent_id=logs.id,
                    content="[WARN] Failed login attempt from 10.0.0.5\n[ALERT] Privilege escalation detected")

        # ── /shared ───────────────────────────────────
        shared = create_node(db, name="shared", node_type="directory", parent_id=root.id)
        create_node(db, name="report.txt", node_type="file", parent_id=shared.id,
                    content="Quarterly report draft — contains revenue figures")
        create_node(db, name="team-notes.txt", node_type="file", parent_id=shared.id,
                    content="Team meeting notes:\n- Discuss virtual memory paging\n- Review page fault handler simulation")

        # Symbolic link
        create_node(db, name="broken-link", node_type="symlink", parent_id=shared.id,
                    target_path="/nonexistent/path/file.txt")

        # ── /tmp ──────────────────────────────────────
        create_node(db, name="tmp", node_type="directory", parent_id=root.id)

        db.commit()
        print("[seed] Database seeded successfully.")

    except Exception as e:
        db.rollback()
        print(f"[seed] Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
