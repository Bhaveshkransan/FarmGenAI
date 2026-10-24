#!/bin/bash
set -e

echo "======================================================================"
echo "RUNNING FARMGENAI FULL LOCAL RUNTIME VERIFICATION (BASH RUNNER)"
echo "======================================================================"

export ENABLE_LLM=false
export TESTING=1
export DATABASE_URL="sqlite+aiosqlite:///agrinegotiator.db"
export DB_PATH="agrinegotiator.db"
export JWT_SECRET_KEY="test-secret-key-32-chars-minimum-abcdef12345"

# Pick python executable
if [ -f ".venv/bin/python" ]; then
    PYTHON_CMD=".venv/bin/python"
elif [ -f ".venv/Scripts/python.exe" ]; then
    PYTHON_CMD=".venv/Scripts/python.exe"
else
    PYTHON_CMD="python3"
fi

echo "Using Python: $PYTHON_CMD"
$PYTHON_CMD scripts/run_full_local_e2e.py

echo "Executing pytest suites..."
$PYTHON_CMD -m pytest tests/test_buyer_workflow_security_and_persistence.py -v

echo "======================================================================"
echo "ALL VERIFICATION RUNS COMPLETED!"
echo "======================================================================"
