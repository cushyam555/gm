@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller==6.16.0
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name GM1-MIDI-Reset run.py
if errorlevel 1 goto fail
echo Built: dist\GM1-MIDI-Reset.exe
:fail
pause
