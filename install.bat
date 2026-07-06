@echo off
setlocal

set SCRIPT_DIR=%~dp0

call "%SCRIPT_DIR%scripts\windows\build\python.bat" || exit /b
call "%SCRIPT_DIR%scripts\windows\build\venv.bat" || exit /b
call "%SCRIPT_DIR%scripts\windows\build\sampletones.bat" %* || exit /b
call "%SCRIPT_DIR%scripts\windows\build\build.bat" %* || exit /b

pause
