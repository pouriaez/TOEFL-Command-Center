@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run run_windows.bat once to create the environment first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements-desktop.txt pyinstaller
if errorlevel 1 (echo Dependency installation failed.& pause & exit /b 1)
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --onefile --windowed --name TOEFL-Command-Center main.py
if errorlevel 1 (echo EXE build failed.& pause & exit /b 1)
echo EXE is in dist\TOEFL-Command-Center.exe
pause
endlocal
