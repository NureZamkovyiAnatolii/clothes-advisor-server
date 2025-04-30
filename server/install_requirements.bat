@echo off
echo Activating virtual environment...
call venv\Scripts\activate

echo Installing dependencies...
pip install -r requirements.txt
echo Installation completed.

pause