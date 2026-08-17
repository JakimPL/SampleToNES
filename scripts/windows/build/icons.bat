@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%\..\lib\root.bat" || exit /b 1

set "PROJECT_DIR=%SCRIPT_DIR%..\..\.."
set "VENV_DIR=%PROJECT_DIR%\.venv-build"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

echo Generating the icon suite...
"%VENV_PY%" scripts\assets\icons.py || exit /b 1

exit /b 0
