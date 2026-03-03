@echo off
title WhisperTyping (Debug)
cd /d "%~dp0"

:: Use venv if it exists
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
) else (
    python main.py
)
pause
