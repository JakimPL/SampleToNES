@echo off
setlocal

call "%~dp0..\lib\root.bat" || exit /b 1

if exist ".venv-build" (
    echo Virtual environment already exists.
) else (
    echo Creating virtual environment...
    python -m venv .venv-build || exit /b
    echo Virtual environment created.
)

exit /b 0
