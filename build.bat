@echo off
chcp 65001 >nul 2>&1
title WhisperTyping - Сборка EXE
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║      WhisperTyping - Сборка .exe         ║
echo  ╚══════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: Activate venv if exists
if exist ".venv312\Scripts\activate.bat" (
    call .venv312\Scripts\activate.bat
    echo  Используется venv312 (Python 3.12)
) else if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo  Используется venv
) else (
    echo  venv не найден, используется системный Python
)

:: Check PyInstaller
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo  Установка PyInstaller...
    pip install pyinstaller
)

echo.
echo  Сборка... (это может занять 2-5 минут)
echo.

pyinstaller whisper_typing.spec --noconfirm

if %errorlevel% neq 0 (
    echo.
    echo  ОШИБКА сборки!
    pause
    exit /b 1
)

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║         Сборка завершена!                ║
echo  ║                                          ║
echo  ║  Результат: dist\WhisperTyping\          ║
echo  ║  Запуск:    dist\WhisperTyping\           ║
echo  ║             WhisperTyping.exe             ║
echo  ╚══════════════════════════════════════════╝
echo.
pause
