@echo off
setlocal enabledelayedexpansion
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%\..\lib\root.bat" || exit /b 1

set "PROJECT_DIR=%SCRIPT_DIR%..\..\.."
set "VENV_DIR=%PROJECT_DIR%\.venv-build"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

set "EXTRAS="

:parse_args
if "%~1"=="" goto install
if "%~1"=="--dev" (
    if defined EXTRAS (
        set "EXTRAS=!EXTRAS!,dev"
    ) else (
        set "EXTRAS=dev"
    )
)
if "%~1"=="--gpu" (
    if defined EXTRAS (
        set "EXTRAS=!EXTRAS!,gpu"
    ) else (
        set "EXTRAS=gpu"
    )
)
shift
goto parse_args

:install
echo Installing dependencies...
"%VENV_PY%" -m pip install --upgrade pip

if defined EXTRAS (
    echo Installing with extras: !EXTRAS!
    "%VENV_PY%" -m pip install ".[!EXTRAS!]"
) else (
    "%VENV_PY%" -m pip install .
)

echo sampletones Python package installed successfully.
exit /b 0
