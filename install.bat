@echo off
setlocal

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYTHON_VERSION=%%v
echo Detected Python version: %PYTHON_VERSION%

for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do set PY_MAJOR=%%a& set PY_MINOR=%%b

set /a VERSION_OK=0
if %PY_MAJOR% GEQ 3 (
    if %PY_MINOR% GEQ 12 set VERSION_OK=1
)

if not %VERSION_OK%==1 (
    echo.
    echo ERROR: Python 3.12 or newer is required.
    echo Please install Python 3.12+ from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Creating virtual environment...
python -m venv .venv
call .venv\Scripts\activate

echo Installing dependencies...
pip install --upgrade pip
pip install .
pip install pyinstaller

echo Building executable...
pyinstaller --name sampletones \
    --onefile \
    --distpath . \
    --icon src\sampletones\icons\sampletones.ico \
    --add-data "src\sampletones\icons;sampletones\icons" src\sampletones\__main__.py

if exist sampletones.exe (
    echo Build complete: .\sampletones.exe
) else (
    echo Build failed.
)

pause
