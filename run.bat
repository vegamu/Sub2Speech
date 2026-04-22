@echo off
cd /d %~dp0

if not exist .venv\Scripts\activate.bat (
    echo Chua co moi truong ao, chay setup...
    call setup.bat
)

call .venv\Scripts\activate.bat
set PYTHONPATH=%CD%\src
python -m sub2speech.app
