@echo off
chcp 65001 >nul
cd /d %~dp0

if not exist venv (
    python -m venv venv
)

call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt

set HOST=0.0.0.0
set PORT=5000
python run_public.py
pause
