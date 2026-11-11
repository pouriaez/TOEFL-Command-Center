@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo TOEFL Command Center - Windows Desktop
echo Project folder: %CD%
echo ==========================================

if not exist "main.py" (
    echo ERROR: main.py was not found.
    pause
    exit /b 1
)
if not exist "requirements-desktop.txt" (
    echo ERROR: requirements-desktop.txt was not found.
    pause
    exit /b 1
)
where py >nul 2>nul
if errorlevel 1 (
    echo ERROR: Install Python 3.11+ and enable Add Python to PATH.
    pause
    exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 (echo ERROR: Could not create virtual environment.& pause & exit /b 1)
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements-desktop.txt
if errorlevel 1 (
    echo ERROR: Desktop dependencies could not be installed.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 echo The desktop application exited with an error.
pause
endlocal
