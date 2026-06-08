"""
terminal.py — API route for the virtual terminal command executor.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import TerminalCommand, TerminalResponse
from app.services.terminal_service import execute_command

router = APIRouter(prefix="/api/terminal", tags=["terminal"])


@router.post("/execute", response_model=TerminalResponse)
def execute(cmd: TerminalCommand, db: Session = Depends(get_db)):
    """Execute a simulated Unix command safely."""
    result = execute_command(db, cmd.command)
    return TerminalResponse(**result)
