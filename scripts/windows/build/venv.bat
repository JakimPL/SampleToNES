@echo off
setlocal

if exist ".venv" (
    echo Virtual environment already exists. Activating...
    call .venv\Scripts\activate || exit /b
    echo Virtual environment activated.
) else (
    echo Creating virtual environment...
    python -m venv .venv || exit /b
    call .venv\Scripts\activate || exit /b
    echo Virtual environment created and activated.
)

exit /b 0
