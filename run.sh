#!/usr/bin/env bash
echo "=========================================="
echo " UnixGuard FS - Unix File System Simulator"
echo "=========================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "[1/5] Creating virtual environment..."
    python3 -m venv venv
else
    echo "[1/5] Virtual environment already exists."
fi

# Activate virtual environment
echo "[2/5] Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "[3/5] Installing dependencies..."
pip install -r requirements.txt --quiet

# Seed the database
echo "[4/5] Initializing and seeding database..."
python -c "from app.seed import seed_database; seed_database()"

# Start server
echo "[5/5] Starting Uvicorn server..."
echo ""
echo "=========================================="
echo " Open your browser at:"
echo " http://127.0.0.1:8000"
echo "=========================================="
echo ""
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
