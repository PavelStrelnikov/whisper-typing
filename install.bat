@echo off
chcp 65001 >nul 2>&1
title WhisperTyping - Установка / Install
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║      WhisperTyping - Установка v1.0      ║
echo  ╚══════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: ─── Check Python ───────────────────────────────────
echo [1/4] Проверка Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ОШИБКА: Python не найден!
    echo  Скачайте Python 3.10+ с https://python.org
    echo  При установке обязательно отметьте "Add Python to PATH"
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo  OK: Python %PYVER%

:: ─── Create venv ────────────────────────────────────
echo.
echo [2/4] Создание виртуального окружения...
if not exist ".venv" (
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo  ОШИБКА: Не удалось создать venv
        pause
        exit /b 1
    )
    echo  Создано: .venv
) else (
    echo  Уже существует: .venv
)

:: ─── Activate venv and install deps ─────────────────
echo.
echo [3/4] Установка зависимостей...
call .venv\Scripts\activate.bat

pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo  ОШИБКА при установке зависимостей!
    pause
    exit /b 1
)

:: ─── CUDA (optional) ────────────────────────────────
echo.
echo [4/4] CUDA (ускорение на GPU NVIDIA)...
echo.
set /p INSTALL_CUDA="  У вас есть NVIDIA GPU и хотите CUDA? (y/n): "
if /i "%INSTALL_CUDA%"=="y" (
    pip install -r requirements-cuda.txt
    if %errorlevel% neq 0 (
        echo  Предупреждение: CUDA не установилась, будет работать на CPU
    ) else (
        echo  CUDA установлена!
    )
) else (
    echo  Пропущено. Будет работать на CPU (медленнее, но работает)
)

:: ─── Done ───────────────────────────────────────────
echo.
echo  ╔══════════════════════════════════════════╗
echo  ║         Установка завершена!             ║
echo  ║                                          ║
echo  ║  Запуск: run.bat (без консоли)           ║
echo  ║  Отладка: run_console.bat (с логами)     ║
echo  ╚══════════════════════════════════════════╝
echo.
pause
