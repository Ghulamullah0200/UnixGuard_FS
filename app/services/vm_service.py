"""
vm_service.py — Demand-paged Virtual Memory Manager simulation.
Simulates a 64KB virtual address space per process (16 pages of 4KB) mapped to a shared 32KB RAM (8 frames of 4KB)
and 32 swap blocks on disk.
"""

from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from app.models import VirtualMemoryProcess, VirtualPage

PAGE_SIZE = 4096      # 4KB
VIRTUAL_PAGES = 16    # 16 pages * 4KB = 64KB address space
PHYSICAL_FRAMES = 8   # 8 frames * 4KB = 32KB RAM
SWAP_BLOCKS = 32      # 32 swap blocks on disk


def get_all_processes(db: Session) -> List[VirtualMemoryProcess]:
    return db.query(VirtualMemoryProcess).all()


def get_process_by_id(db: Session, pid: int) -> Optional[VirtualMemoryProcess]:
    return db.query(VirtualMemoryProcess).get(pid)


def create_process(db: Session, name: str) -> VirtualMemoryProcess:
    """Create a process and initialize its page table (all invalid initially)."""
    proc = VirtualMemoryProcess(name=name, state="READY", privilege_ring=3)
    db.add(proc)
    db.commit()
    db.refresh(proc)

    # Initialize 16 virtual pages (0 to 15)
    for p_num in range(VIRTUAL_PAGES):
        page = VirtualPage(
            process_id=proc.id,
            page_number=p_num,
            frame_number=None,
            is_valid=False,
            is_dirty=False,
            is_referenced=False,
            swap_block=None,
            allocated_content=None
        )
        db.add(page)

    db.commit()
    db.refresh(proc)
    return proc


def delete_process(db: Session, pid: int) -> bool:
    proc = db.query(VirtualMemoryProcess).get(pid)
    if not proc:
        return False
    db.delete(proc)
    db.commit()
    return True


def get_ram_layout(db: Session) -> List[dict]:
    """Retrieve the physical memory frame status (Frame 0 to 7)."""
    frames = [{"frame_number": i, "pid": None, "process_name": None, "page_number": None, "content": None} for i in range(PHYSICAL_FRAMES)]

    # Query all valid pages across all processes
    valid_pages = db.query(VirtualPage).filter(VirtualPage.is_valid == True).all()
    for page in valid_pages:
        proc = db.query(VirtualMemoryProcess).get(page.process_id)
        if page.frame_number is not None and page.frame_number < PHYSICAL_FRAMES:
            frames[page.frame_number] = {
                "frame_number": page.frame_number,
                "pid": page.process_id,
                "process_name": proc.name if proc else "Unknown",
                "page_number": page.page_number,
                "content": page.allocated_content or "[empty]"
            }
    return frames


def get_swap_layout(db: Session) -> List[dict]:
    """Retrieve the swap space block status on disk."""
    swap = [{"block_number": i, "pid": None, "process_name": None, "page_number": None} for i in range(SWAP_BLOCKS)]

    swapped_pages = db.query(VirtualPage).filter(VirtualPage.swap_block.isnot(None)).all()
    for page in swapped_pages:
        proc = db.query(VirtualMemoryProcess).get(page.process_id)
        if page.swap_block is not None and page.swap_block < SWAP_BLOCKS:
            swap[page.swap_block] = {
                "block_number": page.swap_block,
                "pid": page.process_id,
                "process_name": proc.name if proc else "Unknown",
                "page_number": page.page_number
            }
    return swap


def access_memory(db: Session, pid: int, address: int, operation: str, data: Optional[str] = None) -> dict:
    """
    Simulate a memory access (read/write) for a specific virtual address.
    Triggers demand paging and the Page Fault Handler if page is invalid.
    Uses the Clock Replacement Algorithm.
    """
    proc = db.query(VirtualMemoryProcess).get(pid)
    if not proc:
        return {"success": False, "error": "Process not found"}

    if address < 0 or address >= VIRTUAL_PAGES * PAGE_SIZE:
        return {"success": False, "error": f"Segmentation Fault: Address 0x{address:04X} out of bounds"}

    page_num = address // PAGE_SIZE
    page = db.query(VirtualPage).filter(
        VirtualPage.process_id == pid,
        VirtualPage.page_number == page_num
    ).first()

    if not page:
        return {"success": False, "error": "Virtual page mapping error"}

    logs = []
    step = 1
    is_fault = False

    def add_log(desc: str, ring: str = "User"):
        nonlocal step
        logs.append({"step": step, "description": desc, "ring": ring})
        step += 1

    # Access starts in Ring 3 (User privilege)
    add_log(f"Process '{proc.name}' (PID {pid}) requested {operation.upper()} at virtual address 0x{address:04X} (Page {page_num}).", "User")

    if page.is_valid:
        # Page Hit!
        frame = page.frame_number
        add_log(f"Page Hit! Page {page_num} is already loaded in Physical Frame {frame}.", "User")
        page.is_referenced = True
        if operation == "write":
            page.is_dirty = True
            page.allocated_content = data or ""
            add_log(f"Write successful. Frame {frame} updated with content: '{page.allocated_content}'. Page marked DIRTY.", "User")
        else:
            add_log(f"Read successful. Value in Frame {frame}: '{page.allocated_content or '[empty]'}'", "User")

        db.commit()
        return {
            "success": True,
            "address": address,
            "page_number": page_num,
            "frame_number": frame,
            "is_page_fault": False,
            "logs": logs,
            "value": page.allocated_content
        }

    # Page Fault! Trap to Ring 0 (Kernel mode)
    is_fault = True
    add_log(f"PAGE FAULT! Page {page_num} is not present in RAM (Valid bit = 0).", "User")
    add_log(f"TRAP: Generating interrupt. Transitioning from Ring 3 (User) to Ring 0 (Kernel Mode).", "Kernel")

    # Step 1: Find a free physical frame
    # A frame is free if no active valid page maps to it
    allocated_frames = {p.frame_number for p in db.query(VirtualPage).filter(VirtualPage.is_valid == True).all()}
    free_frames = [f for f in range(PHYSICAL_FRAMES) if f not in allocated_frames]

    target_frame = None
    if free_frames:
        target_frame = free_frames[0]
        add_log(f"Found free Physical Frame {target_frame} in RAM.", "Kernel")
    else:
        # RAM is full, must run Page Replacement Algorithm (Clock)
        add_log("RAM is full. Running Page Replacement Algorithm (Clock / Second-Chance)...", "Kernel")

        # Get all currently valid pages in RAM, ordered by frame_number
        valid_pages_in_ram = {
            p.frame_number: p for p in db.query(VirtualPage).filter(VirtualPage.is_valid == True).all()
        }

        # Simulated Clock scan starting at Frame 0
        victim_page = None
        # We perform up to two full sweeps of frames to guarantee we find a page with reference bit 0
        # since we clear it in the first sweep.
        sweeps = 0
        current_frame_check = 0

        while victim_page is None and sweeps < 2:
            candidate_page = valid_pages_in_ram.get(current_frame_check)
            if candidate_page:
                if candidate_page.is_referenced:
                    add_log(f"Clock Hand at Frame {current_frame_check} (Page {candidate_page.page_number} of PID {candidate_page.process_id}): Referenced bit is 1. Clearing it and passing.", "Kernel")
                    candidate_page.is_referenced = False
                    db.commit()
                else:
                    add_log(f"Clock Hand at Frame {current_frame_check} (Page {candidate_page.page_number} of PID {candidate_page.process_id}): Referenced bit is 0. Selected as victim!", "Kernel")
                    victim_page = candidate_page
                    target_frame = current_frame_check
                    break

            current_frame_check += 1
            if current_frame_check >= PHYSICAL_FRAMES:
                current_frame_check = 0
                sweeps += 1

        # Fallback if no victim selected (should not happen)
        if not victim_page:
            victim_page = db.query(VirtualPage).filter(VirtualPage.is_valid == True).first()
            target_frame = victim_page.frame_number
            add_log(f"Fallback: Evicting Page {victim_page.page_number} of PID {victim_page.process_id} from Frame {target_frame}.", "Kernel")

        # Evict victim_page
        victim_proc = db.query(VirtualMemoryProcess).get(victim_page.process_id)
        victim_proc_name = victim_proc.name if victim_proc else "Unknown"

        if victim_page.is_dirty:
            # Dirty victim: must page out to swap space on disk
            # Find a free swap block
            allocated_swap_blocks = {p.swap_block for p in db.query(VirtualPage).filter(VirtualPage.swap_block.isnot(None)).all()}
            free_swap_blocks = [sb for sb in range(SWAP_BLOCKS) if sb not in allocated_swap_blocks]

            if not free_swap_blocks:
                add_log("CRITICAL ERROR: Out of Swap Space on Disk! Page replacement failed.", "Kernel")
                add_log("Kernel panics. Returning failure.", "Kernel")
                return {"success": False, "error": "Kernel Panic: Out of Swap Space"}

            allocated_swap = free_swap_blocks[0]
            add_log(f"Victim page {victim_page.page_number} of process '{victim_proc_name}' (PID {victim_page.process_id}) is DIRTY. Paging out to Swap Block {allocated_swap} on Disk.", "Kernel")

            victim_page.swap_block = allocated_swap
            victim_page.is_valid = False
            victim_page.frame_number = None
            victim_page.is_dirty = False
            victim_page.is_referenced = False
            db.commit()
        else:
            # Clean victim: just evict
            add_log(f"Victim page {victim_page.page_number} of process '{victim_proc_name}' (PID {victim_page.process_id}) is CLEAN. Evicting from RAM without swap write.", "Kernel")
            victim_page.is_valid = False
            victim_page.frame_number = None
            victim_page.is_referenced = False
            db.commit()

    # Step 3: Page in the requested page
    if page.swap_block is not None:
        add_log(f"Requested page {page_num} was swapped out. Reading from Swap Block {page.swap_block} into Frame {target_frame}.", "Kernel")
        page.swap_block = None  # freed swap block
    else:
        add_log(f"Requested page {page_num} is clean/new. Allocating and initializing zero-filled page in Frame {target_frame}.", "Kernel")

    # Step 4: Map requested page to frame
    page.frame_number = target_frame
    page.is_valid = True
    page.is_referenced = True

    if operation == "write":
        page.is_dirty = True
        page.allocated_content = data or ""
        add_log(f"Write completed: Frame {target_frame} initialized with content: '{data}'. Page marked DIRTY.", "Kernel")
    else:
        page.is_dirty = False
        add_log(f"Read completed: Page mapped into Frame {target_frame}.", "Kernel")

    db.commit()

    # Returning to Ring 3 (User privilege)
    add_log(f"Interrupt handled. Returning from Ring 0 (Kernel) to Ring 3 (User mode). Memory operation completed.", "User")

    return {
        "success": True,
        "address": address,
        "page_number": page_num,
        "frame_number": target_frame,
        "is_page_fault": is_fault,
        "logs": logs,
        "value": page.allocated_content
    }
