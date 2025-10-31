#!/bin/bash
# Fresh Markets Watch - Quick Start Script

set -e

echo "Starting Fresh Markets Watch..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "Error: .env file not found"
    echo "Please copy .env.example to .env and configure it"
    echo "  cp .env.example .env"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Starting server..."
python -m uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}
