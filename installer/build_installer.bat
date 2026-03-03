@echo off
chcp 65001 >nul 2>&1
title WhisperTyping - Build Installer

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║    WhisperTyping - Создание установщика  ║
echo  ╚══════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: Check that dist\WhisperTyping exists
if not exist "..\dist\WhisperTyping\WhisperTyping.exe" (
    echo  ОШИБКА: сначала запусти build.bat для сборки .exe
    echo  Файл ..\dist\WhisperTyping\WhisperTyping.exe не найден
    pause
    exit /b 1
)

:: Find Inno Setup compiler
set ISCC=""
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"

if %ISCC%=="" (
    echo  ОШИБКА: Inno Setup не найден
    echo  Установи через: winget install JRSoftware.InnoSetup
    pause
    exit /b 1
)

echo  Сборка установщика...
echo.

%ISCC% setup.iss

if %errorlevel% neq 0 (
    echo.
    echo  ОШИБКА при создании установщика!
    pause
    exit /b 1
)

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║       Установщик создан!                 ║
echo  ║                                          ║
echo  ║  Файл: dist\WhisperTyping_Setup.exe      ║
echo  ╚══════════════════════════════════════════╝
echo.
pause
