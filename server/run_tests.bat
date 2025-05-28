@echo off
call venv\Scripts\activate
set TESTING=1
pytest -n 0 --setup-only
pytest -n 8


pause