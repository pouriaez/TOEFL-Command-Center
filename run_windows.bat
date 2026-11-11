@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo TOEFL Command Center - Windows Launcher
echo Project folder: %CD%
echo ==========================================

if not exist "main.py" (
    echo ERROR: main.py was not found.
    echo Please extract the ZIP and run this file from the project folder.
    pause
    exit /b 1
)

if not exist "requirements.txt" (
    echo ERROR: requirements.txt was not found.
    echo Please download the complete repository ZIP and extract it.
    pause
    exit /b 1
)

where py >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python Launcher ^(py^) was not found.
    echo Install Python 3.11 or newer and enable "Add Python to PATH".
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo ERROR: Could not create the virtual environment.
        pause
        exit /b 1
    )
)

echo Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo WARNING: pip upgrade failed. Continuing with the installed pip.
)

echo Installing requirements...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Dependency installation failed.
    echo Check your internet connection or configure a working PyPI mirror.
    pause
    exit /b 1
)

echo Starting TOEFL Command Center...
".venv\Scripts\python.exe" main.py
if errorlevel 1 (
    echo The application exited with an error.
)

pause
endlocal
