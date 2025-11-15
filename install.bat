@echo off
setlocal

rem --- Check for Python 3.12 ---
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v

echo Detected Python version: %PYVER%

echo %PYVER% | findstr /b "3.12." >nul
if errorlevel 1 (
    echo.
    echo ERROR: Python 3.12 is required.
    echo Please install Python 3.12 from https://www.python.org/downloads/
    exit /b 1
)

rem --- Create venv ---
python -m venv .venv
call .venv\Scripts\activate

rem --- Install dependencies ---
pip install --upgrade pip
pip install .
pip install pyinstaller

rem --- Build executable ---
pyinstaller --name sampletones --onefile --distpath . src/sampletones/__main__.py

