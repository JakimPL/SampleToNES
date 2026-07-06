@echo off
setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set NO_VENV=false
set PASS_ARGS=

:parse_args
if "%~1"=="" goto run_install
if "%~1"=="--no-venv" (
    set NO_VENV=true
) else (
    set PASS_ARGS=!PASS_ARGS! %~1
)
shift
goto parse_args

:run_install
if "%NO_VENV%"=="false" (
    call "%SCRIPT_DIR%scripts\windows\build\python.bat" || exit /b
    call "%SCRIPT_DIR%scripts\windows\build\venv.bat" || exit /b
)

call "%SCRIPT_DIR%scripts\windows\build\install.bat" %PASS_ARGS% || exit /b
call "%SCRIPT_DIR%scripts\windows\build\build.bat" %PASS_ARGS% || exit /b

pause
