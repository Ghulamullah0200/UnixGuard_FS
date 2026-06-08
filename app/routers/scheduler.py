"""
scheduler.py — API route for CPU scheduling simulation demos.
"""

from fastapi import APIRouter, Query
from app.services.scheduler_service import run_scheduler_demo

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


@router.get("/demo")
def scheduler_demo(
    algorithm: str = Query("fcfs", description="fcfs | rr | priority"),
    quantum: int = Query(2, description="Time quantum for Round Robin"),
):
    """Run a scheduling simulation and return results with Gantt data."""
    return run_scheduler_demo(algorithm, quantum)
