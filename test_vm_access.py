import sys
from app.database import SessionLocal
from app.services.vm_service import access_memory
from app.models import VirtualMemoryProcess

db = SessionLocal()
proc = db.query(VirtualMemoryProcess).first()
if not proc:
    print("No processes found. Please seed the database or create a process first.")
    sys.exit(1)

print(f"Testing access for process {proc.name} (PID {proc.id})")
try:
    res = access_memory(db, pid=proc.id, address=0x00A0, operation="write", data="test data")
    print("Success:", res)
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()
