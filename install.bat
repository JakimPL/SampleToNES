@echo off
setlocal

set SCRIPT_DIR=%~dp0

call "%SCRIPT_DIR%scripts\windows\python.bat" || exit /b
call "%SCRIPT_DIR%scripts\windows\venv.bat" || exit /b
call "%SCRIPT_DIR%scripts\windows\install.bat" %* || exit /b
call "%SCRIPT_DIR%scripts\windows\build.bat" || exit /b

pause
