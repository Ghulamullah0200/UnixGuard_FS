"""
models.py — SQLAlchemy ORM models for the simplified Unix File System (block-mapped) and Virtual Memory Simulator.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Boolean
)
from sqlalchemy.orm import relationship
from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class FilesystemNode(Base):
    __tablename__ = "filesystem_nodes"

    id = Column(Integer, primary_key=True, index=True)
    inode_number = Column(Integer, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    node_type = Column(String(16), nullable=False)  # file, directory, symlink
    parent_id = Column(Integer, ForeignKey("filesystem_nodes.id", ondelete="CASCADE"), nullable=True)
    content = Column(Text, nullable=True)
    size_bytes = Column(Integer, nullable=False, default=0)
    target_path = Column(String(512), nullable=True)       # for symlinks
    created_at = Column(DateTime, default=_utcnow)
    modified_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    accessed_at = Column(DateTime, default=_utcnow)

    parent = relationship("FilesystemNode", remote_side=[id], backref="children")


class DiskBlock(Base):
    __tablename__ = "disk_blocks"

    block_number = Column(Integer, primary_key=True)
    inode_number = Column(Integer, nullable=True) # associated inode
    block_index = Column(Integer, nullable=True) # sequence index in file (0, 1, 2...)


class VirtualMemoryProcess(Base):
    __tablename__ = "virtual_memory_processes"

    id = Column(Integer, primary_key=True, index=True) # PID
    name = Column(String(64), nullable=False)
    state = Column(String(32), default="READY") # READY, RUNNING, BLOCKED
    privilege_ring = Column(Integer, default=3) # Ring 3 (User), Ring 0 (Kernel)

    pages = relationship("VirtualPage", back_populates="process", cascade="all, delete-orphan")
    page_frames = relationship("PageFrame", back_populates="process", cascade="all, delete-orphan")


class VirtualPage(Base):
    __tablename__ = "virtual_pages"

    id = Column(Integer, primary_key=True, index=True)
    process_id = Column(Integer, ForeignKey("virtual_memory_processes.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    frame_number = Column(Integer, nullable=True)
    is_valid = Column(Boolean, default=False)
    is_dirty = Column(Boolean, default=False)
    is_referenced = Column(Boolean, default=False)
    swap_block = Column(Integer, nullable=True)
    allocated_content = Column(Text, nullable=True)

    process = relationship("VirtualMemoryProcess", back_populates="pages")


class PageFrame(Base):
    """Each page (0-15) of a process has up to 8 frame slots.
    When all 8 are full, FIFO eviction pushes the oldest to swap."""
    __tablename__ = "page_frames"

    id = Column(Integer, primary_key=True, index=True)
    process_id = Column(Integer, ForeignKey("virtual_memory_processes.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)   # 0-15
    frame_slot = Column(Integer, nullable=False)     # 0-7
    content = Column(Text, nullable=True)
    operation = Column(String(16), nullable=False, default="write")  # read / write
    entry_order = Column(Integer, nullable=False, default=0)         # for FIFO ordering
    is_swapped = Column(Boolean, default=False)
    swap_block = Column(Integer, nullable=True)

    process = relationship("VirtualMemoryProcess", back_populates="page_frames")
