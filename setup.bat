@echo off
cd /d %~dp0

if not exist .venv (
    py -3 -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo Setup hoan tat.
pause
