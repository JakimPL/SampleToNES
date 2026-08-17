@echo off
setlocal enabledelayedexpansion
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
call "%SCRIPT_DIR%\..\lib\root.bat" || exit /b 1

set "PROJECT_DIR=%SCRIPT_DIR%..\..\.."
set "VENV_DIR=%PROJECT_DIR%\.venv-build"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

set "EXTRAS=build"

:parse_args
if "%~1"=="" goto install
if "%~1"=="--gpu" set "EXTRAS=!EXTRAS!,gpu"
shift
goto parse_args

:install
echo Installing dependencies...
"%VENV_PY%" -m pip install --upgrade pip

echo Installing with extras: !EXTRAS!
"%VENV_PY%" -m pip install ".[!EXTRAS!]" --group assets || exit /b 1

echo sampletones Python package installed successfully.
exit /b 0
