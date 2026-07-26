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

exit /b 0
