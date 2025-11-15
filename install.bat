@echo off
setlocal

rem --- Check for Python 3.12 or newer ---
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v

echo Detected Python version: %PYVER%

rem Extract major and minor version
for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do set MAJOR=%%a& set MINOR=%%b

set /a VER_OK=0
if %MAJOR% GEQ 3 (
    if %MINOR% GEQ 12 set VER_OK=1
)

if not %VER_OK%==1 (
    echo.
    echo ERROR: Python 3.12 or newer is required.
    echo Please install Python 3.12+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

rem --- Create venv ---
echo Creating virtual environment...
python -m venv .venv
call .venv\Scripts\activate

rem --- Install dependencies ---
echo Installing dependencies...
pip install --upgrade pip
pip install .
pip install pyinstaller

rem --- Build executable ---
echo Building executable...
pyinstaller --name sampletones --onefile --distpath . src/sampletones/__main__.py

if exist sampletones (
    echo Build complete: .\sampletones.exe
) else (
    echo Build failed.
)

pause
