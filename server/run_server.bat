@echo off

echo Starting FastAPI server...
echo  http://127.0.0.1:8000/docs
uvicorn app.main:app 
pause


