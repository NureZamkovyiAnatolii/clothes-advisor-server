@echo off
echo Activating virtual environment...
call venv\Scripts\activate

echo Starting FastAPI server...
python -m app.seeding_manager.seed

echo Server running at http://127.0.0.1:8000/docs
uvicorn app.main:app --reload

pause