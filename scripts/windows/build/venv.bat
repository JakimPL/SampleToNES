@echo off
setlocal

call "%~dp0..\lib\root.bat" || exit /b 1

if exist ".venv-build" (
    echo Virtual environment already exists. Activating...
    call .venv-build\Scripts\activate || exit /b
    echo Virtual environment activated.
) else (
    echo Creating virtual environment...
    python -m venv .venv-build || exit /b
    call .venv-build\Scripts\activate || exit /b
    echo Virtual environment created and activated.
)

exit /b 0
