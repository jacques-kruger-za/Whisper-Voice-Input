@echo off
REM Whisper Voice Input - Build Script
REM Uses project venv with Python 3.12

setlocal
cd /d "%~dp0"

set VENV_PYTHON=venv\Scripts\python.exe
set VENV_PIP=venv\Scripts\pip.exe
set VENV_PYINSTALLER=venv\Scripts\pyinstaller.exe

REM Check if venv exists
if not exist "%VENV_PYTHON%" (
    echo [ERROR] Virtual environment not found!
    echo.
    echo Creating venv with Python 3.12...
    "C:\Users\Jacques Kruger\AppData\Local\Programs\Python\Python312\python.exe" -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv. Is Python 3.12 installed?
        pause
        exit /b 1
    )
)

REM Show Python version
echo.
echo === Python Environment ===
"%VENV_PYTHON%" --version

REM Install/update dependencies
echo.
echo === Installing Dependencies ===
"%VENV_PIP%" install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

REM Ensure PyInstaller is installed
"%VENV_PIP%" show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo.
    echo === Installing PyInstaller ===
    "%VENV_PIP%" install pyinstaller
)

REM Build the executable
echo.
echo === Building Executable ===
"%VENV_PYINSTALLER%" "Whisper Voice Input.spec" --noconfirm
if errorlevel 1 (
    echo [ERROR] Build failed
    pause
    exit /b 1
)

echo.
echo === Build Complete ===
echo Output: dist\Whisper Voice Input.exe
echo.
pause
