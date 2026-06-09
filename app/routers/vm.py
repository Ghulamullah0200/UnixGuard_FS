"""
vm.py — API routes for demand-paged Virtual Memory simulation.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import VMProcessOut, VMProcessCreate, VMMemoryAccessRequest, VMMemoryAccessResponse
from app.services import vm_service

router = APIRouter(prefix="/api/vm", tags=["virtual_memory"])


@router.get("/processes", response_model=list[VMProcessOut])
def get_processes(db: Session = Depends(get_db)):
    """List all running VM processes."""
    return vm_service.get_all_processes(db)


@router.post("/processes", response_model=VMProcessOut)
def create_process_endpoint(data: VMProcessCreate, db: Session = Depends(get_db)):
    """Create a new simulated Ring 3 user mode process."""
    return vm_service.create_process(db, data.name)


@router.delete("/processes/{pid}")
def delete_process_endpoint(pid: int, db: Session = Depends(get_db)):
    """Terminate a process and free all its pages/memory."""
    success = vm_service.delete_process(db, pid)
    if not success:
        raise HTTPException(status_code=404, detail="Process not found")
    return {"message": "Process deleted successfully"}


@router.get("/ram")
def get_ram_layout_endpoint(db: Session = Depends(get_db)):
    """Get physical frame mapping (RAM layout)."""
    return vm_service.get_ram_layout(db)


@router.get("/swap")
def get_swap_layout_endpoint(db: Session = Depends(get_db)):
    """Get swap block mapping on disk."""
    return vm_service.get_swap_layout(db)


@router.post("/access", response_model=VMMemoryAccessResponse)
def access_memory_endpoint(data: VMMemoryAccessRequest, db: Session = Depends(get_db)):
    """Simulate a memory access. Triggers page fault handler if invalid."""
    result = vm_service.access_memory(
        db,
        pid=data.process_id,
        address=data.address,
        operation=data.operation,
        data=data.data
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/processes/{pid}/memory-map")
def get_process_memory_map_endpoint(pid: int, db: Session = Depends(get_db)):
    """Get per-process memory map: frames owned, pages swapped, global state."""
    result = vm_service.get_process_memory_map(db, pid)
    if not result:
        raise HTTPException(status_code=404, detail="Process not found")
    return result

