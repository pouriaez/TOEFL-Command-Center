@echo off
call .venv\Scripts\activate
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name TOEFL-Command-Center main.py
 echo EXE is in dist\TOEFL-Command-Center.exe
pause
