@echo off
setlocal

set SCRIPT_DIR=%~dp0

call "%SCRIPT_DIR%mypy.bat"
set MYPY_EXIT=%ERRORLEVEL%

call "%SCRIPT_DIR%pylint.bat"
set PYLINT_EXIT=%ERRORLEVEL%

if not %MYPY_EXIT%==0 (
    echo Linting failed.
    exit /b 1
)

if not %PYLINT_EXIT%==0 (
    echo Linting failed.
    exit /b 1
)

echo All linting checks passed.
exit /b 0
