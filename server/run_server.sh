#!/bin/bash

echo "Activating virtual environment..."
source venv/bin/activate

echo "Starting FastAPI seeding..."
python -m app.seeding_manager.seed

echo "Server running at http://127.0.0.1:8000/docs"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

read -p "Press any key to exit..."
