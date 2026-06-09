"""
vm_service.py — Demand-paged Virtual Memory Manager simulation.
Simulates a 64KB virtual address space per process (16 pages of 4KB) mapped to a shared 32KB RAM (8 frames of 4KB)
and 32 swap blocks on disk.
"""

from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from app.models import VirtualMemoryProcess, VirtualPage, PageFrame

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
    """Retrieve the physical memory frame status (Frame 0 to 7) - returns empty slots by default when no process/page is selected."""
    return [{"frame_number": i, "pid": None, "process_id": None, "process_name": None, "page_number": None, "content": None, "is_dirty": False} for i in range(PHYSICAL_FRAMES)]


def get_swap_layout(db: Session) -> List[dict]:
    """Retrieve the swap space block status on disk - returns empty slots by default when no process/page is selected."""
    return [{"block_number": i, "pid": None, "process_id": None, "process_name": None, "page_number": None} for i in range(SWAP_BLOCKS)]


def access_memory(db: Session, pid: int, address: int, operation: str, data: Optional[str] = None) -> dict:
    """
    Simulate a memory access (read/write) for a specific virtual address.
    Triggers per-page frame allocation and FIFO swapping.
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

    def add_log(desc: str, ring: str = "User"):
        nonlocal step
        logs.append({"step": step, "message": desc, "ring": 0 if ring == "Kernel" else 3})
        step += 1

    # Access starts in Ring 3 (User privilege)
    add_log(f"Process '{proc.name}' (PID {pid}) requested {operation.upper()} at virtual address 0x{address:04X} (Page {page_num}).", "User")

    from sqlalchemy import func
    max_order = db.query(func.max(PageFrame.entry_order)).filter(
        PageFrame.process_id == pid,
        PageFrame.page_number == page_num
    ).scalar() or 0

    ram_frames = db.query(PageFrame).filter(
        PageFrame.process_id == pid,
        PageFrame.page_number == page_num,
        PageFrame.is_swapped == False
    ).order_by(PageFrame.entry_order).all()

    # Step 1: Check if there's space in the 8 frames of this specific page
    if len(ram_frames) < 8:
        occupied_slots = {f.frame_slot for f in ram_frames}
        free_slots = set(range(8)) - occupied_slots
        target_slot = min(free_slots)

        add_log(f"Page {page_num} frames are not full ({len(ram_frames)}/8 used). Found free Frame Slot {target_slot}.", "Kernel")
        
        new_frame = PageFrame(
            process_id=pid,
            page_number=page_num,
            frame_slot=target_slot,
            content=data if operation == "write" else f"Read Op ({hex(address)})",
            operation=operation,
            entry_order=max_order + 1,
            is_swapped=False,
            swap_block=None
        )
        db.add(new_frame)
        
        # Update VirtualPage record for page table stats
        page.is_valid = True
        page.frame_number = target_slot
        page.allocated_content = data if operation == "write" else (page.allocated_content or "")
        if operation == "write":
            page.is_dirty = True
        page.is_referenced = True
        
        db.commit()
        
        add_log(f"Loaded {operation.upper()} command into Frame Slot {target_slot} of Page {page_num}.", "Kernel")
        add_log(f"Returning from Ring 0 to Ring 3. Memory operation completed.", "User")
        
        return {
            "success": True,
            "address": address,
            "page_number": page_num,
            "frame_number": target_slot,
            "is_page_fault": False,
            "logs": logs,
            "value": page.allocated_content
        }

    # Step 2: Frames are full! Page Fault & Swap Triggered!
    # Transition to Ring 0 (Kernel)
    add_log(f"PAGE FAULT! All 8 frames for Page {page_num} are full.", "User")
    add_log(f"TRAP: Transitioning from Ring 3 (User) to Ring 0 (Kernel Mode).", "Kernel")
    add_log(f"Running FIFO Page Replacement on Page {page_num}'s frames...", "Kernel")

    # The oldest frame in RAM for this page is ram_frames[0]
    victim = ram_frames[0]
    add_log(f"Victim selected: Frame Slot {victim.frame_slot} (Content: '{victim.content}') because it is at the TOP (oldest) of the FIFO queue.", "Kernel")

    # Find a free swap block
    used_swap_blocks = {f.swap_block for f in db.query(PageFrame).filter(PageFrame.swap_block.isnot(None)).all()}
    free_swap_blocks = [b for b in range(32) if b not in used_swap_blocks]

    if not free_swap_blocks:
        oldest_swap = db.query(PageFrame).filter(PageFrame.swap_block.isnot(None)).order_by(PageFrame.entry_order).first()
        if oldest_swap:
            target_swap_block = oldest_swap.swap_block
            db.delete(oldest_swap)
            db.commit()
            add_log(f"Disk Swap is full! Evicting oldest swapped block {target_swap_block} to make space.", "Kernel")
        else:
            add_log("CRITICAL ERROR: Out of Swap Space on Disk!", "Kernel")
            return {"success": False, "error": "Kernel Panic: Out of Swap Space"}
    else:
        target_swap_block = free_swap_blocks[0]

    add_log(f"Paging out data from Frame Slot {victim.frame_slot} to Disk Swap Block {target_swap_block}.", "Kernel")

    # Move victim to swap
    victim.is_swapped = True
    victim.swap_block = target_swap_block
    
    # Load new command/data into the freed Frame Slot
    new_frame = PageFrame(
        process_id=pid,
        page_number=page_num,
        frame_slot=victim.frame_slot,
        content=data if operation == "write" else f"Read Op ({hex(address)})",
        operation=operation,
        entry_order=max_order + 1,
        is_swapped=False,
        swap_block=None
    )
    db.add(new_frame)

    # Update VirtualPage record
    page.is_valid = True
    page.frame_number = victim.frame_slot
    page.allocated_content = data if operation == "write" else (page.allocated_content or "")
    if operation == "write":
        page.is_dirty = True
    page.is_referenced = True

    db.commit()

    add_log(f"Swapped out victim to Block {target_swap_block}. Loaded new command into Page {page_num} Frame Slot {victim.frame_slot}.", "Kernel")
    add_log(f"Returning from Ring 0 to Ring 3. Memory operation completed.", "User")

    return {
        "success": True,
        "address": address,
        "page_number": page_num,
        "frame_number": victim.frame_slot,
        "is_page_fault": True,
        "logs": logs,
        "value": page.allocated_content
    }


def get_process_memory_map(db: Session, pid: int, page_num: int = 0) -> Optional[dict]:
    """Get per-process, per-page memory map: which frame slots are occupied
    for this specific page, which are swapped, and summary details."""
    proc = db.query(VirtualMemoryProcess).get(pid)
    if not proc:
        return None

    pages = db.query(VirtualPage).filter(
        VirtualPage.process_id == pid
    ).order_by(VirtualPage.page_number).all()

    ram_frames = db.query(PageFrame).filter(
        PageFrame.process_id == pid,
        PageFrame.page_number == page_num,
        PageFrame.is_swapped == False
    ).all()
    
    ram_map = {f.frame_slot: f for f in ram_frames}

    frames = []
    for slot in range(PHYSICAL_FRAMES):
        f = ram_map.get(slot)
        if f:
            frames.append({
                "frame_number": slot,
                "owner": "self",
                "pid": pid,
                "process_name": proc.name,
                "page_number": page_num,
                "content": f.content or "[empty]",
                "is_dirty": f.operation == "write",
                "is_referenced": True,
                "operation": f.operation
            })
        else:
            frames.append({
                "frame_number": slot,
                "owner": None,
                "pid": None,
                "process_name": None,
                "page_number": None,
                "content": None,
                "is_dirty": False,
                "is_referenced": False,
                "operation": None
            })

    swapped_frames = db.query(PageFrame).filter(
        PageFrame.process_id == pid,
        PageFrame.page_number == page_num,
        PageFrame.is_swapped == True
    ).order_by(PageFrame.swap_block).all()

    swap_entries = []
    for sf in swapped_frames:
        swap_entries.append({
            "swap_block": sf.swap_block,
            "page_number": page_num,
            "content": sf.content or "[swapped]",
            "operation": sf.operation
        })

    pages_in_ram = len(ram_frames)
    pages_in_swap = len(swapped_frames)
    pages_accessed = pages_in_ram + pages_in_swap
    dirty_pages = sum(1 for f in ram_frames if f.operation == "write") + sum(1 for sf in swapped_frames if sf.operation == "write")

    all_swapped = db.query(PageFrame).filter(PageFrame.swap_block.isnot(None)).all()
    total_used_swap = len({p.swap_block for p in all_swapped})

    all_ram_frames = db.query(PageFrame).filter(PageFrame.is_swapped == False).all()
    total_used_frames = len(all_ram_frames)

    return {
        "pid": proc.id,
        "process_name": proc.name,
        "state": proc.state,
        "privilege_ring": proc.privilege_ring,
        "selected_page": page_num,
        "summary": {
            "total_pages": len(pages),
            "pages_in_ram": pages_in_ram,
            "pages_in_swap": pages_in_swap,
            "pages_accessed": pages_accessed,
            "dirty_pages": dirty_pages,
        },
        "global_ram": {
            "total_frames": PHYSICAL_FRAMES,
            "used_frames": total_used_frames,
            "free_frames": max(0, PHYSICAL_FRAMES - total_used_frames),
        },
        "global_swap": {
            "total_blocks": SWAP_BLOCKS,
            "used_blocks": total_used_swap,
            "free_blocks": max(0, SWAP_BLOCKS - total_used_swap),
        },
        "frames": frames,
        "swap_entries": swap_entries,
    }

