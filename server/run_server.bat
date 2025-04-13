@echo off

echo Starting FastAPI server...
python -m app.seeding_manager.seed
echo  http://127.0.0.1:8000/docs
uvicorn app.main:app 
pause


