@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo The Python virtual environment was not found.
    echo Please run: python -m venv .venv
    pause
    exit /b 1
)

if not exist "app_ui.py" (
    echo app_ui.py was not found in this folder.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m streamlit run app_ui.py --server.port 8501
pause
