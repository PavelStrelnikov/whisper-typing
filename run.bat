@echo off
title WhisperTyping
cd /d "%~dp0"

:: Use venv if it exists
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" whisper_typing.pyw
    exit /b
)

if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\python.exe" main.py
    exit /b
)

:: Fallback to system Python
where pythonw >nul 2>&1
if %errorlevel%==0 (
    start "" pythonw whisper_typing.pyw
) else (
    python main.py
)
