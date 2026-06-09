"""
schemas.py — Pydantic models for request/response validation in UnixGuard FS.
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ──── Filesystem Node & Disk Block ──────────────────────────
class DiskBlockOut(BaseModel):
    block_number: int
    node_id: Optional[int] = None
    block_index: Optional[int] = None
    class Config:
        from_attributes = True


class NodeCreate(BaseModel):
    name: str
    node_type: str = "file"  # file | directory | symlink
    parent_id: Optional[int] = None
    content: Optional[str] = None
    target_path: Optional[str] = None


class NodeOut(BaseModel):
    id: int
    inode_number: int
    name: str
    node_type: str
    parent_id: Optional[int]
    content: Optional[str]
    size_bytes: int
    target_path: Optional[str]
    created_at: Optional[datetime]
    modified_at: Optional[datetime]
    accessed_at: Optional[datetime]
    class Config:
        from_attributes = True


class NodeTree(BaseModel):
    id: int
    inode_number: int
    name: str
    node_type: str
    size_bytes: int
    children: List["NodeTree"] = []
    class Config:
        from_attributes = True


# ──── Terminal ─────────────────────────────────────
class TerminalCommand(BaseModel):
    command: str


class TerminalResponse(BaseModel):
    output: str
    cwd: str
    error: bool = False


# ──── Scheduler ────────────────────────────────────
class SchedulerJob(BaseModel):
    job_id: int
    name: str
    burst_time: int
    priority: int = 5
    arrival_time: int = 0


class SchedulerResult(BaseModel):
    job_id: int
    name: str
    arrival_time: int
    burst_time: int
    start_time: int
    completion_time: int
    waiting_time: int
    turnaround_time: int
    priority: int = 5


class SchedulerDemoResponse(BaseModel):
    algorithm: str
    quantum: Optional[int] = None
    jobs: List[SchedulerResult]
    gantt: List[dict]
    avg_waiting_time: float
    avg_turnaround_time: float


# ──── Virtual Memory ───────────────────────────────
class VMProcessCreate(BaseModel):
    name: str


class VMPageOut(BaseModel):
    id: int
    page_number: int
    frame_number: Optional[int] = None
    is_valid: bool
    is_dirty: bool
    is_referenced: bool
    swap_block: Optional[int] = None
    allocated_content: Optional[str] = None
    class Config:
        from_attributes = True


class VMProcessOut(BaseModel):
    id: int
    name: str
    state: str
    privilege_ring: int
    pages: List[VMPageOut] = []
    class Config:
        from_attributes = True


class VMMemoryAccessRequest(BaseModel):
    process_id: int
    address: int  # 0 to 65535
    operation: str  # read | write
    data: Optional[str] = None


class PageFaultLogEntry(BaseModel):
    step: int
    message: str
    ring: int


class VMMemoryAccessResponse(BaseModel):
    success: bool
    address: int
    page_number: int
    frame_number: Optional[int]
    is_page_fault: bool
    logs: List[PageFaultLogEntry]
    value: Optional[str] = None


# ──── Dashboard Stats ──────────────────────────────
class DashboardStats(BaseModel):
    total_nodes: int
    total_files: int
    total_directories: int
    total_blocks: int
    used_blocks: int
    free_blocks: int
    total_processes: int
