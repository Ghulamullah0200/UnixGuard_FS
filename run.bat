@echo off
echo ==========================================
echo  UnixGuard FS - Unix File System Simulator
echo ==========================================
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo [1/5] Creating virtual environment...
    python -m venv venv
) else (
    echo [1/5] Virtual environment already exists.
)

REM Activate virtual environment
echo [2/5] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install requirements
echo [3/5] Installing dependencies...
pip install -r requirements.txt --quiet

REM Seed the database
echo [4/5] Initializing and seeding database...
python -c "from app.seed import seed_database; seed_database()"

REM Start server
echo [5/5] Starting Uvicorn server...
echo.
echo ==========================================
echo  Open your browser at:
echo  http://127.0.0.1:8000
echo ==========================================
echo.
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
