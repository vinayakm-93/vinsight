#!/bin/bash

# VinSight Local Runner
# Handles PYTHONPATH and dependency checks for a smooth startup.

# 1. Set PYTHONPATH to include the backend directory
export PYTHONPATH=$PYTHONPATH:$(pwd)/backend

echo "=================================================="
echo " VinSight Local Dev Server"
echo "=================================================="
echo " [INFO] PYTHONPATH set to include backend/"

# 2. Check for .env
if [ ! -f .env ]; then
    echo " [WARNING] .env file not found! Copying .env.example..."
    cp .env.example .env
    echo " [INFO] Created .env. Please check it."
fi

# 3. Check if virtualenv is active (optional, just a warning)
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo " [TIP] No virtual environment detected. Recommended to run: source .venv/bin/activate"
fi

# 4. Start Uvicorn
echo " [INFO] Starting Uvicorn Server on http://0.0.0.0:8000..."
echo "=================================================="

# Run from root, targeting backend.main:app
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
