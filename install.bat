@echo off
setlocal

python "%~dp0scripts\bundle.py" %*
set STATUS=%ERRORLEVEL%
pause
exit /b %STATUS%
