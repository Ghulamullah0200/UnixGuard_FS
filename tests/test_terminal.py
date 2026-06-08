"""Tests for the terminal simulator."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import engine, Base, SessionLocal
from app.seed import seed_database
from app.services.terminal_service import execute_command
import app.services.terminal_service as ts

import pytest

@pytest.fixture(autouse=True)
def setup_db():
    seed_database()
    ts._cwd_id = None  # Reset global CWD tracking to root
    yield

def _db():
    return SessionLocal()

def test_pwd():
    db = _db()
    r = execute_command(db, "pwd")
    assert r["output"] == "/"
    assert r["error"] is False
    db.close()

def test_ls():
    db = _db()
    r = execute_command(db, "ls")
    assert "home" in r["output"]
    assert r["error"] is False
    db.close()

def test_ls_l():
    db = _db()
    r = execute_command(db, "ls -l")
    assert "blks" in r["output"]
    db.close()

def test_cd_and_pwd():
    db = _db()
    execute_command(db, "cd home")
    r = execute_command(db, "pwd")
    assert r["output"] == "/home"
    db.close()

def test_cd_dotdot():
    db = _db()
    execute_command(db, "cd home")
    execute_command(db, "cd ..")
    r = execute_command(db, "pwd")
    assert r["output"] == "/"
    db.close()

def test_mkdir():
    db = _db()
    r = execute_command(db, "mkdir testdir")
    assert r["error"] is False
    r2 = execute_command(db, "ls")
    assert "testdir" in r2["output"]
    db.close()

def test_touch_and_cat():
    db = _db()
    execute_command(db, "touch newfile.txt")
    r = execute_command(db, "cat newfile.txt")
    assert r["error"] is False
    db.close()

def test_echo_redirect():
    db = _db()
    execute_command(db, "touch testecho.txt")
    execute_command(db, 'echo hello > testecho.txt')
    r = execute_command(db, "cat testecho.txt")
    assert "hello" in r["output"]
    
    # Test append redirect
    execute_command(db, 'echo world >> testecho.txt')
    r = execute_command(db, "cat testecho.txt")
    assert "hello\nworld" in r["output"]
    db.close()

def test_rm():
    db = _db()
    execute_command(db, "touch removeme.txt")
    r = execute_command(db, "rm removeme.txt")
    assert r["error"] is False
    db.close()

def test_stat():
    db = _db()
    r = execute_command(db, "stat /etc/database.env")
    assert "Inode" in r["output"]
    db.close()

def test_tree():
    db = _db()
    r = execute_command(db, "tree /home")
    assert "admin" in r["output"]
    db.close()

def test_df():
    db = _db()
    r = execute_command(db, "df")
    assert "vdisk0" in r["output"]
    db.close()

def test_help():
    db = _db()
    r = execute_command(db, "help")
    assert "Available Commands" in r["output"]
    db.close()

def test_invalid_command():
    db = _db()
    r = execute_command(db, "hackthesystem")
    assert r["error"] is True
    db.close()
