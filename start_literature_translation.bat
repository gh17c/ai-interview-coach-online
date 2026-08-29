@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo The Python virtual environment was not found.
    echo Please run install_windows.bat first.
    pause
    exit /b 1
)

start "AI Interview Coach - Literature Translation" /b ".venv\Scripts\python.exe" -m streamlit run app_ui.py --server.headless true --server.port 8501
timeout /t 2 /nobreak >nul
start "" "http://localhost:8501/?mode=literature_translation"
echo Literature translation simulation is running at http://localhost:8501/?mode=literature_translation
pause
