@echo off
echo Activating virtual environment...
call venv\Scripts\activate

echo Starting FastAPI server...

echo Server running at http://127.0.0.1:8000/docs
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload


pause